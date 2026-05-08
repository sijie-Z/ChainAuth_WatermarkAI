"""
区块链存证数据模型
"""
from datetime import datetime
import uuid
from app.extensions import db


class BlockchainTransaction(db.Model):
    """区块链交易记录表"""
    __tablename__ = 'blockchain_transactions'

    id = db.Column(db.Integer, primary_key=True)
    tx_hash = db.Column(db.String(66), unique=True, nullable=False, index=True)

    # 交易类型
    tx_type = db.Column(db.String(50), nullable=False)
    # asset_register: 资产存证
    # license_grant: 授权记录
    # license_revoke: 授权撤销
    # ownership_transfer: 权属转移

    # 关联资产
    asset_id = db.Column(db.String(36), db.ForeignKey('assets.id'), nullable=True)

    # 区块信息
    block_number = db.Column(db.BigInteger, nullable=True)
    block_hash = db.Column(db.String(66), nullable=True)

    # 交易信息
    from_address = db.Column(db.String(42), nullable=True)
    to_address = db.Column(db.String(42), nullable=True)
    gas_used = db.Column(db.BigInteger, nullable=True)
    gas_price = db.Column(db.BigInteger, nullable=True)

    # 状态
    status = db.Column(db.String(20), default='pending')  # pending/confirmed/failed
    confirmations = db.Column(db.Integer, default=0)

    # 原始数据
    raw_data = db.Column(db.JSON, nullable=True)
    error_message = db.Column(db.Text, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    confirmed_at = db.Column(db.DateTime, nullable=True)

    asset = db.relationship('Asset', backref='blockchain_transactions')

    def to_dict(self):
        return {
            'id': self.id,
            'tx_hash': self.tx_hash,
            'tx_type': self.tx_type,
            'asset_id': self.asset_id,
            'block_number': self.block_number,
            'block_hash': self.block_hash,
            'from_address': self.from_address,
            'to_address': self.to_address,
            'gas_used': self.gas_used,
            'status': self.status,
            'confirmations': self.confirmations,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'confirmed_at': self.confirmed_at.isoformat() if self.confirmed_at else None
        }


class Certificate(db.Model):
    """存证证书表"""
    __tablename__ = 'certificates'

    id = db.Column(db.Integer, primary_key=True)
    certificate_id = db.Column(db.String(64), unique=True, nullable=False, index=True)

    # 关联资产
    asset_id = db.Column(db.String(36), db.ForeignKey('assets.id'), unique=True, nullable=False)

    # 区块链信息
    tx_hash = db.Column(db.String(66), nullable=True)
    block_number = db.Column(db.BigInteger, nullable=True)

    # 水印信息
    watermark_id = db.Column(db.String(64), nullable=True)

    # 文件信息
    file_hash = db.Column(db.String(64), nullable=False)  # SHA256

    # 创建者信息
    creator_name = db.Column(db.String(100), nullable=True)
    creator_id_hash = db.Column(db.String(64), nullable=True)  # 身份证号哈希

    # 权属信息
    ownership_type = db.Column(db.String(50), default='original')
    # original: 原创
    # authorized: 授权使用
    # derived: 衍生作品

    # 有效期
    valid_from = db.Column(db.DateTime, default=datetime.utcnow)
    valid_until = db.Column(db.DateTime, nullable=True)

    # 证书文件
    certificate_file = db.Column(db.String(500), nullable=True)

    # 状态
    status = db.Column(db.String(20), default='valid')  # valid/revoked/expired

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    asset = db.relationship('Asset', backref='certificate', uselist=False)

    def to_dict(self):
        return {
            'id': self.id,
            'certificate_id': self.certificate_id,
            'asset_id': self.asset_id,
            'tx_hash': self.tx_hash,
            'block_number': self.block_number,
            'watermark_id': self.watermark_id,
            'file_hash': self.file_hash,
            'creator_name': self.creator_name,
            'ownership_type': self.ownership_type,
            'valid_from': self.valid_from.isoformat() if self.valid_from else None,
            'valid_until': self.valid_until.isoformat() if self.valid_until else None,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

    @staticmethod
    def generate_certificate_id():
        """生成证书编号"""
        return f"CERT-{datetime.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:4].upper()}"