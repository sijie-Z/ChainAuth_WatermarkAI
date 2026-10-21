"""登录会话安全：登出撤销 refresh、改密使旧 token 失效"""
import time


def _login(client, username, password):
    response = client.post('/api/login', json={
        'username': username,
        'password': password
    })
    assert response.status_code == 200
    return response.get_json()['data']


def test_logout_revokes_refresh_token(client):
    client.post('/api/register', json={
        'username': 'sessionuser',
        'password': 'test123',
        'email': 'session@test.com'
    })
    tokens = _login(client, 'sessionuser', 'test123')
    access = tokens['access_token']
    refresh = tokens['refresh_token']

    refresh_headers = {'Authorization': f'Bearer {refresh}'}
    assert client.post('/api/refresh', headers=refresh_headers).status_code == 200

    logout = client.post(
        '/api/logout',
        headers={'Authorization': f'Bearer {access}'},
        json={'refresh_token': refresh}
    )
    assert logout.status_code == 200

    # access 与 refresh 都应立即失效
    assert client.get(
        '/api/user/current',
        headers={'Authorization': f'Bearer {access}'}
    ).status_code == 401
    assert client.post('/api/refresh', headers=refresh_headers).status_code == 401


def test_password_change_invalidates_existing_tokens(client):
    client.post('/api/register', json={
        'username': 'pwuser',
        'password': 'oldpass123',
        'email': 'pw@test.com'
    })
    tokens = _login(client, 'pwuser', 'oldpass123')
    access = tokens['access_token']
    headers = {'Authorization': f'Bearer {access}'}

    assert client.get('/api/user/current', headers=headers).status_code == 200

    # JWT 的 iat 精确到秒，留出跨秒时间，避免同秒签发被判为有效
    time.sleep(1.1)
    changed = client.post('/api/user/change-password', headers=headers, json={
        'old_password': 'oldpass123',
        'new_password': 'newpass123'
    })
    assert changed.status_code == 200

    assert client.get('/api/user/current', headers=headers).status_code == 401
    assert client.post('/api/login', json={
        'username': 'pwuser',
        'password': 'oldpass123'
    }).status_code == 401
    assert client.post('/api/login', json={
        'username': 'pwuser',
        'password': 'newpass123'
    }).status_code == 200
