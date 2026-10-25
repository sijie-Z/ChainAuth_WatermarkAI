"""疑似侵权线索 API

公开溯源页可以提交疑似盗用文件或链接；服务端尝试提取水印并匹配已发布资产。
管理员在后台受理、确认或驳回，结果会通知举报人与资产权利人。
"""
import hashlib
import os
import uuid
from datetime import datetime, timedelta

from flask import current_app, request, send_file
from flask_jwt_extended import get_jwt_identity, jwt_required
from flask_restful import Resource
from sqlalchemy import or_

from app.extensions import db
from app.models import Asset, Certificate, InfringementReport, OperationLog, User
from app.resources.asset import validate_magic_bytes
from app.services.notification_service import add_notification_event
from app.services.watermark_service import WatermarkService
from app.utils.middleware import rate_limit
from app.utils.paths import REPORT_EXT_ALIASES, canonical_extension, uuid_filename

ADMIN_ROLES = ('admin', 'asset_admin', 'license_admin', 'adm1', 'adm2')
REVIEW_ROLES = ('admin', 'asset_admin', 'license_admin')
REPORT_STATUSES = ('pending', 'reviewing', 'confirmed', 'rejected')
MAX_REPORT_FILE = 20 * 1024 * 1024


def _published_asset_by_watermark(watermark_id):
    if not watermark_id:
        return None
    return Asset.query.filter_by(
        watermark_id=watermark_id, status='published'
    ).first()


def _certificate_for(asset):
    if not asset or not asset.certificate_id:
        return None
    return Certificate.query.filter_by(
        certificate_id=asset.certificate_id
    ).first()


def _report_dir():
    root = os.path.abspath(current_app.config.get('UPLOAD_FOLDER', './uploads'))
    path = os.path.join(root, 'reports')
    os.makedirs(path, exist_ok=True)
    return path


def _notify_report_parties(report, action, comment=None):
    """确认/驳回后通知举报人和资产权利人，同一用户只发一次。"""
    event_type = (
        'infringement_confirmed' if action == 'confirm'
        else 'infringement_rejected'
    )
    label = '已确认' if action == 'confirm' else '已驳回'
    targets = set()
    if report.reporter_id:
        targets.add(report.reporter_id)
    asset = report.asset
    owner_id = None
    if asset:
        owner_id = asset.owner_id or asset.creator_id or asset.uploader_id
        if owner_id:
            targets.add(owner_id)

    for user_id in targets:
        add_notification_event(
            user_id,
            event_type,
            f'侵权线索{label}：{report.report_code}',
            (
                f'{(asset.title if asset else report.source_url) or "疑似侵权线索"}'
                + (f' · {comment}' if comment else '')
            ),
            f'/assets/{report.asset_id}' if (asset and user_id != report.reporter_id) else '/trace',
        )


