"""
资产数据模型
"""
from datetime import datetime
import json
import uuid
from app.extensions import db


def generate_uuid():
    return str(uuid.uuid4())


class Asset(db.Model):
    """资产主表"""
    __tablename__ = 'assets'

    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    asset_code = db.Column(db.String(32), unique=True, nullable=False, index=True)  # 资产编码

    # 基本信息
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    asset_type = db.Column(db.String(50), nullable=False)  # image/model/vector/document/video
    file_format = db.Column(db.String(20), nullable=True)  # JPG/PNG/SHP/OBJ/PDF/MP4
    file_size = db.Column(db.BigInteger, nullable=True)  # 文件大小(字节)
    file_hash = db.Column(db.String(64), nullable=True)  # SHA256哈希

    # 存储信息
    storage_path = db.Column(db.String(500), nullable=True)  # MinIO存储路径
    thumbnail_path = db.Column(db.String(500), nullable=True)  # 缩略图路径

    # 水印信息
    watermark_status = db.Column(db.String(20), default='none')  # none/pending/embedded
    watermark_id = db.Column(db.String(64), nullable=True, index=True)
    watermarked_path = db.Column(db.String(500), nullable=True)
    watermark_embedded_at = db.Column(db.DateTime, nullable=True)
    vr_value = db.Column(db.Text, nullable=True)  # 矢量水印验证值(JSON字符串)

    # 区块链存证
    chain_status = db.Column(db.String(20), default='none')  # none/pending/confirmed
    chain_tx_hash = db.Column(db.String(66), nullable=True, index=True)
    chain_timestamp = db.Column(db.DateTime, nullable=True)
    certificate_id = db.Column(db.String(64), nullable=True)

    # AI特征
    feature_status = db.Column(db.String(20), default='none')  # none/pending/done
    feature_vector_id = db.Column(db.BigInteger, nullable=True)  # Milvus向量ID

    # 所属信息
    garden_id = db.Column(db.Integer, db.ForeignKey('gardens.id'), nullable=True)
    creator_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    uploader_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)  # 上传者
    owner_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)  # 版权所有者

    # 版权信息
    copyright_status = db.Column(db.String(20), default='unregistered')  # unregistered/registered
    copyright_number = db.Column(db.String(50), nullable=True)  # 版权登记号

    # 统计信息
    view_count = db.Column(db.Integer, default=0)
    download_count = db.Column(db.Integer, default=0)
    license_count = db.Column(db.Integer, default=0)  # 授权次数
    favorite_count = db.Column(db.Integer, default=0)  # 收藏次数

    # 状态
    status = db.Column(db.String(20), default='draft')  # draft/pending/published/rejected/archived/deleted
    publish_at = db.Column(db.DateTime, nullable=True)  # 发布时间
    approver_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)  # 审核人
    approve_time = db.Column(db.DateTime, nullable=True)  # 审核时间
    reject_reason = db.Column(db.String(500), nullable=True)  # 拒绝原因

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系
    creator = db.relationship('User', foreign_keys=[creator_id], backref='created_assets')
    uploader = db.relationship('User', foreign_keys=[uploader_id], backref='uploaded_assets')
    owner = db.relationship('User', foreign_keys=[owner_id], backref='owned_assets')
    tags = db.relationship('AssetTag', backref='asset', lazy='dynamic', cascade='all, delete-orphan')
    features = db.relationship('AssetFeature', backref='asset', lazy='dynamic', cascade='all, delete-orphan')
    licenses = db.relationship('License', backref='asset', lazy='dynamic')
    versions = db.relationship(
        'AssetVersion',
        backref='asset',
        lazy='dynamic',
        cascade='all, delete-orphan'
    )

    def to_dict(self):
        vr_value = None
        if self.vr_value:
            try:
                parsed = json.loads(self.vr_value)
                if isinstance(parsed, (int, float)):
                    vr_value = parsed
            except (TypeError, ValueError):
                pass

        return {
            'id': self.id,
            'asset_code': self.asset_code,
            'title': self.title,
            'description': self.description,
            'asset_type': self.asset_type,
            'file_format': self.file_format,
            'file_size': self.file_size,
            'thumbnail_path': self.thumbnail_path,
            'watermark_status': self.watermark_status,
            'watermark_id': self.watermark_id,
            'watermark_embedded_at': self.watermark_embedded_at.isoformat() if self.watermark_embedded_at else None,
            'vr_value': vr_value,
            'chain_status': self.chain_status,
            'chain_tx_hash': self.chain_tx_hash,
            'chain_timestamp': self.chain_timestamp.isoformat() if self.chain_timestamp else None,
            'certificate_id': self.certificate_id,
            'garden_id': self.garden_id,
            'garden_name': self.garden.name if self.garden else None,
            'creator_id': self.creator_id,
            'owner_id': self.owner_id,
            'uploader_name': (self.uploader.nickname or self.uploader.username) if self.uploader else None,
            'creator_name': (self.creator.nickname or self.creator.username) if self.creator else None,
            'view_count': self.view_count,
            'download_count': self.download_count,
            'favorite_count': self.favorite_count,
            'license_count': self.license_count,
            'status': self.status,
            'publish_at': self.publish_at.isoformat() if self.publish_at else None,
            'reject_reason': self.reject_reason,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

    def __repr__(self):
        return f'<Asset {self.asset_code}: {self.title}>'


class AssetTag(db.Model):
    """资产标签表"""
    __tablename__ = 'asset_tags'

    id = db.Column(db.Integer, primary_key=True)
    asset_id = db.Column(db.String(36), db.ForeignKey('assets.id'), nullable=False)
    name = db.Column(db.String(50), nullable=False)  # 标签名称
    tag_name = db.Column(db.String(50), nullable=True)  # 别名，兼容旧代码
    tag_type = db.Column(db.String(20), nullable=True)  # style/scene/element/season
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name or self.tag_name,
            'tag_type': self.tag_type
        }


