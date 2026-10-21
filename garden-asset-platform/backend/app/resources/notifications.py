"""站内待办提醒

不新增通知表：按当前用户角色与业务状态实时汇总需要处理的事项。
"""
from datetime import datetime, timedelta

from flask_jwt_extended import get_jwt_identity, jwt_required
from flask_restful import Resource

from app.models import Asset, License, LicenseApplication, User

ADMIN_ROLES = ('admin', 'asset_admin', 'license_admin', 'adm1', 'adm2')


class NotificationsResource(Resource):
    """当前用户的待办与状态提醒"""

    @jwt_required()
    def get(self):
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        if not user:
            return {'code': 404, 'message': '用户不存在'}, 404

        items = []
        now = datetime.utcnow()

        if user.role in ADMIN_ROLES:
            pending_licenses = LicenseApplication.query.filter(
                LicenseApplication.status.in_(['pending', 'adm1_approved'])
            ).count()
            if pending_licenses:
                items.append({
                    'id': 'pending-licenses',
                    'type': 'approval',
                    'title': f'{pending_licenses} 条授权申请待审批',
                    'description': '一级审批与二级复核会在这里汇总',
                    'link': '/admin/license/pending',
                    'count': pending_licenses,
                    'time': None
                })

            pending_assets = Asset.query.filter_by(status='pending').count()
            if pending_assets:
                items.append({
                    'id': 'pending-assets',
                    'type': 'asset',
                    'title': f'{pending_assets} 件资产待发布审核',
                    'description': '审核通过后资产才会进入公开档案',
                    'link': '/admin/assets?status=pending',
                    'count': pending_assets,
                    'time': None
                })

        applications = LicenseApplication.query.filter(
            LicenseApplication.applicant_id == user_id,
            LicenseApplication.status.in_(['pending', 'adm1_approved', 'rejected'])
        ).order_by(LicenseApplication.updated_at.desc(), LicenseApplication.created_at.desc()).limit(5).all()

        for application in applications:
            asset_title = application.asset.title if application.asset else '资产'
            if application.status == 'pending':
                title = '授权申请待一级审批'
                description = f'{asset_title} · 已提交，等待审批员处理'
                item_type = 'info'
            elif application.status == 'adm1_approved':
                title = '授权申请待二级复核'
                description = f'{asset_title} · 一级审批已通过'
                item_type = 'info'
            else:
                title = '授权申请未通过'
                description = f'{asset_title} · {application.adm2_review_comment or application.adm1_review_comment or "请查看申请详情"}'
                item_type = 'warning'
            items.append({
                'id': f'application-{application.id}',
                'type': item_type,
                'title': title,
                'description': description,
                'link': '/license/my?tab=pending' if application.status != 'rejected' else '/license/my?tab=rejected',
                'count': 1,
                'time': (application.updated_at or application.created_at).isoformat()
            })

        expiring = License.query.filter(
            License.licensee_id == user_id,
            License.status == 'active',
            License.end_time.isnot(None),
            License.end_time >= now,
            License.end_time <= now + timedelta(days=30)
        ).order_by(License.end_time.asc()).limit(5).all()

        for license in expiring:
            items.append({
                'id': f'license-{license.id}',
                'type': 'warning',
                'title': '授权即将到期',
                'description': f'{license.asset.title if license.asset else "资产"} · {license.end_time:%Y-%m-%d} 到期',
                'link': '/license/my',
                'count': 1,
                'time': license.end_time.isoformat()
            })

        return {
            'code': 200,
            'data': {
                'count': sum(item.get('count', 1) for item in items),
                'items': items
            }
        }, 200
