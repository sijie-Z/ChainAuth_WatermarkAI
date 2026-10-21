"""
授权数据模型
"""
from datetime import datetime
import uuid
from app.extensions import db


def generate_license_code():
    return f"LIC-{datetime.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:4].upper()}"


class License(db.Model):
    """授权记录表"""
    __tablename__ = 'licenses'

    id = db.Column(db.Integer, primary_key=True)
    license_code = db.Column(db.String(32), unique=True, default=generate_license_code)

    # 关联信息
    asset_id = db.Column(db.String(36), db.ForeignKey('assets.id'), nullable=False)
    licensor_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)  # 授权方
    licensee_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)  # 被授权方

    # 授权类型
    license_type = db.Column(db.String(50), nullable=False)
    # non_commercial: 非商业使用
    # commercial_ad: 商业-广告宣传
    # commercial_product: 商业-产品
    # commercial_publish: 商业-出版
    # derivative: 衍生创作
    # exclusive: 独家授权

    usage_scope = db.Column(db.Text, nullable=True)  # 使用范围描述
    territory = db.Column(db.String(100), default='中国大陆')  # 授权地域

    # 有效期
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=True)

    # 是否独家
    is_exclusive = db.Column(db.Boolean, default=False)

    # 授权费用
    fee_amount = db.Column(db.Numeric(12, 2), nullable=True)
    payment_status = db.Column(db.String(20), default='pending')  # pending/paid/refunded

    # 区块链记录
    tx_hash = db.Column(db.String(66), nullable=True)

    # 状态
    status = db.Column(db.String(20), default='pending')  # pending/active/expired/revoked

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系
    licensor = db.relationship('User', foreign_keys=[licensor_id])
    licensee = db.relationship('User', foreign_keys=[licensee_id])
    contracts = db.relationship('LicenseContract', backref='license', lazy='dynamic')

    def to_dict(self):
        return {
            'id': self.id,
            'license_code': self.license_code,
            'asset_id': self.asset_id,
            'license_type': self.license_type,
            'usage_scope': self.usage_scope,
            'territory': self.territory,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'is_exclusive': self.is_exclusive,
            'status': self.status,
            'tx_hash': self.tx_hash,
            'asset_code': self.asset.asset_code if self.asset else None,
            'asset_title': self.asset.title if self.asset else None,
            'file_format': self.asset.file_format if self.asset else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class LicenseApplication(db.Model):
    """授权申请表"""
    __tablename__ = 'license_applications'

    id = db.Column(db.Integer, primary_key=True)
    application_code = db.Column(db.String(32), unique=True, nullable=False)

    asset_id = db.Column(db.String(36), db.ForeignKey('assets.id'), nullable=False)
    applicant_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    # 申请内容
    license_type = db.Column(db.String(50), nullable=False)
    usage_scope = db.Column(db.Text, nullable=False)
    usage_purpose = db.Column(db.Text, nullable=True)
    territory = db.Column(db.String(100), default='中国大陆')
    duration_months = db.Column(db.Integer, nullable=True)
    is_exclusive = db.Column(db.Boolean, default=False)
    expected_fee = db.Column(db.Numeric(12, 2), nullable=True)

    # 申请材料
    company_name = db.Column(db.String(200), nullable=True)
    company_license = db.Column(db.String(100), nullable=True)
    contact_person = db.Column(db.String(50), nullable=True)
    contact_phone = db.Column(db.String(20), nullable=True)
    attachment_paths = db.Column(db.Text, nullable=True)  # JSON格式存储附件路径列表

    # 审批流程
    status = db.Column(db.String(20), default='pending')
    # pending/adm1_approved/adm2_approved/approved/rejected/cancelled

    adm1_reviewer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    adm1_review_time = db.Column(db.DateTime, nullable=True)
    adm1_review_comment = db.Column(db.Text, nullable=True)
    adm1_status = db.Column(db.String(20), default='pending')  # pending/approved/rejected

    adm2_reviewer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    adm2_review_time = db.Column(db.DateTime, nullable=True)
    adm2_review_comment = db.Column(db.Text, nullable=True)
    adm2_status = db.Column(db.String(20), default='pending')

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系
    asset = db.relationship('Asset', backref='license_applications')
    applicant = db.relationship('User', foreign_keys=[applicant_id])
    adm1_reviewer = db.relationship('User', foreign_keys=[adm1_reviewer_id])
    adm2_reviewer = db.relationship('User', foreign_keys=[adm2_reviewer_id])

    def to_dict(self):
        return {
            'id': self.id,
            'application_code': self.application_code,
            'asset_id': self.asset_id,
            'asset_code': self.asset.asset_code if self.asset else None,
            'asset_title': self.asset.title if self.asset else None,
            'applicant_name': self.applicant.username if self.applicant else None,
            'license_type': self.license_type,
            'usage_scope': self.usage_scope,
            'usage_purpose': self.usage_purpose,
            'purpose': self.usage_purpose or self.usage_scope,
            'duration_months': self.duration_months,
            'status': self.status,
            'adm1_status': self.adm1_status,
            'adm2_status': self.adm2_status,
            'adm1_review_comment': self.adm1_review_comment,
            'adm2_review_comment': self.adm2_review_comment,
            'adm1_review_time': self.adm1_review_time.isoformat() if self.adm1_review_time else None,
            'adm2_review_time': self.adm2_review_time.isoformat() if self.adm2_review_time else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class LicenseContract(db.Model):
    """授权合同表"""
    __tablename__ = 'license_contracts'

    id = db.Column(db.Integer, primary_key=True)
    contract_code = db.Column(db.String(32), unique=True, nullable=False)

    application_id = db.Column(db.Integer, db.ForeignKey('license_applications.id'))
    license_id = db.Column(db.Integer, db.ForeignKey('licenses.id'))

    # 合同内容
    contract_content = db.Column(db.Text, nullable=True)
    special_terms = db.Column(db.Text, nullable=True)
    fee_amount = db.Column(db.Numeric(12, 2), nullable=True)
    payment_method = db.Column(db.String(50), nullable=True)

    # 签署信息
    licensor_signature = db.Column(db.String(500), nullable=True)
    licensee_signature = db.Column(db.String(500), nullable=True)
    sign_time = db.Column(db.DateTime, nullable=True)

    # 生效信息
    effective_time = db.Column(db.DateTime, nullable=True)
    expiry_time = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String(20), default='draft')  # draft/signed/effective/expired/terminated

    contract_file = db.Column(db.String(500), nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'contract_code': self.contract_code,
            'status': self.status,
            'effective_time': self.effective_time.isoformat() if self.effective_time else None,
            'expiry_time': self.expiry_time.isoformat() if self.expiry_time else None
        }