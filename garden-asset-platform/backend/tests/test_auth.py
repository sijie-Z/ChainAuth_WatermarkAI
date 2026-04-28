"""
认证模块测试
"""
import pytest


class TestAuth:
    """认证测试类"""

    def test_register_success(self, client):
        """测试注册成功"""
        response = client.post('/api/register', json={
            'username': 'newuser',
            'password': 'password123',
            'email': 'newuser@test.com'
        })

        assert response.status_code == 200
        data = response.get_json()
        assert data['code'] == 200
        assert 'user_id' in data['data']

    def test_register_duplicate_username(self, client):
        """测试重复用户名注册"""
        # 第一次注册
        client.post('/api/register', json={
            'username': 'duplicate',
            'password': 'password123',
            'email': 'dup1@test.com'
        })

        # 第二次注册相同用户名
        response = client.post('/api/register', json={
            'username': 'duplicate',
            'password': 'password123',
            'email': 'dup2@test.com'
        })

        assert response.status_code == 400

    def test_register_missing_fields(self, client):
        """测试缺少必填字段"""
        response = client.post('/api/register', json={
            'username': 'no_password'
        })

        assert response.status_code == 400

    def test_login_success(self, client):
        """测试登录成功"""
        # 先注册
        client.post('/api/register', json={
            'username': 'loginuser',
            'password': 'password123',
            'email': 'login@test.com'
        })

        # 登录
        response = client.post('/api/login', json={
            'username': 'loginuser',
            'password': 'password123'
        })

        assert response.status_code == 200
        data = response.get_json()
        assert 'access_token' in data['data']
        assert 'refresh_token' in data['data']

    def test_login_wrong_password(self, client):
        """测试错误密码登录"""
        client.post('/api/register', json={
            'username': 'wrongpass',
            'password': 'correct',
            'email': 'wrong@test.com'
        })

        response = client.post('/api/login', json={
            'username': 'wrongpass',
            'password': 'wrong'
        })

        assert response.status_code == 401

    def test_login_nonexistent_user(self, client):
        """测试不存在的用户登录"""
        response = client.post('/api/login', json={
            'username': 'nouser',
            'password': 'password'
        })

        assert response.status_code == 401

    def test_get_current_user(self, client, auth_header):
        """测试获取当前用户"""
        response = client.get('/api/user/current', headers=auth_header)

        assert response.status_code == 200
        data = response.get_json()
        assert data['data']['username'] == 'testuser'

    def test_get_current_user_unauthorized(self, client):
        """测试未认证获取用户"""
        response = client.get('/api/user/current')

        assert response.status_code == 401

    def test_logout(self, client, auth_header):
        """测试登出"""
        response = client.post('/api/logout', headers=auth_header)

        assert response.status_code == 200

    def test_refresh_token(self, client):
        """测试刷新Token"""
        # 注册并登录
        client.post('/api/register', json={
            'username': 'refresh',
            'password': 'password123',
            'email': 'refresh@test.com'
        })

        response = client.post('/api/login', json={
            'username': 'refresh',
            'password': 'password123'
        })

        refresh_token = response.get_json()['data']['refresh_token']

        # 刷新Token
        response = client.post('/api/refresh', headers={
            'Authorization': f'Bearer {refresh_token}'
        })

        assert response.status_code == 200
        data = response.get_json()
        assert 'access_token' in data['data']