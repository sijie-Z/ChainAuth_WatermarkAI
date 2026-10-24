"""系统级 Webhook 通知

管理员在后台配置一个 Webhook（支持通用 JSON 与企业微信群机器人）。
事件写入时若 Webhook 已启用，会同时生成 webhook 投递行；worker 按分组
筛选后 POST，支持 HMAC-SHA256 签名、失败退避重试与内网地址拦截。
"""
import hashlib
import hmac
import ipaddress
import json
import logging
import socket
import time
from datetime import datetime, timedelta
from urllib.parse import urlparse

import requests
from flask import current_app
from sqlalchemy import or_

from app.extensions import db
from app.models import NotificationDelivery, NotificationEvent, SystemConfig
from app.services.email_service import notification_group

logger = logging.getLogger(__name__)

CONFIG_KEYS = {
    'url': 'notification_webhook_url',
    'secret': 'notification_webhook_secret',
    'enabled': 'notification_webhook_enabled',
    'format': 'notification_webhook_format',
    'groups': 'notification_webhook_groups',
}
DEFAULT_GROUPS = ['asset', 'license', 'task', 'infringement']
WEBHOOK_GROUP_OPTIONS = ('asset', 'license', 'task', 'infringement')


def _config_rows():
    rows = SystemConfig.query.filter(
        SystemConfig.key.in_(list(CONFIG_KEYS.values()))
    ).all()
    return {row.key: row.value for row in rows}


def get_webhook_config():
    values = _config_rows()
    groups = DEFAULT_GROUPS
    raw_groups = values.get(CONFIG_KEYS['groups'])
    if raw_groups:
        try:
            parsed = json.loads(raw_groups)
            if isinstance(parsed, list):
                groups = [
                    item for item in parsed if item in WEBHOOK_GROUP_OPTIONS
                ]
        except (TypeError, ValueError):
            pass
    return {
        'enabled': values.get(CONFIG_KEYS['enabled'], 'false') == 'true',
        'url': values.get(CONFIG_KEYS['url'], '') or '',
        'secret': values.get(CONFIG_KEYS['secret'], '') or '',
        'format': values.get(CONFIG_KEYS['format'], 'json') or 'json',
        'groups': groups,
    }


def webhook_enabled():
    config = get_webhook_config()
    return bool(config['enabled'] and config['url'])


def _upsert(key, value, description=None):
    row = SystemConfig.query.filter_by(key=key).first()
    if not row:
        row = SystemConfig(key=key, description=description)
        db.session.add(row)
    row.value = value


def save_webhook_config(data):
    """保存配置；secret 留空表示不修改，clear_secret=true 表示清空。"""
    enabled = bool(data.get('enabled'))
    url = (data.get('url') or '').strip()
    webhook_format = (data.get('format') or 'json').strip()
    groups = data.get('groups', DEFAULT_GROUPS)
    if webhook_format not in ('json', 'wecom'):
        return 'Webhook 格式只能是 json 或 wecom'
    if not isinstance(groups, list):
        return '通知分组必须是数组'
    groups = [item for item in groups if item in WEBHOOK_GROUP_OPTIONS]
    if enabled and not url:
        return '启用 Webhook 前请填写地址'
    if url:
        parsed = urlparse(url)
        if parsed.scheme not in ('http', 'https') or not parsed.hostname:
            return 'Webhook 地址必须是 http/https URL'
        if len(url) > 500:
            return 'Webhook 地址过长'

    _upsert(CONFIG_KEYS['enabled'], 'true' if enabled else 'false',
            '是否启用系统 Webhook 通知')
    _upsert(CONFIG_KEYS['url'], url, 'Webhook 接收地址')
    _upsert(CONFIG_KEYS['format'], webhook_format,
            'Webhook 载荷格式：json/wecom')
    _upsert(CONFIG_KEYS['groups'], json.dumps(groups, ensure_ascii=False),
            'Webhook 订阅的事件分组')
    existing = _config_rows().get(CONFIG_KEYS['secret'], '')
    if data.get('clear_secret'):
        _upsert(CONFIG_KEYS['secret'], '', 'Webhook HMAC 签名密钥')
    elif (data.get('secret') or '').strip():
        _upsert(CONFIG_KEYS['secret'], data['secret'].strip()[:200],
                'Webhook HMAC 签名密钥')
    elif existing:
        # 保持原密钥
        pass
    db.session.commit()
    return None


def config_for_api():
    config = get_webhook_config()
    return {
        'enabled': config['enabled'],
        'url': config['url'],
        'format': config['format'],
        'groups': config['groups'],
        'secret_set': bool(config['secret']),
        'allow_private': bool(
            current_app.config.get('WEBHOOK_ALLOW_PRIVATE', False)
        ),
    }


def _validate_destination(url):
    parsed = urlparse(url)
    if parsed.scheme not in ('http', 'https') or not parsed.hostname:
        raise ValueError('Webhook 地址无效')
    if current_app.config.get('WEBHOOK_ALLOW_PRIVATE', False):
        return
    try:
        addresses = socket.getaddrinfo(parsed.hostname, parsed.port or 443)
    except socket.gaierror as exc:
        raise ValueError('Webhook 域名无法解析') from exc
    for info in addresses:
        ip = ipaddress.ip_address(info[4][0])
        if (
            ip.is_private or ip.is_loopback or ip.is_link_local
            or ip.is_reserved or ip.is_multicast
        ):
            raise ValueError('Webhook 不允许指向内网或保留地址')


