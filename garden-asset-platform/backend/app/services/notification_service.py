"""事件型站内通知

审核结果、授权撤销/续期等需要保留正文的事件写入 notification_events。
调用方负责 commit，便于与业务事务保持一致。
"""
from app.extensions import db
from app.models import NotificationEvent


def add_notification_event(user_id, event_type, title, description=None, link=None):
    if not user_id:
        return None
    event = NotificationEvent(
        user_id=user_id,
        event_type=event_type,
        title=title[:200],
        description=(description or '')[:500] or None,
        link=(link or '')[:300] or None
    )
    db.session.add(event)
    return event
