"""授权使用报表

聚合授权状态、配额、下载/拒绝趋势与版本过期情况，供后台“使用报表”页使用。
"""
from datetime import datetime, timedelta

from flask import request
from flask_jwt_extended import get_jwt_identity, jwt_required
from flask_restful import Resource
from sqlalchemy import and_, func, or_

from app.extensions import db
from app.models import Asset, AssetVersion, DownloadRecord, License, User
from app.services.license_scope import scope_summary

ADMIN_ROLES = ('admin', 'asset_admin', 'license_admin', 'adm1', 'adm2')

DENIAL_LABELS = {
    'version': '授权版本过期',
    'quota': '下载次数用完',
    'territory': '超出授权地域',
    'format': '格式不在范围',
    'purpose': '用途不符',
    'no_license': '无有效授权',
    'other': '其他原因',
}


def _denial_category(reason):
    text = reason or ''
    if '版本' in text or ('v' in text and '当前' in text):
        return 'version'
    if '次数' in text:
        return 'quota'
    if '地域' in text:
        return 'territory'
    if '格式' in text:
        return 'format'
    if '用途' in text:
        return 'purpose'
    if '无下载权限' in text or '申请授权' in text:
        return 'no_license'
    return 'other'


def _latest_versions(asset_ids):
    if not asset_ids:
        return {}
    versions = AssetVersion.query.filter(
        AssetVersion.asset_id.in_(list(asset_ids))
    ).order_by(
        AssetVersion.asset_id.asc(), AssetVersion.version_no.desc()
    ).all()
    latest = {}
    for version in versions:
        latest.setdefault(version.asset_id, version)
    return latest


def _download_stats(license_ids):
    stats = {}
    if not license_ids:
        return stats
    rows = db.session.query(
        DownloadRecord.license_id,
        DownloadRecord.status,
        func.count(DownloadRecord.id),
        func.max(DownloadRecord.created_at),
    ).filter(
        DownloadRecord.license_id.in_(list(license_ids))
    ).group_by(
        DownloadRecord.license_id, DownloadRecord.status
    ).all()
    for license_id, status, count, last_at in rows:
        entry = stats.setdefault(license_id, {
            'success': 0, 'denied': 0, 'last_download_at': None
        })
        if status == 'denied':
            entry['denied'] += count
        else:
            entry['success'] += count
            if last_at and (
                entry['last_download_at'] is None
                or last_at > entry['last_download_at']
            ):
                entry['last_download_at'] = last_at
    return stats


