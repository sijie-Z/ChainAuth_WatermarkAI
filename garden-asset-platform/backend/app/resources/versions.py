"""资产版本历史 API

提供版本列表、新版本上传、历史版本下载与恢复能力。
版本文件统一保存在 UPLOAD_FOLDER/versions/<asset_id>/ 下，资产主表始终
指向当前版本；上传/恢复只重置水印字段，不改动链上存证字段，历史存证
由证据链标记为“当前文件已变更”。
"""
import hashlib
import os
import shutil
import uuid
from datetime import datetime

from flask import current_app, request, send_file
from flask_jwt_extended import get_jwt_identity, jwt_required
from flask_restful import Resource
from sqlalchemy import func

from app.extensions import db
from app.models.asset import Asset, AssetVersion
from app.models.blockchain import Certificate
from app.models.log import OperationLog
from app.models.task import AsyncTask
from app.models.user import User
from app.resources.asset import allowed_file, calculate_file_hash, validate_magic_bytes
from app.services.blockchain_service import blockchain_service

VERSION_ADMIN_ROLES = ('admin', 'asset_admin')
VERSION_DIRNAME = 'versions'
DEFAULT_CHANGE_NOTE = '上传新版本'


def _is_admin(user):
    return bool(user and user.role in VERSION_ADMIN_ROLES)


def _is_owner(user_id, asset):
    return user_id in (asset.creator_id, asset.owner_id, asset.uploader_id)


def _can_manage(user, user_id, asset):
    """上传/下载/恢复版本：资产所有者或管理员"""
    return _is_admin(user) or _is_owner(user_id, asset)


def _can_view(user, user_id, asset):
    """与资产详情一致：已发布公开；未发布仅所有者/管理员；已删除仅管理员"""
    if not user:
        return False
    if asset.status == 'deleted':
        return _is_admin(user)
    if asset.status == 'published':
        return True
    return _is_admin(user) or _is_owner(user_id, asset)


def _max_version_no(asset_id):
    value = db.session.query(func.max(AssetVersion.version_no)).filter(
        AssetVersion.asset_id == asset_id
    ).scalar()
    return value or 0


def _next_version_no(asset_id):
    return _max_version_no(asset_id) + 1


def _running_task(asset_id):
    """运行中的水印/存证任务会写资产字段，文件替换必须等它结束。"""
    return AsyncTask.query.filter(
        AsyncTask.asset_id == asset_id,
        AsyncTask.status == 'running',
        AsyncTask.task_type.in_(('watermark_embed', 'blockchain_register')),
    ).first()


def _cancel_queued_tasks(asset_id):
    """文件已被替换，排队中的旧版本任务不再有意义。"""
    AsyncTask.query.filter(
        AsyncTask.asset_id == asset_id,
        AsyncTask.status == 'queued',
        AsyncTask.task_type.in_(('watermark_embed', 'blockchain_register')),
    ).update({
        'status': 'cancelled',
        'error_message': '文件已更新，旧版本任务自动取消',
        'finished_at': datetime.utcnow(),
    }, synchronize_session=False)


def _version_save_dir(asset_id):
    upload_root = os.path.abspath(current_app.config.get('UPLOAD_FOLDER', './uploads'))
    save_dir = os.path.join(upload_root, VERSION_DIRNAME, str(asset_id))
    os.makedirs(save_dir, exist_ok=True)
    return save_dir


