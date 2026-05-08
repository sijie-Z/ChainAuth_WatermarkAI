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

    def test_change_password_success(self, client, auth_header):
        """测试修改密码成功"""
        response = client.post('/api/user/change-password',
            json={
                'old_password': 'test123',
                'new_password': 'newpass123'
            },
            headers=auth_header
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data['code'] == 200

    def test_change_password_wrong_old(self, client, auth_header):
        """测试修改密码旧密码错误"""
        response = client.post('/api/user/change-password',
            json={
                'old_password': 'wrongold',
                'new_password': 'newpass123'
            },
            headers=auth_header
        )

        assert response.status_code == 400

    def test_change_password_too_short(self, client, auth_header):
        """测试修改密码新密码太短"""
        response = client.post('/api/user/change-password',
            json={
                'old_password': 'test123',
                'new_password': '123'
            },
            headers=auth_header
        )

        assert response.status_code == 400

    def test_update_profile(self, client, auth_header):
        """测试更新个人信息"""
        response = client.put('/api/user/current',
            json={
                'email': 'updated@test.com',
                'phone': '13800138000'
            },
            headers=auth_header
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data['data']['email'] == 'updated@test.com'

    def test_register_role_injection(self, client):
        """测试注册角色注入攻击被阻止"""
        response = client.post('/api/register', json={
            'username': 'hacker',
            'password': 'password123',
            'email': 'hacker@test.com',
            'role': 'admin'
        })

        assert response.status_code == 200

        # 登录并验证角色是 user 而非 admin
        response = client.post('/api/login', json={
            'username': 'hacker',
            'password': 'password123'
        })
        data = response.get_json()
        assert data['data']['user']['role'] == 'user'