class LicenseUsageReportResource(Resource):
    """授权使用报表：状态、配额、拒绝原因与版本过期"""

    @jwt_required()
    def get(self):
        user = User.query.get(get_jwt_identity())
        if not user or user.role not in ADMIN_ROLES:
            return {'code': 403, 'message': '需要管理员权限'}, 403

        now = datetime.utcnow()
        try:
            days = int(request.args.get('days', 30))
        except (TypeError, ValueError):
            return {'code': 400, 'message': 'days 必须是整数'}, 400
        days = min(max(days, 1), 365)
        start = (now - timedelta(days=days - 1)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )

        status = (request.args.get('status') or '').strip()
        if status and status not in ('active', 'expired', 'revoked', 'pending'):
            return {'code': 400, 'message': '无效的授权状态'}, 400
        keyword = (request.args.get('keyword') or '').strip()
        version_filter = (request.args.get('version_outdated') or '').strip()
        if version_filter not in ('', '0', '1'):
            return {'code': 400, 'message': 'version_outdated 只能是 0 或 1'}, 400

        query = License.query
        if status == 'active':
            query = query.filter(
                License.status == 'active',
                or_(License.end_time.is_(None), License.end_time > now),
            )
        elif status == 'expired':
            query = query.filter(or_(
                License.status == 'expired',
                and_(License.status == 'active', License.end_time <= now),
            ))
        elif status in ('revoked', 'pending'):
            query = query.filter(License.status == status)

        if keyword:
            like = f'%{keyword}%'
            asset_ids = db.session.query(Asset.id).filter(or_(
                Asset.asset_code.ilike(like), Asset.title.ilike(like)
            ))
            user_ids = db.session.query(User.id).filter(
                User.username.ilike(like)
            )
            query = query.filter(or_(
                License.license_code.ilike(like),
                License.asset_id.in_(asset_ids),
                License.licensee_id.in_(user_ids),
            ))

        licenses = query.order_by(License.created_at.desc()).all()
        asset_ids = {row.asset_id for row in licenses}
        latest = _latest_versions(asset_ids)
        stats = _download_stats([row.id for row in licenses])

        rows = []
        for license_row in licenses:
            current_version = latest.get(license_row.asset_id)
            outdated = bool(
                license_row.version_id
                and (
                    not current_version
                    or current_version.id != license_row.version_id
                )
            )
            if version_filter == '1' and not outdated:
                continue
            if version_filter == '0' and outdated:
                continue
            stat = stats.get(license_row.id, {})
            data = license_row.to_dict()
            data.update({
                'licensee_name': (
                    license_row.licensee.username if license_row.licensee else None
                ),
                'asset_code': (
                    license_row.asset.asset_code if license_row.asset else None
                ),
                'asset_title': (
                    license_row.asset.title if license_row.asset else None
                ),
                'current_version_no': (
                    current_version.version_no if current_version else None
                ),
                'version_outdated': outdated,
                'download_count': max(
                    license_row.download_count or 0,
                    stat.get('success', 0),
                ),
                'denied_count': stat.get('denied', 0),
                'last_download_at': (
                    stat['last_download_at'].isoformat()
                    if stat.get('last_download_at') else None
                ),
                'scope_summary': scope_summary(license_row),
            })
            rows.append(data)

        total = len(rows)
        page = max(request.args.get('page', 1, type=int), 1)
        per_page = min(max(request.args.get('per_page', 20, type=int), 1), 100)
        page_rows = rows[(page - 1) * per_page: page * per_page]

        all_licenses = License.query.all()
        all_asset_ids = {row.asset_id for row in all_licenses}
        all_latest = _latest_versions(all_asset_ids)
        all_stats = _download_stats([row.id for row in all_licenses])
        outdated_total = sum(
            1 for row in all_licenses
            if row.version_id and (
                not all_latest.get(row.asset_id)
                or all_latest[row.asset_id].id != row.version_id
            )
        )
        active_total = sum(
            1 for row in all_licenses
            if row.status == 'active'
            and (row.end_time is None or row.end_time > now)
        )
        expiring_total = sum(
            1 for row in all_licenses
            if row.status == 'active'
            and row.end_time is not None
            and now < row.end_time <= now + timedelta(days=30)
        )
        expired_total = sum(
            1 for row in all_licenses
            if row.status == 'expired'
            or (row.status == 'active' and row.end_time and row.end_time <= now)
        )
        revoked_total = sum(1 for row in all_licenses if row.status == 'revoked')
        pending_total = sum(1 for row in all_licenses if row.status == 'pending')
        quota_licenses = [row for row in all_licenses if row.max_downloads is not None]
        quota_total = sum(row.max_downloads or 0 for row in quota_licenses)
        quota_used = sum(row.download_count or 0 for row in quota_licenses)

        download_rows = db.session.query(
            DownloadRecord.status,
            func.count(DownloadRecord.id),
        ).filter(
            DownloadRecord.license_id.isnot(None),
            DownloadRecord.created_at >= start,
        ).group_by(DownloadRecord.status).all()
        downloads = sum(
            count for status_value, count in download_rows
            if status_value != 'denied'
        )
        denied = sum(
            count for status_value, count in download_rows
            if status_value == 'denied'
        )
        downloads_today = DownloadRecord.query.filter(
            DownloadRecord.license_id.isnot(None),
            DownloadRecord.status != 'denied',
            DownloadRecord.created_at >= now.replace(
                hour=0, minute=0, second=0, microsecond=0
            ),
        ).count()

        trend_rows = db.session.query(
            func.date(DownloadRecord.created_at),
            DownloadRecord.status,
            func.count(DownloadRecord.id),
        ).filter(
            DownloadRecord.license_id.isnot(None),
            DownloadRecord.created_at >= start,
        ).group_by(
            func.date(DownloadRecord.created_at), DownloadRecord.status
        ).all()
        trend_map = {}
        for date_value, status_value, count in trend_rows:
            entry = trend_map.setdefault(
                str(date_value), {'success': 0, 'denied': 0}
            )
            if status_value == 'denied':
                entry['denied'] += count
            else:
                entry['success'] += count
        trend = []
        for offset in range(days):
            date_value = (start + timedelta(days=offset)).strftime('%Y-%m-%d')
            entry = trend_map.get(date_value, {'success': 0, 'denied': 0})
            trend.append({
                'date': date_value,
                'success': entry['success'],
                'denied': entry['denied'],
            })

        denied_records = DownloadRecord.query.filter(
            DownloadRecord.license_id.isnot(None),
            DownloadRecord.status == 'denied',
            DownloadRecord.created_at >= start,
        ).all()
        category_counts = {}
        for record in denied_records:
            category = _denial_category(record.denial_reason)
            category_counts[category] = category_counts.get(category, 0) + 1
        denial_categories = [
            {
                'key': key,
                'label': DENIAL_LABELS.get(key, key),
                'count': category_counts.get(key, 0),
            }
            for key in DENIAL_LABELS
            if category_counts.get(key)
        ]
        denial_categories.sort(key=lambda item: item['count'], reverse=True)

        asset_stats = {}
        for license_row in all_licenses:
            item = asset_stats.setdefault(license_row.asset_id, {
                'asset_id': license_row.asset_id,
                'asset_code': (
                    license_row.asset.asset_code if license_row.asset else None
                ),
                'asset_title': (
                    license_row.asset.title if license_row.asset else None
                ),
                'license_count': 0,
                'downloads': 0,
                'denied': 0,
            })
            stat = all_stats.get(license_row.id, {})
            item['license_count'] += 1
            item['downloads'] += max(
                license_row.download_count or 0, stat.get('success', 0)
            )
            item['denied'] += stat.get('denied', 0)
        top_assets = sorted(
            asset_stats.values(),
            key=lambda item: (item['downloads'] + item['denied'], item['denied']),
            reverse=True,
        )[:8]

        return {
            'code': 200,
            'data': {
                'summary': {
                    'total': len(all_licenses),
                    'active': active_total,
                    'expiring_30d': expiring_total,
                    'expired': expired_total,
                    'revoked': revoked_total,
                    'pending': pending_total,
                    'version_outdated': outdated_total,
                    'quota_licenses': len(quota_licenses),
                    'quota_total': quota_total,
                    'quota_used': quota_used,
                    'downloads': downloads,
                    'denied': denied,
                    'downloads_today': downloads_today,
                    'days': days,
                },
                'rows': {
                    'items': page_rows,
                    'total': total,
                    'page': page,
                    'per_page': per_page,
                },
                'trend': trend,
                'denial_categories': denial_categories,
                'top_assets': top_assets,
                'generated_at': now.isoformat(),
            }
        }, 200
