"""
用户收藏、下载记录、分享链接与通知已读模型
"""
import json
from datetime import datetime
from app.extensions import db


class Favorite(db.Model):
    """用户收藏表"""
    __tablename__ = 'favorites'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    asset_id = db.Column(db.String(36), db.ForeignKey('assets.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('user_id', 'asset_id', name='uk_user_asset'),
    )

    user = db.relationship('User', backref=db.backref('favorites', lazy='dynamic'))
    asset = db.relationship('Asset', backref=db.backref('favorited_by', lazy='dynamic'))

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'asset_id': self.asset_id,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class DownloadRecord(db.Model):
    """下载记录表"""
    __tablename__ = 'download_records'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    asset_id = db.Column(db.String(36), db.ForeignKey('assets.id'), nullable=False)
    license_id = db.Column(db.Integer, db.ForeignKey('licenses.id'), nullable=True)
    fingerprint_id = db.Column(
        db.Integer, db.ForeignKey('download_fingerprints.id'), nullable=True
    )
    ip_address = db.Column(db.String(50), nullable=True)
    user_agent = db.Column(db.String(500), nullable=True)

    # 授权范围执行：成功下载与超范围拒绝都进入台账
    status = db.Column(db.String(20), default='success')  # success/denied
    denial_reason = db.Column(db.String(300), nullable=True)
    usage_purpose = db.Column(db.String(40), nullable=True)
    territory = db.Column(db.String(100), nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref=db.backref('downloads', lazy='dynamic'))
    asset = db.relationship('Asset', backref=db.backref('downloads', lazy='dynamic'))
    license = db.relationship(
        'License', backref=db.backref('download_records', lazy='dynamic')
    )
    fingerprint = db.relationship(
        'DownloadFingerprint', backref=db.backref('download_records', lazy='dynamic')
    )

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'asset_id': self.asset_id,
            'license_id': self.license_id,
            'fingerprint_id': self.fingerprint_id,
            'fingerprint_code': (
                self.fingerprint.fingerprint_code if self.fingerprint else None
            ),
            'status': self.status or 'success',
            'denial_reason': self.denial_reason,
            'usage_purpose': self.usage_purpose,
            'territory': self.territory,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class AssetShare(db.Model):
    """资产公开分享链接

    令牌不可枚举；可选访问码、有效期、下载权限与下载次数上限。
    访问码只保存哈希，接口仅返回 has_access_code。
    """
    __tablename__ = 'asset_shares'

    id = db.Column(db.Integer, primary_key=True)
    token = db.Column(db.String(64), unique=True, nullable=False, index=True)
    asset_id = db.Column(db.String(36), db.ForeignKey('assets.id'), nullable=False, index=True)
    creator_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    access_code_hash = db.Column(db.String(256), nullable=True)
    expires_at = db.Column(db.DateTime, nullable=True)
    allow_download = db.Column(db.Boolean, default=False)
    max_downloads = db.Column(db.Integer, nullable=True)
    download_count = db.Column(db.Integer, default=0)
    view_count = db.Column(db.Integer, default=0)
    last_viewed_at = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String(20), default='active')  # active/revoked
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    asset = db.relationship('Asset', backref=db.backref('shares', lazy='dynamic'))
    creator = db.relationship('User', backref=db.backref('asset_shares', lazy='dynamic'))

    @property
    def is_expired(self):
        return bool(self.expires_at and self.expires_at <= datetime.utcnow())

    @property
    def is_download_limited(self):
        return bool(self.max_downloads is not None and self.download_count >= self.max_downloads)

    def is_available(self):
        return self.status == 'active' and not self.is_expired

    def check_access_code(self, code):
        if not self.access_code_hash:
            return True
        if not code:
            return False
        from werkzeug.security import check_password_hash
        return check_password_hash(self.access_code_hash, str(code))

    def to_dict(self, include_asset=False):
        data = {
            'id': self.id,
            'token': self.token,
            'asset_id': self.asset_id,
            'creator_id': self.creator_id,
            'has_access_code': bool(self.access_code_hash),
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'allow_download': bool(self.allow_download),
            'max_downloads': self.max_downloads,
            'download_count': self.download_count or 0,
            'view_count': self.view_count or 0,
            'last_viewed_at': self.last_viewed_at.isoformat() if self.last_viewed_at else None,
            'status': 'expired' if self.is_expired and self.status == 'active' else self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'url': f'/share/{self.token}'
        }
        if include_asset and self.asset:
            data['asset'] = {
                'id': self.asset.id,
                'asset_code': self.asset.asset_code,
                'title': self.asset.title,
                'status': self.asset.status
            }
        return data


