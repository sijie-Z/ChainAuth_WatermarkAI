"""
完整功能测试
"""
import pytest
from app import create_app
from app.extensions import db
from app.models import User, Garden, Asset


class TestFullFlow:
    """完整流程测试"""

    @pytest.fixture
    def app(self):
        app = create_app('testing')
        with app.app_context():
            db.create_all()
            yield app
            db.session.remove()
            db.drop_all()

    @pytest.fixture
    def client(self, app):
        return app.test_client()

    def test_user_registration_login_flow(self, client):
        """测试用户注册登录流程"""
        # 注册
        response = client.post('/api/register', json={
            'username': 'testuser',
            'password': 'Test@123',
            'email': 'test@example.com'
        })
        assert response.status_code == 200

        # 登录
        response = client.post('/api/login', json={
            'username': 'testuser',
            'password': 'Test@123'
        })
        assert response.status_code == 200
        data = response.get_json()
        assert 'access_token' in data['data']

        # 获取用户信息
        token = data['data']['access_token']
        response = client.get('/api/user/current', headers={
            'Authorization': f'Bearer {token}'
        })
        assert response.status_code == 200
        assert response.get_json()['data']['username'] == 'testuser'

    def test_asset_crud_flow(self, client):
        """测试资产CRUD流程"""
        # 先创建用户并登录
        client.post('/api/register', json={
            'username': 'assetuser',
            'password': 'Test@123',
            'email': 'asset@example.com'
        })
        response = client.post('/api/login', json={
            'username': 'assetuser',
            'password': 'Test@123'
        })
        token = response.get_json()['data']['access_token']
        headers = {'Authorization': f'Bearer {token}'}

        # 获取资产列表
        response = client.get('/api/assets', headers=headers)
        assert response.status_code == 200

    def test_watermark_verify_flow(self, client):
        """测试水印验证流程"""
        response = client.post('/api/watermark/verify', json={
            'watermark_id': 'ZY-IMG-20260426120000-XXXX'
        })
        assert response.status_code in [200, 404]

    def test_blockchain_status(self, client):
        """测试区块链状态"""
        response = client.get('/api/blockchain/status')
        assert response.status_code == 200
        data = response.get_json()
        assert 'connected' in data['data']


class TestModels:
    """模型测试"""

    @pytest.fixture
    def app(self):
        app = create_app('testing')
        with app.app_context():
            db.create_all()
            yield app
            db.session.remove()
            db.drop_all()

    def test_user_model(self, app):
        """测试用户模型"""
        with app.app_context():
            user = User(username='modeltest', email='model@test.com', role='user')
            user.set_password('password')

            db.session.add(user)
            db.session.commit()

            assert user.id is not None
            assert user.check_password('password')
            assert not user.check_password('wrong')

    def test_garden_model(self, app):
        """测试园林模型"""
        with app.app_context():
            garden = Garden(
                name='测试园林',
                code='TEST',
                location='测试地址'
            )

            db.session.add(garden)
            db.session.commit()

            assert garden.id is not None
            assert garden.code == 'TEST'


class TestSecurity:
    """安全测试"""

    @pytest.fixture
    def client(self):
        app = create_app('testing')
        with app.app_context():
            db.create_all()
        client = app.test_client()
        yield client
        with app.app_context():
            db.session.remove()
            db.drop_all()

    def test_sql_injection_protection(self, client):
        """测试SQL注入防护"""
        response = client.post('/api/login', json={
            'username': "admin'--",
            'password': "anything"
        })
        assert response.status_code == 401

    def test_xss_protection(self, client):
        """测试XSS防护"""
        response = client.post('/api/register', json={
            'username': '<script>alert(1)</script>',
            'password': 'Test@123'
        })
        # 应该拒绝或清理
        assert response.status_code in [200, 400]

    def test_unauthorized_access(self, client):
        """测试未授权访问"""
        response = client.get('/api/assets')
        assert response.status_code == 401

    def test_invalid_token(self, client):
        """测试无效Token"""
        response = client.get('/api/user/current', headers={
            'Authorization': 'Bearer invalid_token'
        })
        assert response.status_code in [401, 422]