class AssetFeature(db.Model):
    """资产AI特征表"""
    __tablename__ = 'asset_features'

    id = db.Column(db.Integer, primary_key=True)
    asset_id = db.Column(db.String(36), db.ForeignKey('assets.id'), nullable=False)
    feature_type = db.Column(db.String(50), nullable=False)  # color/style/scene/season/object
    feature_value = db.Column(db.String(100), nullable=False)
    confidence = db.Column(db.Numeric(5, 4), nullable=True)  # AI识别置信度
    source = db.Column(db.String(20), default='ai')  # ai/manual
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'feature_type': self.feature_type,
            'feature_value': self.feature_value,
            'confidence': float(self.confidence) if self.confidence else None
        }


class AssetVersion(db.Model):
    """资产版本历史表

    每次上传新文件或恢复旧版本都会新增一条记录，历史文件保持原位不删除。
    资产主表始终指向当前版本；链上存证等历史信息保留在资产上，由证据链标记
    “当前文件已变更”。
    """
    __tablename__ = 'asset_versions'
    __table_args__ = (
        db.UniqueConstraint('asset_id', 'version_no', name='uk_asset_version'),
    )

    id = db.Column(db.Integer, primary_key=True)
    asset_id = db.Column(
        db.String(36), db.ForeignKey('assets.id'), nullable=False, index=True
    )
    version_no = db.Column(db.Integer, nullable=False)

    # 文件信息（file_path 为服务器上的绝对路径）
    file_path = db.Column(db.String(500), nullable=False)
    file_name = db.Column(db.String(255), nullable=True)
    file_format = db.Column(db.String(20), nullable=True)
    file_size = db.Column(db.BigInteger, nullable=True)
    file_hash = db.Column(db.String(64), nullable=True)
    thumbnail_path = db.Column(db.String(500), nullable=True)

    change_note = db.Column(db.String(500), nullable=True)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    creator = db.relationship('User', foreign_keys=[created_by], backref='asset_versions')

    def to_dict(self, is_current=False):
        return {
            'id': self.id,
            'asset_id': self.asset_id,
            'version_no': self.version_no,
            'file_name': self.file_name,
            'file_format': self.file_format,
            'file_size': self.file_size,
            'file_hash': self.file_hash,
            'change_note': self.change_note,
            'created_by': self.created_by,
            'creator_name': (self.creator.nickname or self.creator.username) if self.creator else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'is_current': bool(is_current)
        }

    def __repr__(self):
        return f'<AssetVersion {self.asset_id} v{self.version_no}>'
