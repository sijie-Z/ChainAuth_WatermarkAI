"""资产证据链接口"""
import os
import shutil
import uuid
from urllib.parse import quote

from flask import Response, current_app, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from flask_restful import Resource

from app.models import Asset, User
from app.models.log import OperationLog
from app.services.evidence_service import build_evidence
from app.services.evidence_package_service import build_evidence_package
from app.services.evidence_verify_service import verify_evidence_package
from app.utils.middleware import rate_limit

ADMIN_ROLES = ('admin', 'asset_admin', 'license_admin', 'adm1', 'adm2')
PACKAGE_ROLES = ('admin', 'asset_admin')


def _stream_package(package):
    """流式返回 ZIP，并在客户端读取结束/断开后清理临时目录。"""
    try:
        with open(package['path'], 'rb') as handle:
            while True:
                chunk = handle.read(256 * 1024)
                if not chunk:
                    break
                yield chunk
    finally:
        shutil.rmtree(package['workdir'], ignore_errors=True)


class AssetEvidenceResource(Resource):
    """资产的上传—水印—存证—证书—授权—下载证据链"""

    @jwt_required()
    def get(self, asset_id):
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        asset = Asset.query.get(asset_id)

        if not asset:
            return {'code': 404, 'message': '资产不存在'}, 404

        is_owner = user_id in (asset.creator_id, asset.owner_id, asset.uploader_id)
        is_admin = bool(user and user.role in ADMIN_ROLES)

        if asset.status == 'deleted' and not is_admin:
            return {'code': 404, 'message': '资产不存在'}, 404
        if asset.status != 'published' and not (is_owner or is_admin):
            return {'code': 403, 'message': '资产未发布'}, 403

        data = build_evidence(asset, include_private=is_owner or is_admin)
        data['asset'] = {
            'id': asset.id,
            'asset_code': asset.asset_code,
            'title': asset.title,
            'status': asset.status
        }
        return {'code': 200, 'data': data}, 200


class AssetEvidencePackageResource(Resource):
    """导出资产证据包（ZIP）

    仅所有者与资产管理员可导出：包内可能包含当前原文件副本。
    """

    @rate_limit(limit=6, window=60)
    @jwt_required()
    def get(self, asset_id):
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        asset = Asset.query.get(asset_id)

        if not asset:
            return {'code': 404, 'message': '资产不存在'}, 404

        is_owner = user_id in (asset.creator_id, asset.owner_id, asset.uploader_id)
        is_admin = bool(user and user.role in PACKAGE_ROLES)

        if asset.status == 'deleted' and not is_admin:
            return {'code': 404, 'message': '资产不存在'}, 404
        if not (is_owner or is_admin):
            return {'code': 403, 'message': '仅资产所有者或资产管理员可导出证据包'}, 403

        include_files = (
            (request.args.get('include_files') or '1').lower()
            not in ('0', 'false', 'no')
        )
        try:
            package = build_evidence_package(
                asset, user=user, include_files=include_files
            )
        except Exception:
            current_app.logger.exception('导出证据包失败: %s', asset.asset_code)
            return {'code': 500, 'message': '证据包生成失败，请稍后重试'}, 500

        OperationLog.log(
            user=user,
            action='export_evidence_package',
            module='asset',
            description=f'导出证据包: {asset.asset_code}',
            target_type='asset',
            target_id=asset.id,
            request=request,
            extra_data={
                'included_files': package['included_files'],
                'omitted': package['omitted'],
            },
        )

        try:
            size = os.path.getsize(package['path'])
        except OSError:
            shutil.rmtree(package['workdir'], ignore_errors=True)
            return {'code': 500, 'message': '证据包生成失败，请稍后重试'}, 500

        filename = package['filename']
        headers = {
            'Content-Disposition': (
                f"attachment; filename={filename}; "
                f"filename*=UTF-8''{quote(filename)}"
            ),
            'Content-Length': str(size),
            'Cache-Control': 'no-store',
            'X-Evidence-Package-Files': str(package['included_files']),
            'X-Evidence-Package-Omitted': '1' if package['omitted'] else '0',
        }
        response = Response(
            _stream_package(package),
            mimetype='application/zip',
            headers=headers,
        )
        # 生成器被消费时会清理；再加一层关闭回调，覆盖客户端提前断开的场景
        response.call_on_close(
            lambda: shutil.rmtree(package['workdir'], ignore_errors=True)
        )
        return response


class EvidencePackageVerifyResource(Resource):
    """公开核验证据包（结构、校验和与平台登记匹配）"""

    @rate_limit(limit=10, window=60)
    def post(self):
        if 'file' not in request.files:
            return {'code': 400, 'message': '未上传证据包'}, 400
        file = request.files['file']
        if not file.filename or not file.filename.lower().endswith('.zip'):
            return {'code': 400, 'message': '请上传 ZIP 证据包'}, 400

        max_bytes = current_app.config.get(
            'EVIDENCE_VERIFY_MAX_BYTES', 20 * 1024 * 1024
        )
        file.seek(0, os.SEEK_END)
        size = file.tell()
        file.seek(0)
        if size > max_bytes:
            return {
                'code': 400,
                'message': f'证据包大小超过限制 ({max_bytes // 1024 // 1024}MB)'
            }, 400

        temp_root = os.path.join(
            current_app.config.get('UPLOAD_FOLDER', './uploads'),
            'evidence_verify_tmp'
        )
        os.makedirs(temp_root, exist_ok=True)
        temp_path = os.path.join(temp_root, f'verify_{uuid.uuid4().hex}.zip')
        file.save(temp_path)

        try:
            result = verify_evidence_package(temp_path)
            return {
                'code': 200,
                'message': '证据包核验完成',
                'data': result,
            }, 200
        except ValueError as exc:
            return {'code': 400, 'message': str(exc)}, 400
        except Exception:
            current_app.logger.exception('证据包核验失败')
            return {'code': 500, 'message': '证据包核验失败，请稍后重试'}, 500
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)
