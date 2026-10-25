"""
用户数据模型
"""
from datetime import datetime
from app.extensions import db
from werkzeug.security import generate_password_hash, check_password_hash


class User(db.Model):
    """用户表"""
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=True)
    phone = db.Column(db.String(20), unique=True, nullable=True)
    password_hash = db.Column(db.String(256), nullable=False)

    # 用户信息
    nickname = db.Column(db.String(50), nullable=True)
    avatar = db.Column(db.String(500), nullable=True)
    real_name = db.Column(db.String(50), nullable=True)
    id_number = db.Column(db.String(50), nullable=True)  # 身份证号(加密存储)

    # 用户角色
    role = db.Column(db.String(20), nullable=False, default='user')  # user/asset_admin/license_admin/adm1/adm2/admin
    user_number = db.Column(db.String(50), nullable=True)  # 工号/管理员编号

    # 状态
    status = db.Column(db.String(20), default='active')  # active/inactive/banned
    is_active = db.Column(db.Boolean, default=True)  # 是否激活
    is_verified = db.Column(db.Boolean, default=False)  # 是否已实名认证
    email_verified_at = db.Column(db.DateTime, nullable=True)  # 邮箱验证时间

    # 时间
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login_at = db.Column(db.DateTime, nullable=True)

    def set_password(self, password):
        """设置密码"""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """验证密码"""
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'phone': self.phone,
            'nickname': self.nickname,
            'avatar': self.avatar,
            'role': self.role,
            'status': self.status,
            'is_verified': self.is_verified,
            'email_verified': bool(self.email_verified_at),
            'email_verified_at': (
                self.email_verified_at.isoformat() if self.email_verified_at else None
            ),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login_at': self.last_login_at.isoformat() if self.last_login_at else None
        }

    def __repr__(self):
        return f'<User {self.username}>'


class UserToken(db.Model):
    """用户Token表(JWT刷新token黑名单管理)"""
    __tablename__ = 'user_tokens'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    token = db.Column(db.String(500), nullable=False)
    token_type = db.Column(db.String(20), nullable=False)  # access/refresh
    is_revoked = db.Column(db.Boolean, default=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref=db.backref('tokens', lazy='dynamic'))

    def __repr__(self):
        return f'<UserToken user_id={self.user_id} type={self.token_type}>'