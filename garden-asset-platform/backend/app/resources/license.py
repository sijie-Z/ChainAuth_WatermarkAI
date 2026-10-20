"""
授权管理API资源
"""
import uuid
from datetime import datetime, timedelta, timezone
from flask import request
from flask_restful import Resource
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import or_
from app.extensions import db
from app.models.license import License, LicenseApplication, LicenseContract
from app.models.asset import Asset
from app.models.user import User
from app.models.log import OperationLog


class LicenseApplyResource(Resource):
    """申请授权"""

    @jwt_required()
    def post(self):
        """提交授权申请"""
        data = request.get_json()
        current_user_id = get_jwt_identity()

        asset_id = data.get('asset_id')
        if not asset_id:
            return {'code': 400, 'message': '缺少资产ID'}, 400

        asset = Asset.query.get(asset_id)
        if not asset:
            return {'code': 404, 'message': '资产不存在'}, 404

        if asset.status != 'published':
            return {'code': 400, 'message': '只能申请已发布资产的授权'}, 400

        existing = LicenseApplication.query.filter(
            LicenseApplication.asset_id == asset_id,
            LicenseApplication.applicant_id == current_user_id,
            LicenseApplication.status.in_(['pending', 'adm1_approved']),
        ).first()
        if existing:
            return {'code': 400, 'message': '该资产已有待审批的申请'}, 400

        application = LicenseApplication(
            application_code=f"APP-{datetime.now().strftime('%Y%m%d%H%M%S%f')}-{uuid.uuid4().hex[:4].upper()}",
            asset_id=asset_id,
            applicant_id=current_user_id,
            license_type=data.get('license_type', 'personal'),
            usage_scope=data.get('purpose', ''),
            usage_purpose=data.get('purpose', ''),
            territory=data.get('territory', '中国大陆'),
            duration_months=self._parse_duration(data.get('valid_period')),
            is_exclusive=data.get('is_exclusive', False),
            contact_person=data.get('contact', '')
        )

        db.session.add(application)
        db.session.commit()

        # 记录操作日志
        log = OperationLog(
            user_id=current_user_id,
            action='license_apply',
            module='license',
            target_type='license_application',
            target_id=str(application.id),
            description=f'提交资产 {asset.title} 的授权申请'
        )
        db.session.add(log)
        db.session.commit()

        return {
            'code': 200,
            'message': '申请提交成功',
            'data': application.to_dict()
        }

    def _parse_duration(self, period):
        if not period:
            return None
        mapping = {'1m': 1, '3m': 3, '6m': 6, '1y': 12, 'permanent': None}
        return mapping.get(period)


class LicensePendingResource(Resource):
    """待审批申请列表"""

    @jwt_required()
    def get(self):
        """获取待审批列表"""
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)

        if user.role not in ['admin', 'asset_admin', 'license_admin', 'adm1', 'adm2']:
            return {'code': 403, 'message': '无权限'}, 403

        # adm1 看尚未分配或分配给自己的一级审批；
        # adm2 看一级已通过、尚未分配或分配给自己的二级审批。
        query = LicenseApplication.query

        if user.role == 'adm1':
            query = query.filter(
                LicenseApplication.status == 'pending',
                or_(
                    LicenseApplication.adm1_reviewer_id == current_user_id,
                    LicenseApplication.adm1_reviewer_id.is_(None),
                ),
            )
        elif user.role == 'adm2':
            query = query.filter(
                LicenseApplication.status == 'adm1_approved',
                or_(
                    LicenseApplication.adm2_reviewer_id == current_user_id,
                    LicenseApplication.adm2_reviewer_id.is_(None),
                ),
            )
        else:
            query = query.filter(
                LicenseApplication.status.in_(['pending', 'adm1_approved'])
            )

        applications = query.order_by(LicenseApplication.created_at.desc()).all()

        result = []
        for app in applications:
            app_dict = app.to_dict()
            app_dict['asset_title'] = app.asset.title if app.asset else ''
            app_dict['applicant_name'] = app.applicant.username if app.applicant else ''
            result.append(app_dict)

        return {'code': 200, 'data': result}


