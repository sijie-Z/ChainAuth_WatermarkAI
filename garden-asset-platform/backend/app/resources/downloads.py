"""下载记录与使用台账"""
from datetime import datetime, timedelta

from flask import request
from flask_jwt_extended import jwt_required, get_jwt_identity
from flask_restful import Resource
from sqlalchemy import func, or_, select

from app.extensions import db
from app.models import Asset, DownloadRecord, User

ADMIN_ROLES = ('admin', 'asset_admin', 'license_admin', 'adm1', 'adm2')


def _parse_date(value, field_name):
    if not value:
        return None, None
    try:
        return datetime.strptime(value, '%Y-%m-%d'), None
    except ValueError:
        return None, {'code': 400, 'message': f'{field_name}格式应为 YYYY-MM-DD'}


def _apply_filters(query, args):
    """应用资产、用户、日期与关键词筛选，返回 (query, error)"""
    asset_id = (args.get('asset_id') or '').strip()
    if asset_id:
        query = query.filter(DownloadRecord.asset_id == asset_id)

    user_id = args.get('user_id', type=int)
    if user_id:
        query = query.filter(DownloadRecord.user_id == user_id)

    start, error = _parse_date(args.get('start_date'), '开始日期')
    if error:
        return query, error
    end, error = _parse_date(args.get('end_date'), '结束日期')
    if error:
        return query, error

    if start:
        query = query.filter(DownloadRecord.created_at >= start)
    if end:
        query = query.filter(DownloadRecord.created_at < end + timedelta(days=1))

    keyword = (args.get('keyword') or '').strip()
    if keyword:
        like = f'%{keyword}%'
        matching_assets = select(Asset.id).where(
            or_(
                Asset.asset_code.ilike(like),
                Asset.title.ilike(like)
            )
        )
        query = query.filter(DownloadRecord.asset_id.in_(matching_assets))

    return query, None


def _serialize(record, include_user=False):
    asset = record.asset
    item = {
        'id': record.id,
        'created_at': record.created_at.isoformat() if record.created_at else None,
        'asset': {
            'id': record.asset_id,
            'asset_code': asset.asset_code if asset else None,
            'title': asset.title if asset else '（资产已删除）',
            'asset_type': asset.asset_type if asset else None,
            'file_format': asset.file_format if asset else None,
            'thumbnail_url': f'/api/assets/{asset.id}/thumbnail?size=card' if asset else None
        } if asset else None,
        'license': (
            {
                'id': record.license.id,
                'license_code': record.license.license_code,
                'license_type': record.license.license_type
            } if record.license else None
        )
    }
    if include_user:
        item['user'] = {
            'id': record.user_id,
            'username': record.user.username if record.user else None,
            'nickname': record.user.nickname if record.user else None
        }
    return item


class MyDownloadsResource(Resource):
    """当前用户的下载记录"""

    @jwt_required()
    def get(self):
        user_id = get_jwt_identity()
        page = max(request.args.get('page', 1, type=int), 1)
        per_page = min(max(request.args.get('per_page', 20, type=int), 1), 100)

        query = DownloadRecord.query.filter(
            DownloadRecord.user_id == user_id,
            DownloadRecord.asset_id.in_(select(Asset.id).where(Asset.status != 'deleted'))
        )
        query, error = _apply_filters(query, request.args)
        if error:
            return error, 400

        pagination = query.order_by(DownloadRecord.created_at.desc(), DownloadRecord.id.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )

        return {
            'code': 200,
            'data': {
                'items': [_serialize(record) for record in pagination.items],
                'total': pagination.total,
                'page': page,
                'per_page': per_page,
                'pages': pagination.pages
            }
        }, 200


class DownloadLedgerResource(Resource):
    """全平台下载台账（管理员）"""

    @jwt_required()
    def get(self):
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        if not user or user.role not in ADMIN_ROLES:
            return {'code': 403, 'message': '需要管理员权限'}, 403

        page = max(request.args.get('page', 1, type=int), 1)
        per_page = min(max(request.args.get('per_page', 20, type=int), 1), 100)

        query = DownloadRecord.query.filter(
            DownloadRecord.asset_id.in_(select(Asset.id).where(Asset.status != 'deleted'))
        )
        query, error = _apply_filters(query, request.args)
        if error:
            return error, 400

        total = query.count()
        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        today_count = query.filter(DownloadRecord.created_at >= today).count()

        subquery = query.with_entities(
            DownloadRecord.user_id, DownloadRecord.asset_id
        ).subquery()
        distinct_users = db.session.query(
            func.count(func.distinct(subquery.c.user_id))
        ).scalar() or 0
        distinct_assets = db.session.query(
            func.count(func.distinct(subquery.c.asset_id))
        ).scalar() or 0

        pagination = query.order_by(DownloadRecord.created_at.desc(), DownloadRecord.id.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )

        return {
            'code': 200,
            'data': {
                'items': [_serialize(record, include_user=True) for record in pagination.items],
                'total': total,
                'page': page,
                'per_page': per_page,
                'pages': pagination.pages,
                'summary': {
                    'total': total,
                    'today': today_count,
                    'users': distinct_users,
                    'assets': distinct_assets
                }
            }
        }, 200


class AssetDownloadSummaryResource(Resource):
    """单件资产的下载摘要（所有者/管理员）"""

    @jwt_required()
    def get(self, asset_id):
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        asset = Asset.query.get(asset_id)
        if not asset or asset.status == 'deleted':
            return {'code': 404, 'message': '资产不存在'}, 404

        is_owner = user_id in (asset.creator_id, asset.owner_id, asset.uploader_id)
        if not is_owner and (not user or user.role not in ADMIN_ROLES):
            return {'code': 403, 'message': '无权查看下载明细'}, 403

        records = DownloadRecord.query.filter_by(asset_id=asset_id).order_by(
            DownloadRecord.id.desc()
        ).limit(10).all()

        return {
            'code': 200,
            'data': {
                'total': DownloadRecord.query.filter_by(asset_id=asset_id).count(),
                'recent': [_serialize(record, include_user=True) for record in records]
            }
        }, 200
