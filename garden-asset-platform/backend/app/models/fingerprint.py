"""下载指纹

授权用户下载影像时，在保留原盲水印的基础上生成一份带可见页脚的副本：
页脚包含资产编码、授权编号、被授权账号和唯一指纹码。每个 (授权, 资产)
只生成一次并复用，下载台账通过 fingerprint_id 回溯到具体副本。
"""
from datetime import datetime
import uuid

from app.extensions import db


def generate_fingerprint_code():
    return f"FP-{datetime.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:8].upper()}"


class DownloadFingerprint(db.Model):
    __tablename__ = 'download_fingerprints'
    __table_args__ = (
        db.UniqueConstraint('license_id', 'asset_id', name='uk_license_asset_fingerprint'),
    )

    id = db.Column(db.Integer, primary_key=True)
    fingerprint_code = db.Column(
        db.String(64), unique=True, nullable=False, index=True,
        default=generate_fingerprint_code,
    )
    asset_id = db.Column(
        db.String(36), db.ForeignKey('assets.id'), nullable=False, index=True
    )
    license_id = db.Column(
        db.Integer, db.ForeignKey('licenses.id'), nullable=False, index=True
    )
    user_id = db.Column(
        db.Integer, db.ForeignKey('users.id'), nullable=False, index=True
    )

    file_path = db.Column(db.String(500), nullable=False)
    file_hash = db.Column(db.String(64), nullable=True)
    file_size = db.Column(db.BigInteger, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    asset = db.relationship('Asset', backref=db.backref('download_fingerprints', lazy='dynamic'))
    license = db.relationship('License', backref=db.backref('download_fingerprints', lazy='dynamic'))
    user = db.relationship('User', backref=db.backref('download_fingerprints', lazy='dynamic'))

    def to_dict(self):
        return {
            'id': self.id,
            'fingerprint_code': self.fingerprint_code,
            'asset_id': self.asset_id,
            'license_id': self.license_id,
            'user_id': self.user_id,
            'file_hash': self.file_hash,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