class InfringementReportResource(Resource):
    """公开提交疑似侵权线索"""

    @rate_limit(limit=5, window=3600)
    @jwt_required(optional=True)
    def post(self):
        user_id = get_jwt_identity()
        user = User.query.get(user_id) if user_id else None

        data = request.form if request.form else (request.get_json(silent=True) or {})
        source_url = (data.get('source_url') or '').strip()[:500]
        description = (data.get('description') or '').strip()[:2000]
        contact = (data.get('contact') or (user.email if user else '') or '').strip()[:200]
        reporter_name = (
            data.get('reporter_name')
            or (user.nickname or user.username if user else '')
            or ''
        ).strip()[:100]

        asset = None
        asset_id = (data.get('asset_id') or '').strip()
        watermark_id = (data.get('watermark_id') or '').strip()
        if asset_id:
            asset = Asset.query.filter_by(id=asset_id, status='published').first()
            if not asset:
                return {'code': 404, 'message': '匹配资产不存在或未发布'}, 404
        if not asset and watermark_id:
            asset = _published_asset_by_watermark(watermark_id)

        file = request.files.get('file')
        suspect_path = None
        suspect_hash = None
        suspect_size = None
        suspect_filename = None
        trace_verified = False

        if file and file.filename:
            original_name = file.filename
            ext = canonical_extension(original_name, REPORT_EXT_ALIASES)
            if not ext:
                return {'code': 400, 'message': '仅支持图片或 ZIP 文件'}, 400
            if not validate_magic_bytes(file, ext.lstrip('.')):
                return {'code': 400, 'message': '文件内容与扩展名不匹配'}, 400

            file.seek(0, os.SEEK_END)
            suspect_size = file.tell()
            file.seek(0)
            if suspect_size > MAX_REPORT_FILE:
                return {
                    'code': 400,
                    'message': f'线索文件不能超过 {MAX_REPORT_FILE // 1024 // 1024}MB'
                }, 400

            suspect_filename = original_name[:255]
            suspect_path = os.path.join(_report_dir(), uuid_filename(ext))
            file.seek(0)
            digest = hashlib.sha256()
            for chunk in iter(lambda: file.read(1024 * 1024), b''):
                digest.update(chunk)
            suspect_hash = digest.hexdigest()
            file.seek(0)
            file.save(suspect_path)

            try:
                trace = WatermarkService.trace_from_file(suspect_path)
                if trace.get('success') and trace.get('watermark_id'):
                    matched = _published_asset_by_watermark(trace['watermark_id'])
                    if matched:
                        asset = matched
                        watermark_id = trace['watermark_id']
                        trace_verified = True
            except Exception:
                current_app.logger.warning('侵权线索文件溯源失败', exc_info=True)

        if not any([suspect_path, asset, source_url, description]):
            return {
                'code': 400,
                'message': '请至少上传线索文件、匹配资产、来源链接或文字说明之一'
            }, 400

        certificate = _certificate_for(asset)
        report = InfringementReport(
            asset_id=asset.id if asset else None,
            reporter_id=user.id if user else None,
            reporter_name=reporter_name or None,
            contact=contact or None,
            source_url=source_url or None,
            description=description or None,
            suspect_filename=suspect_filename,
            suspect_file_path=suspect_path,
            suspect_file_hash=suspect_hash,
            suspect_file_size=suspect_size,
            watermark_id=watermark_id or (asset.watermark_id if asset else None),
            certificate_id=(
                certificate.certificate_id if certificate
                else (asset.certificate_id if asset else None)
            ),
            trace_verified=bool(trace_verified or (asset is not None and not suspect_path)),
            status='pending',
        )
        db.session.add(report)
        db.session.flush()

        if asset:
            owner_id = asset.owner_id or asset.creator_id or asset.uploader_id
            add_notification_event(
                owner_id,
                'infringement_reported',
                f'收到疑似侵权线索：{asset.title}',
                f'线索编号 {report.report_code}，管理员会跟进核实。',
                f'/assets/{asset.id}?tab=evidence',
            )

        db.session.commit()

        OperationLog.log(
            user=user,
            action='infringement_report',
            module='infringement',
            description=f'提交侵权线索: {report.report_code}',
            target_type='infringement_report',
            target_id=str(report.id),
            request=request,
        )

        return {
            'code': 200,
            'message': '线索已提交，管理员会尽快核实',
            'data': {
                'report_code': report.report_code,
                'status': report.status,
                'trace_verified': report.trace_verified,
                'asset': {
                    'id': asset.id,
                    'asset_code': asset.asset_code,
                    'title': asset.title,
                } if asset else None,
            }
        }, 200


