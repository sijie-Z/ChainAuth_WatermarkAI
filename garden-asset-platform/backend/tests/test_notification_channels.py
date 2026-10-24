"""通知渠道测试

覆盖邮件偏好、投递记录、SMTP 派发失败重试与 SSE 实时流。
"""
from app.extensions import db
from app.models import (
    NotificationDelivery, NotificationEvent, NotificationPreference, User
)
from app.services import email_service
from app.services.notification_service import add_notification_event


def _set_mail(app, enabled=True):
    app.config['MAIL_ENABLED'] = enabled
    app.config['MAIL_HOST'] = 'smtp.example.com' if enabled else ''
    app.config['MAIL_PORT'] = 587
    app.config['MAIL_FROM'] = 'noreply@example.com'
    app.config['PUBLIC_BASE_URL'] = 'https://garden.example.com'


def _enable_email(app, user_id, groups=None):
    pref = NotificationPreference.query.filter_by(user_id=user_id).first()
    if not pref:
        pref = NotificationPreference(user_id=user_id)
        db.session.add(pref)
    pref.email_enabled = True
    pref.email_groups = groups or ['asset', 'license', 'task']
    db.session.commit()


def test_preferences_default_and_update(client, app, auth_header):
    response = client.get('/api/notifications/preferences', headers=auth_header)
    assert response.status_code == 200
    data = response.get_json()['data']
    assert data['email_enabled'] is False
    assert data['email'] == 'test@test.com'
    assert data['mail_configured'] is False

    response = client.put(
        '/api/notifications/preferences',
        json={'email_enabled': True, 'email_groups': ['license']},
        headers=auth_header
    )
    assert response.status_code == 200, response.get_json()
    assert response.get_json()['data']['email_groups'] == ['license']

    response = client.get('/api/notifications/preferences', headers=auth_header)
    assert response.get_json()['data']['email_enabled'] is True


def test_preferences_reject_invalid_group(client, auth_header):
    response = client.put(
        '/api/notifications/preferences',
        json={'email_enabled': True, 'email_groups': ['unknown']},
        headers=auth_header
    )
    assert response.status_code == 400


def test_event_creates_pending_delivery(client, app, auth_header):
    with app.app_context():
        user = User.query.filter_by(username='testuser').one()
        event = add_notification_event(
            user.id, 'license_approved', '授权已通过', '测试正文', '/license/my'
        )
        db.session.commit()
        delivery = NotificationDelivery.query.filter_by(event_id=event.id).one()
        assert delivery.status == 'pending'
        assert delivery.channel == 'email'

    # SMTP 未配置时不发送、也不误判失败
    with app.app_context():
        result = email_service.dispatch_pending_emails()
        assert result['mail_configured'] is False
        assert NotificationDelivery.query.filter_by(status='pending').count() == 1


def test_dispatch_sends_email(client, app, auth_header, monkeypatch):
    _set_mail(app)
    sent = []

    def fake_send(to_address, subject, body):
        sent.append({'to': to_address, 'subject': subject, 'body': body})

    monkeypatch.setattr(email_service, 'send_email', fake_send)

    with app.app_context():
        user = User.query.filter_by(username='testuser').one()
        _enable_email(app, user.id, ['license'])
        add_notification_event(
            user.id, 'license_approved', '授权已通过', '《拙政园》授权生效', '/license/my'
        )
        db.session.commit()

        result = email_service.dispatch_pending_emails()
        assert result['sent'] == 1
        assert sent[0]['to'] == 'test@test.com'
        assert '授权已通过' in sent[0]['subject']
        assert 'https://garden.example.com/license/my' in sent[0]['body']

        delivery = NotificationDelivery.query.one()
        assert delivery.status == 'sent'
        assert delivery.sent_at is not None


def test_dispatch_skips_disabled_group(client, app, auth_header, monkeypatch):
    _set_mail(app)
    monkeypatch.setattr(email_service, 'send_email', lambda *args: None)

    with app.app_context():
        user = User.query.filter_by(username='testuser').one()
        _enable_email(app, user.id, ['asset'])
        add_notification_event(
            user.id, 'license_approved', '授权已通过', '测试', '/license/my'
        )
        db.session.commit()

        result = email_service.dispatch_pending_emails()
        assert result['skipped'] == 1
        assert NotificationDelivery.query.one().status == 'skipped'


def test_dispatch_retries_then_fails(client, app, auth_header, monkeypatch):
    _set_mail(app)

    def failing_send(*args):
        raise RuntimeError('smtp down')

    monkeypatch.setattr(email_service, 'send_email', failing_send)

    with app.app_context():
        user = User.query.filter_by(username='testuser').one()
        _enable_email(app, user.id, ['license'])
        add_notification_event(
            user.id, 'license_approved', '授权已通过', '测试', '/license/my'
        )
        db.session.commit()

        for attempt in range(1, 4):
            delivery = NotificationDelivery.query.one()
            delivery.next_attempt_at = None
            db.session.commit()
            result = email_service.dispatch_pending_emails()
            delivery = NotificationDelivery.query.one()
            assert delivery.attempts == attempt
            if attempt < 3:
                assert result['retried'] == 1
                assert delivery.status == 'pending'
            else:
                assert result['failed'] == 1
                assert delivery.status == 'failed'


def test_send_email_uses_smtp_settings(app, monkeypatch):
    _set_mail(app)
    app.config['MAIL_USERNAME'] = 'smtp-user'
    app.config['MAIL_PASSWORD'] = 'smtp-pass'
    sent = []

    class FakeSMTP:
        def __init__(self, host, port, timeout=None):
            self.host = host
            self.port = port
            self.started_tls = False
            self.logged_in = False

        def starttls(self):
            self.started_tls = True

        def login(self, username, password):
            self.logged_in = (username, password)

        def send_message(self, message):
            sent.append(message)

        def quit(self):
            pass

    monkeypatch.setattr(email_service.smtplib, 'SMTP', FakeSMTP)

    email_service.send_email('user@example.com', '主题', '正文')

    assert len(sent) == 1
    assert sent[0]['To'] == 'user@example.com'
    assert sent[0]['From'] == 'noreply@example.com'
    assert sent[0].get_content().strip() == '正文'


def test_test_email_requires_smtp(client, auth_header):
    response = client.post('/api/notifications/test-email', headers=auth_header)
    assert response.status_code == 503
    assert 'SMTP' in response.get_json()['message']


def test_sse_stream_returns_new_events(client, app, auth_header):
    with app.app_context():
        user = User.query.filter_by(username='testuser').one()
        add_notification_event(
            user.id, 'asset_approved', '资产审核通过', '可以发布了', '/assets/demo'
        )
        db.session.commit()

    response = client.get(
        '/api/notifications/stream?since_id=0',
        headers=auth_header,
        buffered=False,
    )
    assert response.status_code == 200
    assert response.mimetype == 'text/event-stream'

    body = response.get_data(as_text=True)
    assert 'event: notification' in body
    assert '资产审核通过' in body
    assert 'https://garden.example.com' not in body  # 事件只存相对链接
    assert ': heartbeat' in body


def test_sse_requires_auth(client):
    response = client.get('/api/notifications/stream?since_id=0')
    assert response.status_code == 401
