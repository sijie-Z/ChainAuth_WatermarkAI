"""
授权管理API资源
"""
from datetime import datetime, timedelta
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

        application = LicenseApplication(
            application_code=f"APP-{datetime.now().strftime('%Y%m%d%H%M%S')}-{asset_id[:4].upper()}",
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
        data = request.get_json()
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)

        application = LicenseApplication.query.get(application_id)
        if not application:
            return {'code': 404, 'message': '申请不存在'}, 404

        action = data.get('action')  # approve or reject
        comment = data.get('comment', '')

        # 双重审批流程
        if user.role in ['admin', 'asset_admin', 'adm1']:
            if application.adm1_status == 'pending':
                application.adm1_reviewer_id = current_user_id
                application.adm1_review_time = datetime.utcnow()
                application.adm1_review_comment = comment
                application.adm1_status = 'approved' if action == 'approve' else 'rejected'
                application.status = 'adm1_approved' if action == 'approve' else 'rejected'

        if user.role in ['admin', 'license_admin', 'adm2']:
            if application.adm1_status == 'approved' and application.adm2_status == 'pending':
                application.adm2_reviewer_id = current_user_id
                application.adm2_review_time = datetime.utcnow()
                application.adm2_review_comment = comment
                application.adm2_status = 'approved' if action == 'approve' else 'rejected'

                if action == 'approve':
                    application.status = 'approved'
                    # 创建授权记录
                    self._create_license(application)
                else:
                    application.status = 'rejected'

        db.session.commit()

        return {'code': 200, 'message': '审批成功'}

    def _create_license(self, application):
        """创建授权记录"""
        asset = application.asset
        end_time = None
        if application.duration_months:
            end_time = datetime.utcnow() + timedelta(days=application.duration_months * 30)

        license = License(
            license_code=f"LIC-{datetime.now().strftime('%Y%m%d%H%M%S')}-{asset.asset_code[:4]}",
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
        """获取已审批列表"""
        data = request.args
        page = int(data.get('page', 1))
        per_page = int(data.get('per_page', 20))
        status = data.get('status', '')

        query = License.query
        if status:
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
        page = int(data.get('page', 1))
        per_page = int(data.get('per_page', 20))
        status = data.get('status', '')

        query = License.query.filter_by(licensee_id=current_user_id)
        if status:
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
