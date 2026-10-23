"""事件型站内通知

审核结果、授权撤销/续期等需要保留正文的事件写入 notification_events。
调用方负责 commit，便于与业务事务保持一致。
"""
from app.extensions import db
from app.models import NotificationDelivery, NotificationEvent


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
    db.session.flush()
    # 邮件投递与事件同一事务写入，worker 按用户偏好决定发送或跳过
    db.session.add(NotificationDelivery(
        event_id=event.id,
        channel='email',
        status='pending',
    ))
    try:
        from app.services.webhook_service import create_webhook_delivery
        create_webhook_delivery(event)
    except Exception:
        # Webhook 配置异常不能阻断业务事件
        pass
    return event