class InfringementPatrolResource(Resource):
    """批量巡检：上传多个疑似副本，异步提取水印并自动生成线索"""

    @rate_limit(limit=5, window=3600)
    @jwt_required()
    def post(self):
        user = User.query.get(get_jwt_identity())
        if not user or user.role not in REVIEW_ROLES:
            return {'code': 403, 'message': '无权限执行巡检'}, 403

        uploads = request.files.getlist('files')
        if not uploads:
            single = request.files.get('file')
            uploads = [single] if single else []
        uploads = [item for item in uploads if item and item.filename]
        if not uploads:
            return {'code': 400, 'message': '请选择要巡检的文件'}, 400
        if len(uploads) > 20:
            return {'code': 400, 'message': '单次最多巡检 20 个文件'}, 400

        validated = []
        for upload in uploads:
            ext = canonical_extension(upload.filename, REPORT_EXT_ALIASES)
            if not ext:
                return {
                    'code': 400,
                    'message': f'{upload.filename}: 仅支持图片或 ZIP 文件'
                }, 400
            if not validate_magic_bytes(upload, ext.lstrip('.')):
                return {
                    'code': 400,
                    'message': f'{upload.filename}: 文件内容与扩展名不匹配'
                }, 400
            upload.seek(0, os.SEEK_END)
            size = upload.tell()
            upload.seek(0)
            if size > MAX_REPORT_FILE:
                return {
                    'code': 400,
                    'message': f'{upload.filename}: 超过 20MB 限制'
                }, 400
            validated.append((upload, ext))

        batch_dir = os.path.join(_report_dir(), 'patrol', uuid.uuid4().hex)
        os.makedirs(batch_dir, exist_ok=True)
        source_url = (request.form.get('source_url') or '').strip()[:500]
        files = []
        try:
            for upload, ext in validated:
                filename = uuid_filename(ext)
                path = os.path.join(batch_dir, filename)
                upload.save(path)
                files.append({
                    'path': path,
                    'name': upload.filename[:255],
                    'source_url': source_url,
                })
        except Exception:
            for item in files:
                try:
                    os.remove(item['path'])
                except OSError:
                    pass
            current_app.logger.exception('保存巡检文件失败')
            return {'code': 500, 'message': '巡检文件保存失败'}, 500

        from app.services.task_service import enqueue_patrol_task
        task = enqueue_patrol_task(user, files)
        return {
            'code': 202,
            'message': '巡检任务已提交，可在任务队列查看进度',
            'data': {
                'task_id': task.id,
                'file_count': len(files),
                'worker_enabled': bool(
                    current_app.config.get('TASK_WORKER_ENABLED', False)
                ),
                'task': task.to_dict(),
            }
        }, 202


class MyInfringementListResource(Resource):
    """当前用户提交的线索"""

    @jwt_required()
    def get(self):
        user_id = get_jwt_identity()
        page = max(request.args.get('page', 1, type=int), 1)
        per_page = min(max(request.args.get('per_page', 20, type=int), 1), 100)
        pagination = InfringementReport.query.filter_by(
            reporter_id=user_id
        ).order_by(
            InfringementReport.created_at.desc()
        ).paginate(page=page, per_page=per_page, error_out=False)
        return {
            'code': 200,
            'data': {
                'items': [item.to_dict() for item in pagination.items],
                'total': pagination.total,
            }
        }, 200


class InfringementListResource(Resource):
    """后台线索列表"""

    @jwt_required()
    def get(self):
        user = User.query.get(get_jwt_identity())
        if not user or user.role not in ADMIN_ROLES:
            return {'code': 403, 'message': '无权限'}, 403

        query = InfringementReport.query
        status = (request.args.get('status') or '').strip()
        if status:
            if status not in REPORT_STATUSES:
                return {'code': 400, 'message': '无效的线索状态'}, 400
            query = query.filter_by(status=status)

        keyword = (request.args.get('keyword') or '').strip()
        if keyword:
            like = f'%{keyword}%'
            matching_assets = db.session.query(Asset.id).filter(
                or_(Asset.asset_code.ilike(like), Asset.title.ilike(like))
            )
            query = query.filter(
                or_(
                    InfringementReport.report_code.ilike(like),
                    InfringementReport.source_url.ilike(like),
                    InfringementReport.description.ilike(like),
                    InfringementReport.asset_id.in_(matching_assets),
                )
            )

        start = request.args.get('start_date')
        end = request.args.get('end_date')
        try:
            if start:
                query = query.filter(
                    InfringementReport.created_at >= datetime.strptime(start, '%Y-%m-%d')
                )
            if end:
                query = query.filter(
                    InfringementReport.created_at < (
                        datetime.strptime(end, '%Y-%m-%d') + timedelta(days=1)
                    )
                )
        except ValueError:
            return {'code': 400, 'message': '日期格式应为 YYYY-MM-DD'}, 400

        page = max(request.args.get('page', 1, type=int), 1)
        per_page = min(max(request.args.get('per_page', 20, type=int), 1), 100)
        pagination = query.order_by(
            InfringementReport.created_at.desc()
        ).paginate(page=page, per_page=per_page, error_out=False)

        counts = {
            status_name: InfringementReport.query.filter_by(
                status=status_name
            ).count()
            for status_name in REPORT_STATUSES
        }
        return {
            'code': 200,
            'data': {
                'items': [
                    item.to_dict(include_private=True)
                    for item in pagination.items
                ],
                'total': pagination.total,
                'page': page,
                'per_page': per_page,
                'counts': counts,
            }
        }, 200