def _payload(event, webhook_format):
    link = event.get('link') or ''
    base = (current_app.config.get('PUBLIC_BASE_URL') or '').rstrip('/')
    if base and link.startswith('/'):
        link = f'{base}{link}'
    if webhook_format == 'wecom':
        content = (
            f"[苏州园林数字资产平台]\n{event.get('title', '')}\n"
            f"{event.get('description') or ''}\n{link}"
        ).strip()
        return {'msgtype': 'text', 'text': {'content': content[:2000]}}
    return {
        'event_id': event.get('id'),
        'event_type': event.get('event_type'),
        'title': event.get('title'),
        'description': event.get('description'),
        'link': link,
        'created_at': event.get('created_at'),
    }


def _post(config, payload):
    url = config['url']
    _validate_destination(url)
    body = json.dumps(payload, ensure_ascii=False).encode('utf-8')
    headers = {
        'Content-Type': 'application/json; charset=utf-8',
        'User-Agent': 'ChainAuth-Webhook/1.0',
    }
    secret = config.get('secret') or ''
    if secret:
        timestamp = str(int(time.time()))
        signature = hmac.new(
            secret.encode('utf-8'),
            f'{timestamp}.'.encode('utf-8') + body,
            hashlib.sha256,
        ).hexdigest()
        headers['X-ChainAuth-Timestamp'] = timestamp
        headers['X-ChainAuth-Signature'] = f'sha256={signature}'

    response = requests.post(
        url, data=body, headers=headers, timeout=8, allow_redirects=False
    )
    if response.status_code < 200 or response.status_code >= 300:
        raise RuntimeError(f'Webhook 返回 HTTP {response.status_code}')
    if config.get('format') == 'wecom':
        try:
            data = response.json()
        except ValueError as exc:
            raise RuntimeError('企业微信 Webhook 返回非 JSON') from exc
        if data.get('errcode', 0) != 0:
            raise RuntimeError(
                f"企业微信 Webhook 错误: {data.get('errmsg') or data.get('errcode')}"
            )


def send_webhook(event, config=None):
    config = config or get_webhook_config()
    event_data = event.to_dict() if hasattr(event, 'to_dict') else event
    _post(config, _payload(event_data, config.get('format', 'json')))


def send_test_webhook(config):
    event = {
        'id': 0,
        'event_type': 'webhook_test',
        'title': 'Webhook 测试通知',
        'description': '如果你收到这条消息，说明 Webhook 配置可用。',
        'link': '/admin/notifications',
        'created_at': datetime.utcnow().isoformat(),
    }
    _post(config, _payload(event, config.get('format', 'json')))


def dispatch_pending_webhooks(limit=20):
    config = get_webhook_config()
    if not webhook_enabled():
        return {
            'configured': False, 'sent': 0, 'skipped': 0,
            'failed': 0, 'retried': 0
        }

    now = datetime.utcnow()
    deliveries = NotificationDelivery.query.filter(
        NotificationDelivery.channel == 'webhook',
        NotificationDelivery.status == 'pending',
        or_(
            NotificationDelivery.next_attempt_at.is_(None),
            NotificationDelivery.next_attempt_at <= now,
        ),    ).order_by(
        NotificationDelivery.created_at.asc(), NotificationDelivery.id.asc()
    ).limit(max(1, limit)).all()

    stats = {'configured': True, 'sent': 0, 'skipped': 0,
             'failed': 0, 'retried': 0}
    groups = set(config.get('groups') or [])

    for delivery in deliveries:
        event = NotificationEvent.query.get(delivery.event_id)
        if not event:
            delivery.status = 'skipped'
            delivery.error_message = '事件不存在'
            stats['skipped'] += 1
            db.session.commit()
            continue
        if notification_group(event.event_type) not in groups:
            delivery.status = 'skipped'
            delivery.error_message = '该事件分组未订阅 Webhook'
            stats['skipped'] += 1
            db.session.commit()
            continue

        try:
            send_webhook(event, config)
            delivery.status = 'sent'
            delivery.sent_at = now
            delivery.error_message = None
            stats['sent'] += 1
        except Exception as exc:
            logger.warning('Webhook 发送失败 delivery=%s: %s', delivery.id, exc)
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


def webhook_delivery_counts():
    rows = db.session.query(
        NotificationDelivery.status, db.func.count(NotificationDelivery.id)
    ).filter(
        NotificationDelivery.channel == 'webhook'
    ).group_by(NotificationDelivery.status).all()
    counts = {status: count for status, count in rows}
    return {
        'pending': counts.get('pending', 0),
        'sent': counts.get('sent', 0),
        'skipped': counts.get('skipped', 0),
        'failed': counts.get('failed', 0),
    }


def create_webhook_delivery(event):
    """事件写入时调用；Webhook 未启用则不创建投递行。"""
    try:
        if not webhook_enabled():
            return None
        delivery = NotificationDelivery(
            event_id=event.id, channel='webhook', status='pending'
        )
        db.session.add(delivery)
        return delivery
    except Exception:
        logger.exception('创建 Webhook 投递记录失败')
        return None
