"""忘记密码与邮箱验证流程"""
from urllib.parse import parse_qs, urlparse


def _token_from_url(url):
    return parse_qs(urlparse(url).query)['token'][0]


def test_forgot_password_reset_flow(client, auth_header):
    forgot = client.post('/api/forgot-password', json={'email': 'test@test.com'})
    assert forgot.status_code == 200, forgot.get_json()
    data = forgot.get_json()['data']
    assert data['sent'] is False
    assert 'dev_reset_url' in data
    token = _token_from_url(data['dev_reset_url'])

    reset = client.post('/api/reset-password', json={
        'token': token,
        'new_password': 'newpass123',
    })
    assert reset.status_code == 200, reset.get_json()

    old_login = client.post('/api/login', json={
        'username': 'testuser', 'password': 'test123'
    })
    assert old_login.status_code == 401
    new_login = client.post('/api/login', json={
        'username': 'testuser', 'password': 'newpass123'
    })
    assert new_login.status_code == 200

    reused = client.post('/api/reset-password', json={
        'token': token,
        'new_password': 'another123',
    })
    assert reused.status_code == 400


def test_forgot_password_unknown_email_is_generic(client):
    response = client.post('/api/forgot-password', json={
        'email': 'nobody@test.com'
    })
    assert response.status_code == 200
    data = response.get_json()['data']
    assert data['sent'] is False
    assert 'dev_reset_url' not in data


def test_email_verification_flow_and_email_change(client, auth_header):
    sent = client.post('/api/verify-email/send', headers=auth_header)
    assert sent.status_code == 200, sent.get_json()
    data = sent.get_json()['data']
    assert 'dev_verify_url' in data
    token = _token_from_url(data['dev_verify_url'])

    verified = client.post('/api/verify-email', json={'token': token})
    assert verified.status_code == 200, verified.get_json()

    current = client.get('/api/user/current', headers=auth_header)
    assert current.get_json()['data']['email_verified'] is True

    changed = client.put(
        '/api/user/current',
        headers=auth_header,
        json={'email': 'changed@test.com'},
    )
    assert changed.status_code == 200, changed.get_json()
    current = client.get('/api/user/current', headers=auth_header)
    assert current.get_json()['data']['email_verified'] is False


def test_tampered_reset_token_rejected(client):
    response = client.post('/api/reset-password', json={
        'token': 'not-a-valid-token',
        'new_password': 'newpass123',
    })
    assert response.status_code == 400
    assert '无效' in response.get_json()['message']
