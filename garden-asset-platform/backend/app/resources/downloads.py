"""下载记录与使用台账"""
from datetime import datetime, timedelta

from flask import request
from flask_jwt_extended import jwt_required, get_jwt_identity
from flask_restful import Resource
from sqlalchemy import Integer, func, literal, or_, select

from app.extensions import db
from app.models import (
    Asset, AssetShare, DownloadRecord, License, ShareDownload, User
)

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
    """全平台下载台账（授权下载 + 匿名分享下载）"""

    @jwt_required()
    def get(self):
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        if not user or user.role not in ADMIN_ROLES:
            return {'code': 403, 'message': '需要管理员权限'}, 403

        page = max(request.args.get('page', 1, type=int), 1)
        per_page = min(max(request.args.get('per_page', 20, type=int), 1), 100)

        channel = (request.args.get('channel') or 'all').strip()
        if channel not in ('all', 'license', 'share'):
            return {'code': 400, 'message': '无效的下载渠道'}, 400

        start, error = _parse_date(request.args.get('start_date'), '开始日期')
        if error:
            return error, 400
        end, error = _parse_date(request.args.get('end_date'), '结束日期')
        if error:
            return error, 400

        asset_id = (request.args.get('asset_id') or '').strip()
        user_id_filter = request.args.get('user_id', type=int)
        keyword = (request.args.get('keyword') or '').strip()

        visible_assets = select(Asset.id).where(Asset.status != 'deleted')
        matching_assets = None
        if keyword:
            like = f'%{keyword}%'
            matching_assets = select(Asset.id).where(
                or_(Asset.asset_code.ilike(like), Asset.title.ilike(like))
            )

        def apply_common(query, model):
            query = query.filter(model.asset_id.in_(visible_assets))
            if asset_id:
                query = query.filter(model.asset_id == asset_id)
            if start:
                query = query.filter(model.created_at >= start)
            if end:
                query = query.filter(model.created_at < end + timedelta(days=1))
            if matching_assets is not None:
                query = query.filter(model.asset_id.in_(matching_assets))
            return query

        license_query = db.session.query(
            literal('license').label('channel'),
            DownloadRecord.id.label('record_id'),
            DownloadRecord.created_at.label('created_at'),
            DownloadRecord.asset_id.label('asset_id'),
            DownloadRecord.user_id.label('user_id'),
            DownloadRecord.license_id.label('license_id'),
            literal(None).cast(Integer).label('share_id')
        )
        license_query = apply_common(license_query, DownloadRecord)
        if user_id_filter:
            license_query = license_query.filter(DownloadRecord.user_id == user_id_filter)

        share_query = db.session.query(
            literal('share').label('channel'),
            ShareDownload.id.label('record_id'),
            ShareDownload.created_at.label('created_at'),
            ShareDownload.asset_id.label('asset_id'),
            literal(None).cast(Integer).label('user_id'),
            literal(None).cast(Integer).label('license_id'),
            ShareDownload.share_id.label('share_id')
        )
        share_query = apply_common(share_query, ShareDownload)

        include_license = channel in ('all', 'license') and not (
            channel == 'share'
        )
        include_share = channel in ('all', 'share') and not user_id_filter

        queries = []
        if include_license:
            queries.append(license_query)
        if include_share:
            queries.append(share_query)
        if not queries:
            return {
                'code': 200,
                'data': {
                    'items': [], 'total': 0, 'page': page,
                    'per_page': per_page, 'pages': 0,
                    'summary': {
                        'total': 0, 'today': 0, 'users': 0, 'assets': 0,
                        'license_total': 0, 'share_total': 0
                    }
                }
            }, 200

        union = queries[0].union_all(queries[1]).subquery() if len(queries) == 2 \
            else queries[0].subquery()
        base_query = db.session.query(union)

        total = base_query.count()
        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        today_count = base_query.filter(union.c.created_at >= today).count()
        distinct_users = db.session.query(
            func.count(func.distinct(union.c.user_id))
        ).scalar() or 0
        distinct_assets = db.session.query(
            func.count(func.distinct(union.c.asset_id))
        ).scalar() or 0

        rows = base_query.order_by(
            union.c.created_at.desc(), union.c.record_id.desc()
        ).offset((page - 1) * per_page).limit(per_page).all()

        asset_map = {
            item.id: item for item in Asset.query.filter(
                Asset.id.in_({row.asset_id for row in rows})
            ).all()
        } if rows else {}
        user_map = {
            item.id: item for item in User.query.filter(
                User.id.in_({
                    row.user_id for row in rows if row.user_id is not None
                })
            ).all()
        } if rows else {}
        license_map = {
            item.id: item for item in License.query.filter(
                License.id.in_({
                    row.license_id for row in rows if row.license_id is not None
                })
            ).all()
        } if rows else {}
        share_map = {
            item.id: item for item in AssetShare.query.filter(
                AssetShare.id.in_({
                    row.share_id for row in rows if row.share_id is not None
                })
            ).all()
        } if rows else {}

        items = []
        for row in rows:
            asset = asset_map.get(row.asset_id)
            account = user_map.get(row.user_id)
            license_row = license_map.get(row.license_id)
            share = share_map.get(row.share_id)
            items.append({
                'id': f'{row.channel}-{row.record_id}',
                'record_id': row.record_id,
                'channel': row.channel,
                'channel_label': '授权下载' if row.channel == 'license' else '分享下载',
                'created_at': row.created_at.isoformat() if row.created_at else None,
                'asset': {
                    'id': row.asset_id,
                    'asset_code': asset.asset_code if asset else None,
                    'title': asset.title if asset else '（资产已删除）',
                    'asset_type': asset.asset_type if asset else None,
                    'file_format': asset.file_format if asset else None,
                    'thumbnail_url': (
                        f'/api/assets/{asset.id}/thumbnail?size=card'
                        if asset else None
                    )
                } if asset else None,
                'user': {
                    'id': row.user_id,
                    'username': account.username if account else None,
                    'nickname': account.nickname if account else None
                } if account else None,
                'license': {
                    'id': license_row.id,
                    'license_code': license_row.license_code,
                    'license_type': license_row.license_type
                } if license_row else None,
                'share': {
                    'id': share.id,
                    'has_access_code': bool(share.access_code_hash)
                } if share else None
            })

        license_total = license_query.count() if include_license else 0
        share_total = share_query.count() if include_share else 0
        license_today = (
            license_query.filter(DownloadRecord.created_at >= today).count()
            if include_license else 0
        )
        share_today = (
            share_query.filter(ShareDownload.created_at >= today).count()
            if include_share else 0
        )

        return {
            'code': 200,
            'data': {
                'items': items,
                'total': total,
                'page': page,
                'per_page': per_page,
                'pages': (total + per_page - 1) // per_page if total else 0,
                'summary': {
                    'total': total,
                    'today': today_count,
                    'users': distinct_users,
                    'assets': distinct_assets,
                    'license_total': license_total,
                    'license_today': license_today,
                    'share_total': share_total,
                    'share_today': share_today
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
