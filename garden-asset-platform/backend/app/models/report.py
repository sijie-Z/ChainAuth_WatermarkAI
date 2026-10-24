"""疑似侵权线索

公开溯源页可以提交疑似盗用文件或链接；系统会尝试提取水印并匹配资产，
后台管理员可受理、确认或驳回。确认/驳回会通知举报人与资产权利人。
"""
from datetime import datetime
import uuid

from app.extensions import db


def generate_report_code():
    return f"IR-{datetime.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:4].upper()}"


class InfringementReport(db.Model):
    """侵权线索表"""

    __tablename__ = 'infringement_reports'

    id = db.Column(db.Integer, primary_key=True)
    report_code = db.Column(
        db.String(40), unique=True, nullable=False, default=generate_report_code
    )

    asset_id = db.Column(
        db.String(36), db.ForeignKey('assets.id'), nullable=True, index=True
    )
    reporter_id = db.Column(
        db.Integer, db.ForeignKey('users.id'), nullable=True, index=True
    )
    reporter_name = db.Column(db.String(100), nullable=True)
    contact = db.Column(db.String(200), nullable=True)

    source_url = db.Column(db.String(500), nullable=True)
    description = db.Column(db.Text, nullable=True)

    # 举报文件只保存在服务端，后台下载查看；不对外暴露路径
    suspect_filename = db.Column(db.String(255), nullable=True)
    suspect_file_path = db.Column(db.String(500), nullable=True)
    suspect_file_hash = db.Column(db.String(64), nullable=True)
    suspect_file_size = db.Column(db.BigInteger, nullable=True)

    # 溯源匹配结果
    watermark_id = db.Column(db.String(64), nullable=True)
    certificate_id = db.Column(db.String(64), nullable=True)
    trace_verified = db.Column(db.Boolean, default=False)

    status = db.Column(db.String(20), default='pending', index=True)
    # pending/reviewing/confirmed/rejected
    reviewer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    review_comment = db.Column(db.Text, nullable=True)
    reviewed_at = db.Column(db.DateTime, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    asset = db.relationship('Asset', backref=db.backref('infringement_reports', lazy='dynamic'))
    reporter = db.relationship(
        'User', foreign_keys=[reporter_id],
        backref=db.backref('infringement_reports', lazy='dynamic')
    )
    reviewer = db.relationship('User', foreign_keys=[reviewer_id])

    def to_dict(self, include_private=False):
        data = {
            'id': self.id,
            'report_code': self.report_code,
            'asset_id': self.asset_id,
            'asset_code': self.asset.asset_code if self.asset else None,
            'asset_title': self.asset.title if self.asset else None,
            'source_url': self.source_url,
            'description': self.description,
            'watermark_id': self.watermark_id,
            'certificate_id': self.certificate_id,
            'trace_verified': bool(self.trace_verified),
            'status': self.status,
            'has_file': bool(self.suspect_file_path),
            'suspect_filename': self.suspect_filename,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'reviewed_at': self.reviewed_at.isoformat() if self.reviewed_at else None,
        }
        if include_private:
            data.update({
                'reporter_id': self.reporter_id,
                'reporter_name': self.reporter_name,
                'reporter_username': (
                    self.reporter.username if self.reporter else None
                ),
                'contact': self.contact,
                'suspect_file_hash': self.suspect_file_hash,
                'suspect_file_size': self.suspect_file_size,
                'reviewer_name': (
                    (self.reviewer.nickname or self.reviewer.username)
                    if self.reviewer else None
                ),
                'review_comment': self.review_comment,
            })
        return data