def _hash_file(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def _generate_thumbnails(asset, file_path):
    """为图片资产生成缩略图；失败不阻断版本创建，返回 detail 路径或 None"""
    if asset.asset_type != 'image':
        return None
    try:
        from app.utils.thumbnails import generate_thumbnail_set
        detail_path, _ = generate_thumbnail_set(file_path, asset.id)
        return detail_path
    except Exception as exc:
        current_app.logger.warning(f'版本缩略图生成失败: {exc}', exc_info=True)
        return None


def _reset_watermark(asset):
    """文件变更后旧水印已失效，重置为未嵌入状态"""
    asset.watermark_status = 'none'
    asset.watermark_id = None
    asset.watermarked_path = None
    asset.watermark_embedded_at = None
    asset.vr_value = None


def _reset_chain(asset):
    """当前文件的旧存证不能代表新文件，资产主表回到未存证状态。

    历史证书与交易仍保留在 certificates / blockchain_transactions 表，
    版本列表会展示每个版本对应的证书。
    """
    asset.chain_status = 'none'
    asset.chain_tx_hash = None
    asset.chain_timestamp = None
    asset.certificate_id = None


def _apply_version_file(asset, file_path, file_hash, file_size, file_format,
                        thumbnail_path):
    """把资产主表指向新文件；旧存证与证书留在历史表，主表状态重置"""
    asset.storage_path = file_path
    asset.file_hash = file_hash
    asset.file_size = file_size
    asset.file_format = file_format
    asset.thumbnail_path = thumbnail_path
    _reset_watermark(asset)
    _reset_chain(asset)


def _create_version(asset, user_id, file_path, file_name, file_format,
                    file_size, file_hash, thumbnail_path, change_note):
    version = AssetVersion(
        asset_id=asset.id,
        version_no=_next_version_no(asset.id),
        file_path=file_path,
        file_name=file_name[:255] if file_name else None,
        file_format=file_format,
        file_size=file_size,
        file_hash=file_hash,
        thumbnail_path=thumbnail_path,
        change_note=change_note,
        created_by=user_id
    )
    db.session.add(version)
    _apply_version_file(
        asset, file_path, file_hash, file_size, file_format, thumbnail_path
    )
    _cancel_queued_tasks(asset.id)

    # 新文件未经水印与审核，不能继续以已发布/待审状态对外分发。
    # 退回草稿，要求重新水印 → 提交发布 → 审核。
    if asset.status in ('published', 'pending', 'rejected'):
        asset.status = 'draft'
        asset.publish_at = None
        asset.reject_reason = None

    return version


def _version_response(asset, version, message):
    return {
        'code': 200,
        'message': message,
        'data': {
            'version': version.to_dict(is_current=True),
            'asset': asset.to_dict()
        }
    }, 200


def _certificate_summary(certificate, is_current):
    return {
        'certificate_id': certificate.certificate_id,
        'tx_hash': certificate.tx_hash,
        'block_number': certificate.block_number,
        'file_hash': certificate.file_hash,
        'status': certificate.status,
        'version_no': certificate.version_no,
        'created_at': (
            certificate.created_at.isoformat() if certificate.created_at else None
        ),
        'is_current': is_current,
        'simulated': not blockchain_service.enabled
    }


def _attach_certificates(items, current_version_no):
    """为每个版本挂上对应证书（旧数据没有 version_id 时按文件指纹匹配）"""
    if not items:
        return
    asset_id = items[0]['asset_id']
    certificates = Certificate.query.filter_by(asset_id=asset_id).all()
    by_version = {
        cert.version_id: cert for cert in certificates if cert.version_id
    }
    by_hash = {
        cert.file_hash: cert
        for cert in certificates
        if cert.file_hash and cert.version_id is None
    }
    for item in items:
        certificate = by_version.get(item['id']) or by_hash.get(item['file_hash'])
        item['certificate'] = (
            _certificate_summary(
                certificate,
                certificate.version_no == current_version_no
                if certificate.version_no is not None
                else item['version_no'] == current_version_no,
            )
            if certificate else None
        )


class AssetVersionListResource(Resource):
    """资产版本列表 / 上传新版本"""

    @jwt_required()
    def get(self, asset_id):
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        asset = Asset.query.get(asset_id)

        if not asset:
            return {'code': 404, 'message': '资产不存在'}, 404
        if not _can_view(user, user_id, asset):
            return {'code': 404, 'message': '资产不存在'}, 404

        current_no = _max_version_no(asset.id)
        versions = AssetVersion.query.filter_by(asset_id=asset.id).order_by(
            AssetVersion.version_no.desc()
        ).all()
        items = [
            item.to_dict(is_current=item.version_no == current_no)
            for item in versions
        ]
        _attach_certificates(items, current_no)

        return {
            'code': 200,
            'data': {
                'items': items,
                'total': len(versions),
                'current_version_no': current_no
            }
        }, 200

    @jwt_required()
    def post(self, asset_id):
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        asset = Asset.query.get(asset_id)

        if not asset:
            return {'code': 404, 'message': '资产不存在'}, 404
        if not _can_manage(user, user_id, asset):
            return {'code': 403, 'message': '无权限上传新版本'}, 403
        if asset.status == 'deleted':
            return {'code': 400, 'message': '已删除的资产不能上传新版本'}, 400
        if _running_task(asset.id):
            return {
                'code': 409,
                'message': '该资产正在执行水印或存证任务，请等待完成后再上传新版本'
            }, 409

        if 'file' not in request.files:
            return {'code': 400, 'message': '未上传文件'}, 400

        file = request.files['file']
        original_name = file.filename or ''
        if not original_name:
            return {'code': 400, 'message': '未选择文件'}, 400

        # 扩展名必须符合资产类型（与资产上传逻辑一致）
        if not allowed_file(original_name, asset.asset_type):
            return {'code': 400, 'message': '不支持的文件类型'}, 400
        if '.' not in original_name:
            return {'code': 400, 'message': '文件名缺少扩展名'}, 400
        ext = original_name.rsplit('.', 1)[1].lower()
        if not validate_magic_bytes(file, ext):
            return {'code': 400, 'message': '文件内容与扩展名不匹配'}, 400

        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)
        max_size = current_app.config.get('MAX_CONTENT_LENGTH', 500 * 1024 * 1024)
        if file_size > max_size:
            return {
                'code': 400,
                'message': f'文件大小超过限制 ({max_size // 1024 // 1024}MB)'
            }, 400

        change_note = (request.form.get('change_note') or '').strip() or DEFAULT_CHANGE_NOTE
        if len(change_note) > 500:
            return {'code': 400, 'message': '变更说明不能超过500字符'}, 400

        file_hash = calculate_file_hash(file)

        save_dir = _version_save_dir(asset.id)
        file_path = os.path.join(save_dir, f'{uuid.uuid4().hex}.{ext}')
        file.save(file_path)
        file_size = os.path.getsize(file_path)

        thumbnail_path = _generate_thumbnails(asset, file_path)

        version = _create_version(
            asset, user_id,
            file_path=file_path,
            file_name=original_name,
            file_format=ext.upper(),
            file_size=file_size,
            file_hash=file_hash,
            thumbnail_path=thumbnail_path,
            change_note=change_note
        )
        db.session.commit()

        OperationLog.log(
            user=user,
            action='upload_version',
            module='asset',
            description=f'上传资产新版本: {asset.asset_code} v{version.version_no}',
            target_type='asset',
            target_id=asset_id,
            request=request
        )

        return _version_response(asset, version, '新版本上传成功')