class ShareDownload(db.Model):
    """匿名分享下载记录

    公开分享下载没有登录用户，单独建表记录，便于与授权下载台账合并审计。
    """
    __tablename__ = 'share_downloads'

    id = db.Column(db.Integer, primary_key=True)
    share_id = db.Column(
        db.Integer, db.ForeignKey('asset_shares.id'), nullable=False, index=True
    )
    asset_id = db.Column(
        db.String(36), db.ForeignKey('assets.id'), nullable=False, index=True
    )
    ip_address = db.Column(db.String(50), nullable=True)
    user_agent = db.Column(db.String(500), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    share = db.relationship(
        'AssetShare', backref=db.backref('downloads', lazy='dynamic')
    )
    asset = db.relationship(
        'Asset', backref=db.backref('share_downloads', lazy='dynamic')
    )


class NotificationEvent(db.Model):
    """事件型通知

    审核结果、授权撤销/续期等需要留下正文的事件写在这里；
    纯状态待办仍由 NotificationsResource 实时计算。
    """
    __tablename__ = 'notification_events'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    event_type = db.Column(db.String(40), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.String(500), nullable=True)
    link = db.Column(db.String(300), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    user = db.relationship(
        'User', backref=db.backref('notification_events', lazy='dynamic')
    )

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'event_type': self.event_type,
            'title': self.title,
            'description': self.description,
            'link': self.link,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class NotificationPreference(db.Model):
    """用户通知偏好

    站内 SSE 默认开启；邮件为显式开关，按事件分组过滤。
    邮箱使用用户资料中的 email，不在偏好表重复存储。
    """
    __tablename__ = 'notification_preferences'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey('users.id'), nullable=False, unique=True, index=True
    )
    email_enabled = db.Column(db.Boolean, default=False, nullable=False)
    # 可选值：asset/license/task/infringement
    email_groups = db.Column(
        db.JSON,
        default=lambda: ['asset', 'license', 'task', 'infringement'],
        nullable=True
    )
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    user = db.relationship(
        'User', backref=db.backref('notification_preference', uselist=False)
    )

    def to_dict(self):
        return {
            'email_enabled': bool(self.email_enabled),
            'email_groups': self.email_groups or [],
            'email': self.user.email if self.user else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class NotificationDelivery(db.Model):
    """通知投递记录（当前支持邮件渠道）

    事件写入时同步创建 pending 投递行（同一事务）；后台 worker 领取后
    根据用户偏好与 SMTP 配置发送，失败按次数退避重试。
    """
    __tablename__ = 'notification_deliveries'
    __table_args__ = (
        db.UniqueConstraint('event_id', 'channel', name='uk_notification_delivery'),
    )

    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(
        db.Integer, db.ForeignKey('notification_events.id'), nullable=False, index=True
    )
    channel = db.Column(db.String(20), default='email', nullable=False)
    status = db.Column(db.String(20), default='pending', nullable=False, index=True)
    attempts = db.Column(db.Integer, default=0, nullable=False)
    error_message = db.Column(db.String(500), nullable=True)
    next_attempt_at = db.Column(db.DateTime, nullable=True)
    sent_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    event = db.relationship(
        'NotificationEvent', backref=db.backref('deliveries', lazy='dynamic')
    )

    def to_dict(self):
        return {
            'id': self.id,
            'event_id': self.event_id,
            'channel': self.channel,
            'status': self.status,
            'attempts': self.attempts,
            'error_message': self.error_message,
            'sent_at': self.sent_at.isoformat() if self.sent_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class NotificationRead(db.Model):
    """通知已读状态

    待办提醒是按业务状态实时计算的，不单独存通知正文；
    这里只记录“某个用户读过哪个 key”，用于区分未读。
    """
    __tablename__ = 'notification_reads'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    notification_key = db.Column(db.String(120), nullable=False)
    read_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('user_id', 'notification_key', name='uk_user_notification'),
    )


class Collection(db.Model):
    """用户自建的资产合集（如“宋代园林”“斗拱细节”）。"""
    __tablename__ = 'collections'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(500), nullable=True)
    owner_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    is_public = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    owner = db.relationship('User', backref=db.backref('collections', lazy='dynamic'))
    items = db.relationship(
        'CollectionAsset', backref='collection',
        cascade='all, delete-orphan', lazy='dynamic'
    )

    def to_dict(self, include_assets=False, viewer_id=None):
        first_item = self.items.order_by(CollectionAsset.id).first()
        cover_asset = first_item.asset if first_item else None
        data = {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'owner_id': self.owner_id,
            'owner_name': (
                (self.owner.nickname or self.owner.username) if self.owner else None
            ),
            'is_public': bool(self.is_public),
            'is_owner': viewer_id is not None and self.owner_id == viewer_id,
            'asset_count': self.items.count(),
            'cover_url': (
                f'/api/assets/{cover_asset.id}/thumbnail?size=card'
                if cover_asset else None
            ),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
        if include_assets:
            data['assets'] = [
                item.asset.to_dict()
                for item in self.items.order_by(CollectionAsset.id).all()
                if item.asset and item.asset.status != 'deleted'
            ]
        return data


class CollectionAsset(db.Model):
    """合集中的资产条目"""
    __tablename__ = 'collection_assets'

    id = db.Column(db.Integer, primary_key=True)
    collection_id = db.Column(
        db.Integer, db.ForeignKey('collections.id'), nullable=False, index=True
    )
    asset_id = db.Column(
        db.String(36), db.ForeignKey('assets.id'), nullable=False, index=True
    )
    added_at = db.Column(db.DateTime, default=datetime.utcnow)

    asset = db.relationship('Asset', backref=db.backref('collection_items', lazy='dynamic'))

    __table_args__ = (
        db.UniqueConstraint('collection_id', 'asset_id', name='uk_collection_asset'),
    )


class SystemConfig(db.Model):
    """系统配置表"""
    __tablename__ = 'system_configs'

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False)
    value = db.Column(db.Text, nullable=True)
    description = db.Column(db.String(500), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'key': self.key,
            'value': self.value,
            'description': self.description
        }

class UploadSession(db.Model):
    """分块上传会话（断点续传）"""
    __tablename__ = 'upload_sessions'

    id = db.Column(db.String(36), primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey('users.id'), nullable=False, index=True
    )
    filename = db.Column(db.String(255), nullable=False)
    asset_type = db.Column(db.String(20), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    garden_id = db.Column(db.Integer, nullable=True)
    tags_json = db.Column(db.Text, nullable=True)
    expected_size = db.Column(db.BigInteger, nullable=False)
    received_size = db.Column(db.BigInteger, default=0, nullable=False)
    chunk_size = db.Column(db.Integer, nullable=False)
    temp_path = db.Column(db.String(500), nullable=False)
    file_fingerprint = db.Column(db.String(64), nullable=True)
    lease_token = db.Column(db.String(64), nullable=True)
    lease_expires_at = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String(20), default='uploading', nullable=False)
    asset_id = db.Column(db.String(36), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    user = db.relationship('User', backref=db.backref('upload_sessions', lazy='dynamic'))

    def to_dict(self):
        try:
            tags = json.loads(self.tags_json or '[]')
        except (TypeError, ValueError):
            tags = []
        return {
            'upload_id': self.id,
            'filename': self.filename,
            'asset_type': self.asset_type,
            'title': self.title,
            'description': self.description or '',
            'garden_id': self.garden_id,
            'tags': tags if isinstance(tags, list) else [],
            'expected_size': self.expected_size,
            'received_size': self.received_size,
            'chunk_size': self.chunk_size,
            'fingerprint': self.file_fingerprint,
            'lease_active': bool(
                self.lease_token
                and self.lease_expires_at
                and self.lease_expires_at > datetime.utcnow()
            ),
            'lease_expires_at': (
                self.lease_expires_at.isoformat()
                if self.lease_expires_at else None
            ),
            'status': self.status,
            'asset_id': self.asset_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
