"""资产公开分享链接

分享页用于把一件已发布资产连同证据链一起发给外部人员核验。
链接本身不可枚举，可选访问码、有效期与下载权限。
"""
import os
import secrets
from datetime import datetime, timedelta

from flask import request, send_file
from flask_restful import Resource
from flask_jwt_extended import jwt_required, get_jwt_identity
from werkzeug.security import generate_password_hash

from app.extensions import db
from app.models import Asset, AssetShare, User
from app.models.log import OperationLog
from app.services.evidence_service import build_evidence
from app.utils.middleware import rate_limit

ADMIN_ROLES = ('admin', 'asset_admin', 'license_admin', 'adm1', 'adm2')
MAX_EXPIRES_DAYS = 90
MIN_ACCESS_CODE_LENGTH = 4
MAX_ACCESS_CODE_LENGTH = 32


def _can_manage(user_id, user, asset):
    if not user:
        return False
    return user.role in ADMIN_ROLES or user_id in (
        asset.creator_id, asset.owner_id, asset.uploader_id
    )


def _generate_token():
    while True:
        token = secrets.token_urlsafe(18)
        if not AssetShare.query.filter_by(token=token).first():
            return token


def _public_asset(asset, share):
    """公开分享页可见的资产字段，不含存储路径与内部统计明细。"""
    tags = [tag.name or tag.tag_name for tag in asset.tags.all() if (tag.name or tag.tag_name)]
    return {
        'id': asset.id,
        'asset_code': asset.asset_code,
        'title': asset.title,
        'description': asset.description,
        'asset_type': asset.asset_type,
        'file_format': asset.file_format,
        'file_size': asset.file_size,
        'garden_id': asset.garden_id,
        'garden_name': asset.garden.name if asset.garden else None,
        'tags': tags,
        'thumbnail_url': f'/api/assets/{asset.id}/thumbnail?size=card',
        'created_at': asset.created_at.isoformat() if asset.created_at else None,
        'publish_at': asset.publish_at.isoformat() if asset.publish_at else None,
        'watermark_status': asset.watermark_status,
        'watermark_id': asset.watermark_id,
        'chain_status': asset.chain_status,
        'chain_tx_hash': asset.chain_tx_hash,
        'certificate_id': asset.certificate_id,
        'license_count': asset.license_count or 0,
        'download_count': asset.download_count or 0,
        'owner_name': (
            (asset.owner.nickname or asset.owner.username) if asset.owner else None
        ),
        'share': {
            'token': share.token,
            'allow_download': bool(share.allow_download),
            'max_downloads': share.max_downloads,
            'download_count': share.download_count or 0,
            'download_remaining': (
                None if share.max_downloads is None
                else max(share.max_downloads - (share.download_count or 0), 0)
            ),
            'expires_at': share.expires_at.isoformat() if share.expires_at else None,
            'has_access_code': bool(share.access_code_hash),
            'created_at': share.created_at.isoformat() if share.created_at else None
        }
    }


def _share_error(share):
    if share.status == 'revoked':
        return {'code': 410, 'message': '分享链接已撤销'}, 410
    if share.is_expired:
        return {'code': 410, 'message': '分享链接已过期'}, 410
    return None


class AssetShareListResource(Resource):
    """某件资产的分享链接列表 / 新建分享"""

    @jwt_required()
    def get(self, asset_id):
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        asset = Asset.query.get(asset_id)
        if not asset or asset.status == 'deleted':
            return {'code': 404, 'message': '资产不存在'}, 404
        if not _can_manage(user_id, user, asset):
            return {'code': 403, 'message': '无权查看该资产的分享链接'}, 403

        shares = AssetShare.query.filter_by(asset_id=asset_id).order_by(
            AssetShare.id.desc()
        ).all()
        return {
            'code': 200,
            'data': [share.to_dict() for share in shares]
        }, 200

    @jwt_required()
    def post(self, asset_id):
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        asset = Asset.query.get(asset_id)
        if not asset or asset.status == 'deleted':
            return {'code': 404, 'message': '资产不存在'}, 404
        if not _can_manage(user_id, user, asset):
            return {'code': 403, 'message': '无权分享该资产'}, 403
        if asset.status != 'published':
            return {'code': 400, 'message': '仅已发布资产可以创建公开分享'}, 400

        data = request.get_json(silent=True) or {}

        expires_in_days = data.get('expires_in_days', 7)
        try:
            expires_in_days = int(expires_in_days)
        except (TypeError, ValueError):
            return {'code': 400, 'message': '有效期必须是整数天'}, 400
        if expires_in_days < 0 or expires_in_days > MAX_EXPIRES_DAYS:
            return {'code': 400, 'message': f'有效期需在 0-{MAX_EXPIRES_DAYS} 天之间'}, 400

        access_code = (data.get('access_code') or '').strip()
        if access_code:
            if not (MIN_ACCESS_CODE_LENGTH <= len(access_code) <= MAX_ACCESS_CODE_LENGTH):
                return {
                    'code': 400,
                    'message': f'访问码长度需为 {MIN_ACCESS_CODE_LENGTH}-{MAX_ACCESS_CODE_LENGTH} 位'
                }, 400

        allow_download = bool(data.get('allow_download', False))
        max_downloads = data.get('max_downloads')
        if allow_download and max_downloads not in (None, '', 0, '0'):
            try:
                max_downloads = int(max_downloads)
            except (TypeError, ValueError):
                return {'code': 400, 'message': '下载次数上限必须是整数'}, 400
            if max_downloads < 1 or max_downloads > 1000:
                return {'code': 400, 'message': '下载次数上限需在 1-1000 之间'}, 400
        else:
            max_downloads = None

        from datetime import datetime, timedelta
        share = AssetShare(
            token=_generate_token(),
            asset_id=asset_id,
            creator_id=user_id,
            access_code_hash=generate_password_hash(access_code) if access_code else None,
            expires_at=(
                datetime.utcnow() + timedelta(days=expires_in_days)
                if expires_in_days else None
            ),
            allow_download=allow_download,
            max_downloads=max_downloads
        )
        db.session.add(share)
        db.session.commit()

        OperationLog.log(
            user=user,
            action='share_create',
            module='asset',
            description=f'创建分享链接: {asset.asset_code}',
            target_type='asset',
            target_id=asset_id,
            request=request,
            extra_data={'share_id': share.id, 'expires_in_days': expires_in_days}
        )

        return {
            'code': 200,
            'message': '分享链接已创建',
            'data': share.to_dict(include_asset=True)
        }, 200


