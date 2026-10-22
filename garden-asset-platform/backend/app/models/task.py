"""异步任务表

水印嵌入与链上存证可能耗时较长，大文件同步处理会撞上 gunicorn 超时。
任务先落库，由进程内 worker 或独立 `flask tasks run` 进程领取执行；
状态持久化，失败可重试，进程重启后队列不丢。
"""
from datetime import datetime
import uuid

from app.extensions import db


TASK_TYPE_LABELS = {
    'watermark_embed': '水印嵌入',
    'blockchain_register': '链上存证',
    'infringement_patrol': '批量侵权巡检',
}

TASK_STATUS_LABELS = {
    'queued': '排队中',
    'running': '处理中',
    'succeeded': '已完成',
    'failed': '失败',
    'cancelled': '已取消',
}


def generate_task_id():
    return str(uuid.uuid4())


class AsyncTask(db.Model):
    """后台任务队列"""

    __tablename__ = 'async_tasks'

    id = db.Column(db.String(36), primary_key=True, default=generate_task_id)
    task_type = db.Column(db.String(40), nullable=False, index=True)
    status = db.Column(db.String(20), default='queued', nullable=False, index=True)

    asset_id = db.Column(
        db.String(36), db.ForeignKey('assets.id'), nullable=True, index=True
    )
    user_id = db.Column(
        db.Integer, db.ForeignKey('users.id'), nullable=True, index=True
    )

    # 入队时的文件版本；执行前会校验，避免把旧文件的水印/存证写到新版本上
    version_id = db.Column(db.Integer, nullable=True)
    payload = db.Column(db.JSON, nullable=True)
    result = db.Column(db.JSON, nullable=True)

    progress = db.Column(db.Integer, default=0)
    attempts = db.Column(db.Integer, default=0, nullable=False)
    max_attempts = db.Column(db.Integer, default=3, nullable=False)
    error_message = db.Column(db.Text, nullable=True)
    dedupe_key = db.Column(db.String(140), nullable=True, index=True)
    worker_id = db.Column(db.String(100), nullable=True)
    # 自动重试前的退避时间；到期后 worker 才会重新领取
    next_attempt_at = db.Column(db.DateTime, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    started_at = db.Column(db.DateTime, nullable=True)
    finished_at = db.Column(db.DateTime, nullable=True)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    asset = db.relationship('Asset', backref='async_tasks')
    user = db.relationship('User', backref='async_tasks')

    @property
    def is_active(self):
        return self.status in ('queued', 'running')

    def to_dict(self, include_payload=False):
        data = {
            'id': self.id,
            'task_type': self.task_type,
            'task_type_label': TASK_TYPE_LABELS.get(self.task_type, self.task_type),
            'status': self.status,
            'status_label': TASK_STATUS_LABELS.get(self.status, self.status),
            'asset_id': self.asset_id,
            'asset_code': self.asset.asset_code if self.asset else None,
            'asset_title': self.asset.title if self.asset else None,
            'version_id': self.version_id,
            'progress': self.progress or 0,
            'attempts': self.attempts or 0,
            'max_attempts': self.max_attempts or 0,
            'error_message': self.error_message,
            'result': self.result,
            'next_attempt_at': (
                self.next_attempt_at.isoformat() if self.next_attempt_at else None
            ),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'finished_at': self.finished_at.isoformat() if self.finished_at else None,
        }
        if include_payload:
            data['payload'] = self.payload or {}
        return data

    def __repr__(self):
        return f'<AsyncTask {self.task_type}:{self.status}>'
