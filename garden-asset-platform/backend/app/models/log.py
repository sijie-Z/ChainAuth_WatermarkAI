"""
操作日志数据模型
"""
from datetime import datetime
from app.extensions import db


class OperationLog(db.Model):
    """操作日志表"""
    __tablename__ = 'operation_logs'

    id = db.Column(db.BigInteger, primary_key=True)

    # 操作用户
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    user_name = db.Column(db.String(50), nullable=True)
    user_role = db.Column(db.String(20), nullable=True)

    # 操作信息
    action = db.Column(db.String(50), nullable=False)  # login/logout/upload/download/embed/extract...
    module = db.Column(db.String(50), nullable=True)  # asset/license/blockchain/user...
    description = db.Column(db.Text, nullable=True)

    # 操作对象
    target_type = db.Column(db.String(50), nullable=True)  # asset/user/license...
    target_id = db.Column(db.String(36), nullable=True)

    # 请求信息
    ip_address = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(db.String(500), nullable=True)
    request_url = db.Column(db.String(500), nullable=True)
    request_method = db.Column(db.String(10), nullable=True)

    # 结果
    status = db.Column(db.String(20), default='success')  # success/failed
    error_message = db.Column(db.Text, nullable=True)

    # 额外数据
    extra_data = db.Column(db.JSON, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    user = db.relationship('User', backref='operation_logs')

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'user_name': self.user_name,
            'action': self.action,
            'module': self.module,
            'description': self.description,
            'target_type': self.target_type,
            'target_id': self.target_id,
            'ip_address': self.ip_address,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

    @classmethod
    def log(cls, user, action, module=None, description=None,
            target_type=None, target_id=None, request=None,
            status='success', error_message=None, extra_data=None):
        """记录操作日志"""
        log = cls(
            user_id=user.id if user else None,
            user_name=user.username if user else None,
            user_role=user.role if user else None,
            action=action,
            module=module,
            description=description,
            target_type=target_type,
            target_id=target_id,
            status=status,
            error_message=error_message,
            extra_data=extra_data
        )

        if request:
            log.ip_address = request.remote_addr
            log.user_agent = request.headers.get('User-Agent', '')[:500]
            log.request_url = request.url[:500]
            log.request_method = request.method

        db.session.add(log)
        try:
            db.session.commit()
        except:
            db.session.rollback()

        return log