"""
用户收藏、下载记录、分享链接与通知已读模型
"""
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
    ip_address = db.Column(db.String(50), nullable=True)
    user_agent = db.Column(db.String(500), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref=db.backref('downloads', lazy='dynamic'))
    asset = db.relationship('Asset', backref=db.backref('downloads', lazy='dynamic'))
    license = db.relationship(
        'License', backref=db.backref('download_records', lazy='dynamic')
    )

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'asset_id': self.asset_id,
            'license_id': self.license_id,
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