class LicenseApproveResource(Resource):
    """审批授权申请"""

    @jwt_required()
    def post(self, application_id):
        """审批操作"""
        data = request.get_json() or {}
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)

        if not user or user.role not in ['admin', 'asset_admin', 'license_admin', 'adm1', 'adm2']:
            return {'code': 403, 'message': '无审批权限'}, 403

        application = LicenseApplication.query.get(application_id)
        if not application:
            return {'code': 404, 'message': '申请不存在'}, 404

        action = data.get('action')
        if action not in ('approve', 'reject'):
            return {'code': 400, 'message': 'action 必须是 approve 或 reject'}, 400
        comment = data.get('comment', '')

        # 审批人可在弹窗中指定到期日；未指定时按申请时长计算
        end_time = None
        valid_until = data.get('valid_until')
        if valid_until:
            try:
                end_time = datetime.fromisoformat(str(valid_until).replace('Z', '+00:00'))
            except ValueError:
                return {'code': 400, 'message': '有效期格式无效'}, 400
            if end_time.tzinfo is not None:
                end_time = end_time.astimezone(timezone.utc).replace(tzinfo=None)
            if end_time <= datetime.utcnow():
                return {'code': 400, 'message': '有效期必须晚于当前时间'}, 400

        acted = False

        # 一级审批：adm1 / asset_admin / admin
        if user.role in ['admin', 'asset_admin', 'adm1'] and application.adm1_status == 'pending':
            if application.adm1_reviewer_id not in (None, current_user_id):
                return {'code': 403, 'message': '该申请已分配给其他审批人'}, 403
            application.adm1_reviewer_id = current_user_id
            application.adm1_review_time = datetime.utcnow()
            application.adm1_review_comment = comment
            application.adm1_status = 'approved' if action == 'approve' else 'rejected'
            application.status = 'adm1_approved' if action == 'approve' else 'rejected'
            acted = True

        # 二级审批：adm2 / license_admin / admin
        elif (
            user.role in ['admin', 'license_admin', 'adm2']
            and application.adm1_status == 'approved'
            and application.adm2_status == 'pending'
        ):
            if application.adm2_reviewer_id not in (None, current_user_id):
                return {'code': 403, 'message': '该申请已分配给其他审批人'}, 403
            application.adm2_reviewer_id = current_user_id
            application.adm2_review_time = datetime.utcnow()
            application.adm2_review_comment = comment
            application.adm2_status = 'approved' if action == 'approve' else 'rejected'

            if action == 'approve':
                application.status = 'approved'
                # 创建授权记录
                self._create_license(application, end_time=end_time)
            else:
                application.status = 'rejected'
            acted = True

        if not acted:
            return {'code': 400, 'message': '当前状态不可审批，或不属于你的审批阶段'}, 400

        db.session.commit()

        return {'code': 200, 'message': '审批成功'}

    def _create_license(self, application, end_time=None):
        """创建授权记录"""
        asset = application.asset
        if end_time is None and application.duration_months:
            end_time = datetime.utcnow() + timedelta(days=application.duration_months * 30)

        license = License(
            license_code=f"LIC-{datetime.now().strftime('%Y%m%d%H%M%S%f')}-{uuid.uuid4().hex[:4].upper()}",
            asset_id=asset.id,
            # 兼容历史数据：旧资产的 uploader_id 可能为空
            licensor_id=asset.owner_id or asset.creator_id or asset.uploader_id,
            licensee_id=application.applicant_id,
            license_type=application.license_type,
            usage_scope=application.usage_scope,
            territory=application.territory,
            start_time=datetime.utcnow(),
            end_time=end_time,
            is_exclusive=application.is_exclusive,
            status='active'
        )
        db.session.add(license)


class LicenseApprovedResource(Resource):
    """已审批列表"""

    @jwt_required()
    def get(self):
        """获取已审批列表（仅审批/管理员角色）"""
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        if not user or user.role not in ['admin', 'asset_admin', 'license_admin', 'adm1', 'adm2']:
            return {'code': 403, 'message': '无权限'}, 403

        data = request.args
        page = max(data.get('page', 1, type=int), 1)
        per_page = min(max(data.get('per_page', 20, type=int), 1), 100)
        status = (data.get('status') or '').strip()

        query = License.query
        if status:
            if status not in ('pending', 'active', 'expired', 'revoked'):
                return {'code': 400, 'message': '无效的状态筛选'}, 400
            query = query.filter_by(status=status)

        pagination = query.order_by(License.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )

        result = []
        for lic in pagination.items:
            lic_dict = lic.to_dict()
            lic_dict['asset_title'] = lic.asset.title if lic.asset else ''
            lic_dict['licensee_name'] = lic.licensee.username if lic.licensee else ''
            lic_dict['licensor_name'] = lic.licensor.username if lic.licensor else ''
            result.append(lic_dict)

        return {
            'code': 200,
            'data': {
                'items': result,
                'total': pagination.total
            }
        }


class MyLicenseResource(Resource):
    """我的授权"""

    @jwt_required()
    def get(self):
        """获取当前用户的授权列表"""
        current_user_id = get_jwt_identity()
        data = request.args
        page = max(data.get('page', 1, type=int), 1)
        per_page = min(max(data.get('per_page', 20, type=int), 1), 100)
        status = (data.get('status') or '').strip()

        query = License.query.filter_by(licensee_id=current_user_id)
        if status:
            if status not in ('pending', 'active', 'expired', 'revoked'):
                return {'code': 400, 'message': '无效的状态筛选'}, 400
            query = query.filter_by(status=status)

        pagination = query.order_by(License.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )

        result = []
        for lic in pagination.items:
            lic_dict = lic.to_dict()
            lic_dict['asset_title'] = lic.asset.title if lic.asset else ''
            result.append(lic_dict)

        return {
            'code': 200,
            'data': {
                'items': result,
                'total': pagination.total
            }
        }


class MyApplicationsResource(Resource):
    """我的授权申请（含审批中与已拒绝）"""

    @jwt_required()
    def get(self):
        current_user_id = get_jwt_identity()
        data = request.args
        page = max(data.get('page', 1, type=int), 1)
        per_page = min(max(data.get('per_page', 20, type=int), 1), 100)
        status = (data.get('status') or '').strip()

        query = LicenseApplication.query.filter_by(applicant_id=current_user_id)
        if status:
            if status not in ('pending', 'adm1_approved', 'approved', 'rejected', 'cancelled', 'in_progress'):
                return {'code': 400, 'message': '无效的状态筛选'}, 400
            if status == 'in_progress':
                query = query.filter(
                    LicenseApplication.status.in_(['pending', 'adm1_approved'])
                )
            else:
                query = query.filter_by(status=status)

        pagination = query.order_by(LicenseApplication.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )

        return {
            'code': 200,
            'data': {
                'items': [application.to_dict() for application in pagination.items],
                'total': pagination.total
            }
        }