class AssetVersionDownloadResource(Resource):
    """下载指定历史版本文件"""

    @jwt_required()
    def get(self, asset_id, version_id):
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        asset = Asset.query.get(asset_id)

        if not asset:
            return {'code': 404, 'message': '资产不存在'}, 404
        if not _can_manage(user, user_id, asset):
            return {'code': 403, 'message': '无下载权限'}, 403

        version = AssetVersion.query.get(version_id)
        if not version or version.asset_id != asset.id:
            return {'code': 404, 'message': '版本不存在'}, 404

        file_path = os.path.abspath(version.file_path or '')
        if not file_path or not os.path.isfile(file_path):
            return {'code': 404, 'message': '版本文件不存在'}, 404

        ext = (version.file_format or os.path.splitext(file_path)[1].lstrip('.')).lower()
        download_name = f'{asset.asset_code}-v{version.version_no}'
        if ext:
            download_name = f'{download_name}.{ext}'

        return send_file(file_path, as_attachment=True, download_name=download_name)


class AssetVersionRestoreResource(Resource):
    """把历史版本恢复为新的当前版本（不删除任何历史版本）"""

    @jwt_required()
    def post(self, asset_id, version_id):
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        asset = Asset.query.get(asset_id)

        if not asset:
            return {'code': 404, 'message': '资产不存在'}, 404
        if not _can_manage(user, user_id, asset):
            return {'code': 403, 'message': '无权限恢复版本'}, 403
        if asset.status == 'deleted':
            return {'code': 400, 'message': '已删除的资产不能恢复版本'}, 400
        if _running_task(asset.id):
            return {
                'code': 409,
                'message': '该资产正在执行水印或存证任务，请等待完成后再恢复版本'
            }, 409

        source = AssetVersion.query.get(version_id)
        if not source or source.asset_id != asset.id:
            return {'code': 404, 'message': '版本不存在'}, 404

        source_path = os.path.abspath(source.file_path or '')
        if not source_path or not os.path.isfile(source_path):
            return {'code': 404, 'message': '版本文件不存在'}, 404

        # 复制为新文件，保留历史版本文件不动
        ext = (source.file_format or os.path.splitext(source_path)[1].lstrip('.')).lower()
        save_dir = _version_save_dir(asset.id)
        file_name = f'{uuid.uuid4().hex}.{ext}' if ext else uuid.uuid4().hex
        file_path = os.path.join(save_dir, file_name)
        shutil.copy2(source_path, file_path)

        file_hash = _hash_file(file_path)
        file_size = os.path.getsize(file_path)
        thumbnail_path = _generate_thumbnails(asset, file_path)

        version = _create_version(
            asset, user_id,
            file_path=file_path,
            file_name=source.file_name,
            file_format=source.file_format or ext.upper() or None,
            file_size=file_size,
            file_hash=file_hash,
            thumbnail_path=thumbnail_path,
            change_note=f'恢复自 v{source.version_no}'
        )
        db.session.commit()

        OperationLog.log(
            user=user,
            action='restore_version',
            module='asset',
            description=(
                f'恢复资产历史版本: {asset.asset_code} '
                f'v{source.version_no} -> v{version.version_no}'
            ),
            target_type='asset',
            target_id=asset_id,
            request=request
        )

        return _version_response(asset, version, '版本恢复成功')
