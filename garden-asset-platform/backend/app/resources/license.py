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


def build_contract_content(license, asset, application=None):
    """生成可读的授权合同正文，供合同接口与前端展示。"""
    def fmt(value):
        return value.strftime('%Y-%m-%d') if value else '未约定期限'

    usage = license.usage_scope or (application.usage_scope if application else '') or '按双方约定'
    type_names = {
        'personal': '个人使用',
        'non_commercial': '非商业使用',
        'academic': '学术研究',
        'commercial': '商业使用',
        'commercial_ad': '商业-广告',
        'commercial_product': '商业-产品',
        'commercial_publish': '商业-出版',
        'display': '展览展示',
        'derivative': '衍生创作',
        'exclusive': '独家授权',
    }
    return (
        f"数字资产使用授权合同\n\n"
        f"合同编号：{license.license_code}\n"
        f"授权方：{license.licensor.username if license.licensor else '平台资产权利人'}\n"
        f"被授权方：{license.licensee.username if license.licensee else '申请人'}\n"
        f"授权资产：{asset.title}（{asset.asset_code}）\n"
        f"授权类型：{type_names.get(license.license_type, license.license_type)}\n"
        f"使用范围：{usage}\n"
        f"授权地域：{license.territory or '中国大陆'}\n"
        f"授权期限：{fmt(license.start_time)} 至 {fmt(license.end_time)}\n"
        f"是否独家：{'是' if license.is_exclusive else '否'}\n\n"
        f"1. 被授权方仅可在上述范围内使用授权资产，不得转授权或超范围使用。\n"
        f"2. 被授权方应保留资产中的水印标识，不得去除、篡改或规避溯源。\n"
        f"3. 授权方保证其对授权资产拥有合法权利，并有权作出本授权。\n"
        f"4. 本合同的成立、生效与解释适用中华人民共和国法律。\n"
    )


class LicenseCancelResource(Resource):
    """申请人撤回授权申请"""

    @jwt_required()
    def post(self, application_id):
        current_user_id = get_jwt_identity()
        application = LicenseApplication.query.get(application_id)
        if not application:
            return {'code': 404, 'message': '申请不存在'}, 404
        if application.applicant_id != current_user_id:
            return {'code': 403, 'message': '只能撤回自己的申请'}, 403
        if application.status not in ('pending', 'adm1_approved'):
            return {'code': 400, 'message': '当前状态不可撤回'}, 400

        application.status = 'cancelled'
        db.session.commit()

        OperationLog.log(
            user=User.query.get(current_user_id),
            action='license_cancel',
            module='license',
            description=f'撤回授权申请: {application.application_code}',
            target_type='license_application',
            target_id=str(application.id)
        )
        db.session.commit()
        return {'code': 200, 'message': '申请已撤回'}, 200


class LicenseContractResource(Resource):
    """授权合同详情（不存在时按授权记录生成标准合同）"""

    @jwt_required()
    def get(self, license_id):
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        license = License.query.get(license_id)
        if not license:
            return {'code': 404, 'message': '授权记录不存在'}, 404

        admin_roles = ('admin', 'asset_admin', 'license_admin', 'adm1', 'adm2')
        if current_user_id not in (license.licensee_id, license.licensor_id) and user.role not in admin_roles:
            return {'code': 403, 'message': '无权查看该合同'}, 403

        asset = license.asset
        application = LicenseApplication.query.filter_by(
            asset_id=license.asset_id,
            applicant_id=license.licensee_id
        ).order_by(LicenseApplication.created_at.desc()).first()

        contract = LicenseContract.query.filter_by(license_id=license.id).first()
        if not contract:
            contract = LicenseContract(
                contract_code=f"CON-{datetime.now().strftime('%Y%m%d%H%M%S%f')}-{uuid.uuid4().hex[:4].upper()}",
                application_id=application.id if application else None,
                license_id=license.id,
                contract_content=build_contract_content(license, asset, application),
                fee_amount=application.expected_fee if application else None,
                effective_time=license.start_time,
                expiry_time=license.end_time,
                status='effective'
            )
            db.session.add(contract)
            db.session.commit()

        data = contract.to_dict()
        data['contract_content'] = contract.contract_content
        data['license_code'] = license.license_code
        data['license_type'] = license.license_type
        data['usage_scope'] = license.usage_scope
        data['territory'] = license.territory
        data['licensee_name'] = license.licensee.username if license.licensee else None
        data['licensor_name'] = license.licensor.username if license.licensor else None
        data['asset_title'] = asset.title if asset else None
        data['asset_code'] = asset.asset_code if asset else None
        return {'code': 200, 'data': data}, 200


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

        OperationLog.log(
            user=user,
            action='approve' if action == 'approve' else 'reject',
            module='license',
            description=f"{'通过' if action == 'approve' else '拒绝'}授权申请: {application.application_code}",
            target_type='license_application',
            target_id=str(application.id)
        )

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
        db.session.flush()
        db.session.add(LicenseContract(
            contract_code=f"CON-{datetime.now().strftime('%Y%m%d%H%M%S%f')}-{uuid.uuid4().hex[:4].upper()}",
            application_id=application.id,
            license_id=license.id,
            contract_content=build_contract_content(license, asset, application),
            special_terms='',
            fee_amount=application.expected_fee,
            effective_time=license.start_time,
            expiry_time=end_time,
            status='effective'
        ))


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

            application = LicenseApplication.query.filter_by(
                asset_id=lic.asset_id,
                applicant_id=lic.licensee_id
            ).order_by(LicenseApplication.created_at.desc()).first()
            lic_dict['approver_name'] = (
                application.adm2_reviewer.username
                if application and application.adm2_reviewer else None
            )
            lic_dict['approved_at'] = (
                application.adm2_review_time.isoformat()
                if application and application.adm2_review_time else None
            )
            contract = LicenseContract.query.filter_by(license_id=lic.id).first()
            lic_dict['contract_code'] = contract.contract_code if contract else None
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
        asset_id = (data.get('asset_id') or '').strip()

        query = License.query.filter_by(licensee_id=current_user_id)
        if asset_id:
            query = query.filter_by(asset_id=asset_id)
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
        asset_id = (data.get('asset_id') or '').strip()

        query = LicenseApplication.query.filter_by(applicant_id=current_user_id)
        if asset_id:
            query = query.filter_by(asset_id=asset_id)
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
