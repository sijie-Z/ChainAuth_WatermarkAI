"""图纸/影像区域标注数据模型

标注以归一化坐标（0-1）绑定到资产上，可选绑定到具体版本：
默认展示当前版本的标注，历史版本可单独查看。
"""
from datetime import datetime

from app.extensions import db

ANNOTATION_TYPES = ('note', 'issue', 'suggestion')
ANNOTATION_STATUSES = ('open', 'resolved')


class AssetAnnotation(db.Model):
    """资产区域标注表"""
    __tablename__ = 'asset_annotations'

    id = db.Column(db.Integer, primary_key=True)
    asset_id = db.Column(
        db.String(36), db.ForeignKey('assets.id'), nullable=False, index=True
    )
    version_id = db.Column(
        db.Integer, db.ForeignKey('asset_versions.id'), nullable=True, index=True
    )
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    # 归一化坐标（0-1），x/y 为左上角，width/height 为宽高
    x = db.Column(db.Float, nullable=False)
    y = db.Column(db.Float, nullable=False)
    width = db.Column(db.Float, nullable=False)
    height = db.Column(db.Float, nullable=False)

    title = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=True)
    annotation_type = db.Column(db.String(20), default='note', nullable=False)
    status = db.Column(db.String(20), default='open', nullable=False)
    resolved_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    resolved_at = db.Column(db.DateTime, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = db.relationship(
        'User', foreign_keys=[user_id], backref=db.backref('annotations', lazy='dynamic')
    )
    resolver = db.relationship('User', foreign_keys=[resolved_by])
    asset = db.relationship('Asset', backref=db.backref('annotations', lazy='dynamic'))
    version = db.relationship('AssetVersion')

    def __repr__(self):
        return f'<AssetAnnotation {self.id} asset={self.asset_id} status={self.status}>'