class InfringementResource(Resource):
    """线索详情"""

    @jwt_required()
    def get(self, report_id):
        user = User.query.get(get_jwt_identity())
        if not user or user.role not in ADMIN_ROLES:
            return {'code': 403, 'message': '无权限'}, 403
        report = InfringementReport.query.get(report_id)
        if not report:
            return {'code': 404, 'message': '线索不存在'}, 404

        data = report.to_dict(include_private=True)
        asset = report.asset
        if asset:
            data['asset'] = {
                'id': asset.id,
                'asset_code': asset.asset_code,
                'title': asset.title,
                'status': asset.status,
                'thumbnail_url': f'/api/assets/{asset.id}/thumbnail?size=card',
            }
        data['can_review'] = user.role in REVIEW_ROLES
        return {'code': 200, 'data': data}, 200


class InfringementReviewResource(Resource):
    """受理、确认或驳回线索"""

    @jwt_required()
    def post(self, report_id):
        user = User.query.get(get_jwt_identity())
        if not user or user.role not in REVIEW_ROLES:
            return {'code': 403, 'message': '无权限处理线索'}, 403
        report = InfringementReport.query.get(report_id)
        if not report:
            return {'code': 404, 'message': '线索不存在'}, 404

        data = request.get_json(silent=True) or {}
        action = data.get('action')
        if action not in ('start', 'confirm', 'reject'):
            return {'code': 400, 'message': 'action 必须是 start/confirm/reject'}, 400
        comment = (data.get('comment') or '').strip()[:1000]

        if report.status in ('confirmed', 'rejected'):
            return {'code': 400, 'message': '该线索已处理完成'}, 400
        if action == 'start' and report.status == 'reviewing':
            return {'code': 200, 'message': '线索已在处理中', 'data': report.to_dict(True)}, 200

        report.reviewer_id = user.id
        report.review_comment = comment or report.review_comment
        if action == 'start':
            report.status = 'reviewing'
        else:
            report.status = 'confirmed' if action == 'confirm' else 'rejected'
            report.reviewed_at = datetime.utcnow()
            _notify_report_parties(report, action, comment)

        db.session.commit()
        OperationLog.log(
            user=user,
            action=f'infringement_{action}',
            module='infringement',
            description=f'处理侵权线索 {report.report_code}: {report.status}',
            target_type='infringement_report',
            target_id=str(report.id),
            request=request,
        )
        return {
            'code': 200,
            'message': '线索状态已更新',
            'data': report.to_dict(include_private=True),
        }, 200


class InfringementFileResource(Resource):
    """下载举报文件（仅管理员）"""

    @jwt_required()
    def get(self, report_id):
        user = User.query.get(get_jwt_identity())
        if not user or user.role not in ADMIN_ROLES:
            return {'code': 403, 'message': '无权限'}, 403
        report = InfringementReport.query.get(report_id)
        if not report:
            return {'code': 404, 'message': '线索不存在'}, 404
        path = os.path.abspath(report.suspect_file_path or '')
        report_root = _report_dir()
        if (
            not path
            or not path.startswith(report_root + os.sep)
            or not os.path.isfile(path)
        ):
            return {'code': 404, 'message': '线索文件不存在'}, 404
        ext = os.path.splitext(path)[1]
        return send_file(
            path,
            as_attachment=True,
            download_name=f'{report.report_code}-suspect{ext}',
        )
