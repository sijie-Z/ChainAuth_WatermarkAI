"""
安全相关回归测试：限流响应、安全响应头、健康检查
"""
import pytest

from app.utils import middleware


@pytest.fixture(autouse=True)
def clear_memory_rate_limits():
    """避免内存限流状态在测试之间串扰"""
    with middleware._memory_lock:
        middleware._memory_rate_limits.clear()
    yield
    with middleware._memory_lock:
        middleware._memory_rate_limits.clear()


def test_login_rate_limit_returns_429_not_500(app, client):
    """超过登录限流阈值时应返回 429 JSON，而不是 Flask-RESTful 序列化 500"""
    app.config['RATELIMIT_ENABLED'] = True

    for _ in range(5):
        response = client.post('/api/login', json={'username': 'nobody', 'password': 'wrong'})
        assert response.status_code == 401

    response = client.post('/api/login', json={'username': 'nobody', 'password': 'wrong'})
    assert response.status_code == 429
    body = response.get_json()
    assert body['code'] == 429
    assert '频繁' in body['message']


def test_security_headers_present(client):
    response = client.get('/health')

    assert response.headers['X-Content-Type-Options'] == 'nosniff'
    assert response.headers['X-Frame-Options'] == 'DENY'
    assert response.headers['X-XSS-Protection'] == '1; mode=block'
    assert 'Content-Security-Policy' in response.headers


def test_health_endpoint_reports_database(client):
    response = client.get('/health')

    assert response.status_code == 200
    body = response.get_json()
    assert body['status'] == 'healthy'
    assert body['database'] == 'connected'
    assert body['service'] == 'garden-asset-platform'
