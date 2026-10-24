"""资产评论数据模型

评论用于资产详情页的公开讨论，支持一级回复（parent_id 指向同资产评论）。
删除采用软删除：回复仍然保留，父评论被删除时前端拿到的 reply_to_name 为 None。
"""
from datetime import datetime

from app.extensions import db


class AssetComment(db.Model):
    """资产评论表"""
    __tablename__ = 'asset_comments'

    id = db.Column(db.Integer, primary_key=True)
    asset_id = db.Column(
        db.String(36), db.ForeignKey('assets.id'), nullable=False, index=True
    )
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    parent_id = db.Column(
        db.Integer, db.ForeignKey('asset_comments.id'), nullable=True
    )
    content = db.Column(db.Text, nullable=False)
    is_deleted = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = db.relationship('User', backref=db.backref('asset_comments', lazy='dynamic'))
    asset = db.relationship('Asset', backref=db.backref('comments', lazy='dynamic'))
    parent = db.relationship(
        'AssetComment',
        remote_side=[id],
        backref=db.backref('replies', lazy='dynamic')
    )

    def __repr__(self):
        return f'<AssetComment {self.id} asset={self.asset_id}>'
