"""邮件通知投递

事件写入时创建 notification_deliveries(pending)，本服务由 worker/CLI 调用：
按用户偏好与事件分组筛选，通过 SMTP 发送，失败按次数退避重试。
SMTP 未配置时不做任何发送，也不把待投递记录标成失败。
"""
import logging
import smtplib
from datetime import datetime, timedelta
from email.message import EmailMessage

from flask import current_app
from sqlalchemy import or_

from app.extensions import db
from app.models.extra import (
    NotificationDelivery, NotificationEvent, NotificationPreference
)
from app.models.user import User

logger = logging.getLogger(__name__)

EMAIL_GROUPS = ('asset', 'license', 'task', 'infringement')


def notification_group(event_type):
    value = event_type or ''
    if value.startswith('license_'):
        return 'license'
    if value.startswith('asset_task_'):
        return 'task'
    if value.startswith('infringement_'):
        return 'infringement'
    if value.startswith('asset_'):
        return 'asset'
    if value.startswith('comment'):
        return 'comment'
    return 'system'


def mail_configured():
    return bool(
        current_app.config.get('MAIL_ENABLED')
        and current_app.config.get('MAIL_HOST')
    )


def send_email(to_address, subject, body):
    """发送纯文本邮件；配置不完整或发送失败时抛异常。"""
    if not mail_configured():
        raise RuntimeError('SMTP 未配置')

    host = current_app.config.get('MAIL_HOST')
    port = int(current_app.config.get('MAIL_PORT', 587))
    username = current_app.config.get('MAIL_USERNAME') or ''
    password = current_app.config.get('MAIL_PASSWORD') or ''
    from_address = current_app.config.get('MAIL_FROM') or username
    use_tls = bool(current_app.config.get('MAIL_USE_TLS', True))
    use_ssl = bool(current_app.config.get('MAIL_USE_SSL', False))
    timeout = int(current_app.config.get('MAIL_TIMEOUT', 10))

    message = EmailMessage()
    message['Subject'] = subject
    message['From'] = from_address
    message['To'] = to_address
    message.set_content(body)

    if use_ssl:
        smtp = smtplib.SMTP_SSL(host, port, timeout=timeout)
    else:
        smtp = smtplib.SMTP(host, port, timeout=timeout)
    try:
        if use_tls and not use_ssl:
            smtp.starttls()
        if username:
            smtp.login(username, password)
        smtp.send_message(message)
    finally:
        try:
            smtp.quit()
        except Exception:
            pass


def _event_link(event):
    base = (current_app.config.get('PUBLIC_BASE_URL') or '').rstrip('/')
    link = event.link or '/notifications'
    return f'{base}{link}' if base else link


def _delivery_body(event):
    lines = [
        event.title,
        '',
        event.description or '',
        '',
        f'查看详情：{_event_link(event)}',
        '',
        '—— 苏州园林数字资产平台',
        '本邮件由系统自动发送，可在“账号设置 → 通知设置”中关闭邮件通知。',
    ]
    return '\n'.join(lines)


def dispatch_pending_emails(limit=20):
    """发送到期的待投递邮件，返回统计。"""
    if not mail_configured():
        return {
            'mail_configured': False,
            'sent': 0, 'skipped': 0, 'failed': 0, 'retried': 0
        }

    now = datetime.utcnow()
    deliveries = NotificationDelivery.query.filter(
        NotificationDelivery.channel == 'email',
        NotificationDelivery.status == 'pending',
        or_(
            NotificationDelivery.next_attempt_at.is_(None),
            NotificationDelivery.next_attempt_at <= now,
        ),    ).order_by(
        NotificationDelivery.created_at.asc(), NotificationDelivery.id.asc()
    ).limit(max(1, limit)).all()

    stats = {'mail_configured': True, 'sent': 0, 'skipped': 0,
             'failed': 0, 'retried': 0}

    for delivery in deliveries:
        event = NotificationEvent.query.get(delivery.event_id)
        user = User.query.get(event.user_id) if event else None
        preference = (
            NotificationPreference.query.filter_by(user_id=user.id).first()
            if user else None
        )

        if not event or not user or not user.email:
            delivery.status = 'skipped'
            delivery.error_message = (
                '事件或用户不存在' if not event or not user else '用户未设置邮箱'
            )
            stats['skipped'] += 1
            db.session.commit()
            continue

        groups = (
            preference.email_groups
            if preference and preference.email_groups is not None
            else ['asset', 'license', 'task', 'infringement']
        )
        if (
            not preference
            or not preference.email_enabled
            or notification_group(event.event_type) not in groups
        ):
            delivery.status = 'skipped'
            delivery.error_message = '用户未开启该分组邮件通知'
            stats['skipped'] += 1
            db.session.commit()
            continue

        try:
            subject = f'[苏州园林数字资产平台] {event.title}'
            subject = subject.replace('\r', ' ').replace('\n', ' ')
            send_email(
                user.email,
                subject,
                _delivery_body(event),
            )
            delivery.status = 'sent'
            delivery.sent_at = now
            delivery.error_message = None
            stats['sent'] += 1
        except Exception as exc:
            logger.warning('邮件发送失败 delivery=%s: %s', delivery.id, exc)
            delivery.attempts = (delivery.attempts or 0) + 1
            delivery.error_message = str(exc)[:500]
            if delivery.attempts >= 3:
                delivery.status = 'failed'
                stats['failed'] += 1
            else:
                delivery.status = 'pending'
                delivery.next_attempt_at = now + timedelta(
                    seconds=60 * delivery.attempts
                )
                stats['retried'] += 1
        db.session.commit()

    return stats


def delivery_counts():
    rows = db.session.query(
        NotificationDelivery.status, db.func.count(NotificationDelivery.id)
    ).filter(NotificationDelivery.channel == 'email').group_by(
        NotificationDelivery.status
    ).all()
    counts = {status: count for status, count in rows}
    return {
        'pending': counts.get('pending', 0),
        'sent': counts.get('sent', 0),
        'skipped': counts.get('skipped', 0),
        'failed': counts.get('failed', 0),
    }


def send_test_email(user):
    if not user or not user.email:
        raise ValueError('当前账号未设置邮箱')
    send_email(
        user.email,
        '[苏州园林数字资产平台] 邮件通知测试',
        (
            f'{user.nickname or user.username}，你好：\n\n'
            '这是一封测试邮件，说明当前部署的 SMTP 配置可用。\n'
            '你可以在“账号设置 → 通知设置”中管理邮件通知。\n\n'
            '—— 苏州园林数字资产平台'
        ),
    )
