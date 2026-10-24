"""系统 Webhook 通知测试"""
import json

import pytest

from app.extensions import db
from app.models import NotificationDelivery, User
from app.services import webhook_service
from app.services.notification_service import add_notification_event


class FakeResponse:
    def __init__(self, status_code=200, body=None):
        self.status_code = status_code
        self._body = body or {'errcode': 0}

    def json(self):
        return self._body


def enable_webhook(client, admin_header, **overrides):
    payload = {
        'enabled': True,
        'url': 'https://example.com/webhook',
        'secret': 'test-secret',
        'format': 'json',
        'groups': ['asset', 'license', 'task', 'infringement'],
    }
    payload.update(overrides)
    return client.put(
        '/api/system/notification-webhook',
        json=payload,
        headers=admin_header,
    )


def test_webhook_config_crud_and_secret_masking(client, admin_header):
    response = client.get(
        '/api/system/notification-webhook', headers=admin_header
    )
    assert response.status_code == 200
    config = response.get_json()['data']['config']
    assert config['enabled'] is False
    assert config['secret_set'] is False
    assert 'secret' not in config

    saved = enable_webhook(client, admin_header, format='wecom', groups=['license'])
    assert saved.status_code == 200, saved.get_json()
    data = saved.get_json()['data']
    assert data['enabled'] is True
    assert data['format'] == 'wecom'
    assert data['groups'] == ['license']
    assert data['secret_set'] is True

    # 留空 secret 不覆盖原值
    assert enable_webhook(
        client, admin_header, secret='', groups=['asset']
    ).status_code == 200
    response = client.get(
        '/api/system/notification-webhook', headers=admin_header
    )
    assert response.get_json()['data']['config']['secret_set'] is True


def test_webhook_requires_super_admin(client, auth_header):
    response = client.get(
        '/api/system/notification-webhook', headers=auth_header
    )
    assert response.status_code == 403
    response = client.put(
        '/api/system/notification-webhook',
        json={'enabled': True, 'url': 'https://example.com/hook'},
        headers=auth_header,
    )
    assert response.status_code == 403


def test_event_creates_webhook_delivery_and_dispatch(
    client, app, admin_header, monkeypatch
):
    assert enable_webhook(client, admin_header).status_code == 200
    calls = []

    def fake_post(url, data, headers, timeout, allow_redirects):
        calls.append({'url': url, 'data': data, 'headers': headers})
        return FakeResponse(200, {'ok': True})

    monkeypatch.setattr(webhook_service.requests, 'post', fake_post)
    with app.app_context():
        user = User.query.filter_by(username='admin').one()
        event = add_notification_event(
            user.id, 'license_approved', '授权已通过', '测试正文', '/license/my'
        )
        db.session.commit()
        delivery = NotificationDelivery.query.filter_by(
            event_id=event.id, channel='webhook'
        ).one()
        assert delivery.status == 'pending'

        result = webhook_service.dispatch_pending_webhooks()
        assert result['sent'] == 1
        assert calls[0]['url'] == 'https://example.com/webhook'
        assert calls[0]['headers']['X-ChainAuth-Signature'].startswith('sha256=')
        payload = json.loads(calls[0]['data'].decode('utf-8'))
        assert payload['title'] == '授权已通过'

        delivery = db.session.get(NotificationDelivery, delivery.id)
        assert delivery.status == 'sent'


def test_webhook_group_filter_and_failure_retry(
    client, app, admin_header, monkeypatch
):
    assert enable_webhook(
        client, admin_header, groups=['license']
    ).status_code == 200
    calls = []

    def fake_post(*args, **kwargs):
        calls.append(1)
        return FakeResponse(500)

    monkeypatch.setattr(webhook_service.requests, 'post', fake_post)
    with app.app_context():
        user = User.query.filter_by(username='admin').one()
        skipped_event = add_notification_event(
            user.id, 'asset_approved', '资产审核通过', '资产组未订阅'
        )
        retry_event = add_notification_event(
            user.id, 'license_approved', '授权通过', '授权组'
        )
        db.session.commit()

        first = webhook_service.dispatch_pending_webhooks()
        assert first['skipped'] == 1
        assert first['retried'] == 1
        skipped = NotificationDelivery.query.filter_by(
            event_id=skipped_event.id, channel='webhook'
        ).one()
        assert skipped.status == 'skipped'

        delivery = NotificationDelivery.query.filter_by(
            event_id=retry_event.id, channel='webhook'
        ).one()
        for attempt in (2, 3):
            delivery.next_attempt_at = None
            db.session.commit()
            webhook_service.dispatch_pending_webhooks()
            delivery = db.session.get(NotificationDelivery, delivery.id)
            assert delivery.attempts == attempt
        assert delivery.status == 'failed'
        assert len(calls) == 3


def test_webhook_test_endpoint(client, app, admin_header, monkeypatch):
    assert enable_webhook(client, admin_header).status_code == 200
    monkeypatch.setattr(
        webhook_service.requests, 'post',
        lambda *args, **kwargs: FakeResponse(200, {'ok': True}),
    )
    response = client.post(
        '/api/system/notification-webhook/test', headers=admin_header
    )
    assert response.status_code == 200, response.get_json()
    assert '已发送' in response.get_json()['message']


def test_webhook_blocks_private_destination(app):
    with app.app_context():
        app.config['WEBHOOK_ALLOW_PRIVATE'] = False
        with pytest.raises(ValueError, match='内网'):
            webhook_service._validate_destination('http://127.0.0.1/hook')
