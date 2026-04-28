"""
测试配置
"""
import pytest
from app import create_app
from app.extensions import db


@pytest.fixture
def app():
    """创建测试应用"""
    app = create_app('testing')

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """创建测试客户端"""
    return app.test_client()


@pytest.fixture
def runner(app):
    """创建CLI测试运行器"""
    return app.test_cli_runner()


@pytest.fixture
def auth_header(client):
    """创建认证头"""
    # 注册用户
    client.post('/api/register', json={
        'username': 'testuser',
        'password': 'test123',
        'email': 'test@test.com'
    })

    # 登录获取token
    response = client.post('/api/login', json={
        'username': 'testuser',
        'password': 'test123'
    })

    data = response.get_json()
    token = data['data']['access_token']

    return {'Authorization': f'Bearer {token}'}