class ShareResource(Resource):
    """撤销分享链接"""

    @jwt_required()
    def delete(self, share_id):
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        share = AssetShare.query.get(share_id)
        if not share:
            return {'code': 404, 'message': '分享链接不存在'}, 404
        if not _can_manage(user_id, user, share.asset):
            return {'code': 403, 'message': '无权撤销该分享链接'}, 403

        if share.status == 'revoked':
            return {'code': 200, 'message': '分享链接已撤销'}, 200

        share.status = 'revoked'
        db.session.commit()

        OperationLog.log(
            user=user,
            action='share_revoke',
            module='asset',
            description=f'撤销分享链接: {share.asset.asset_code if share.asset else share.asset_id}',
            target_type='asset',
            target_id=share.asset_id,
            request=request,
            extra_data={'share_id': share.id}
        )
        return {'code': 200, 'message': '分享链接已撤销'}, 200


def _resolve_share(token):
    share = AssetShare.query.filter_by(token=token).first()
    if not share:
        return None, ({'code': 404, 'message': '分享链接不存在'}, 404)
    error = _share_error(share)
    if error:
        return None, error
    return share, None


def _check_code(share):
    if not share.access_code_hash:
        return None
    code = request.args.get('code') or request.headers.get('X-Share-Code') or ''
    if not share.check_access_code(code):
        return {
            'code': 401,
            'message': '该分享需要访问码',
            'data': {'requires_code': True}
        }, 401
    return None


class PublicShareResource(Resource):
    """公开分享页数据（免登录）"""

    @rate_limit(limit=60, window=60)
    def get(self, token):
        share, error = _resolve_share(token)
        if error:
            return error

        asset = Asset.query.get(share.asset_id)
        if not asset or asset.status != 'published':
            return {'code': 410, 'message': '分享的资产已不可访问'}, 410

        code_error = _check_code(share)
        if code_error:
            return code_error

        share.view_count = (share.view_count or 0) + 1
        share.last_viewed_at = datetime.utcnow()
        db.session.commit()

        evidence = build_evidence(asset, include_private=False)
        return {
            'code': 200,
            'data': {
                'asset': _public_asset(asset, share),
                'evidence': evidence
            }
        }, 200


class PublicShareDownloadResource(Resource):
    """公开分享下载（受分享设置限制）"""

    @rate_limit(limit=20, window=60)
    def get(self, token):
        share, error = _resolve_share(token)
        if error:
            return error

        asset = Asset.query.get(share.asset_id)
        if not asset or asset.status != 'published':
            return {'code': 410, 'message': '分享的资产已不可访问'}, 410

        code_error = _check_code(share)
        if code_error:
            return code_error

        if not share.allow_download:
            return {'code': 403, 'message': '该分享未开放下载'}, 403
        if share.is_download_limited:
            return {'code': 410, 'message': '该分享的下载次数已用完'}, 410

        file_path = os.path.abspath(asset.watermarked_path or asset.storage_path or '')
        if not file_path or not os.path.exists(file_path):
            return {'code': 404, 'message': '文件不存在'}, 404

        share.download_count = (share.download_count or 0) + 1
        asset.download_count = (asset.download_count or 0) + 1
        db.session.commit()

        OperationLog.log(
            user=None,
            action='share_download',
            module='asset',
            description=f'通过分享链接下载: {asset.asset_code}',
            target_type='asset',
            target_id=asset.id,
            request=request,
            extra_data={'share_id': share.id}
        )

        download_name = (
            f"{asset.asset_code}.{asset.file_format.lower()}"
            if asset.file_format else asset.asset_code
        )
        return send_file(file_path, as_attachment=True, download_name=download_name)
