"""资产证据链接口"""
from flask_jwt_extended import jwt_required, get_jwt_identity
from flask_restful import Resource

from app.models import Asset, User
from app.services.evidence_service import build_evidence

ADMIN_ROLES = ('admin', 'asset_admin', 'license_admin', 'adm1', 'adm2')


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
