"""
认证接口边界测试

聚焦注册/登录校验、资料更新的唯一性冲突，以及用户管理接口的权限分支。
"""
import pytest

from app.models.user import User


def register_and_login(client, username, password='pass1234', **extra):
    payload = {
        'username': username,
        'password': password,
        'email': f'{username}@test.com',
    }
    payload.update(extra)
    client.post('/api/register', json=payload)
    response = client.post('/api/login', json={'username': username, 'password': password})
    token = response.get_json()['data']['access_token']
    return {'Authorization': f'Bearer {token}'}


def current_user_id(client, headers):
    return client.get('/api/user/current', headers=headers).get_json()['data']['id']


class TestRegisterValidation:
    def test_rejects_html_in_username(self, client):
        response = client.post('/api/register', json={
            'username': '<script>alert(1)</script>',
            'password': 'pass1234',
        })

        assert response.status_code == 400
        assert '非法字符' in response.get_json()['message']

    def test_rejects_duplicate_email(self, client):
        client.post('/api/register', json={
            'username': 'first', 'password': 'pass1234', 'email': 'shared@test.com',
        })

        response = client.post('/api/register', json={
            'username': 'second', 'password': 'pass1234', 'email': 'shared@test.com',
        })

        assert response.status_code == 400
        assert '邮箱已被注册' in response.get_json()['message']

    def test_rejects_duplicate_phone(self, client):
        client.post('/api/register', json={
            'username': 'first', 'password': 'pass1234', 'phone': '13800138000',
        })

        response = client.post('/api/register', json={
            'username': 'second', 'password': 'pass1234', 'phone': '13800138000',
        })

        assert response.status_code == 400
        assert '手机号已被注册' in response.get_json()['message']

    def test_rejects_short_password(self, client):
        response = client.post('/api/register', json={
            'username': 'shorty', 'password': '12345',
        })

        assert response.status_code == 400
        assert '少于6位' in response.get_json()['message']

    def test_returns_500_when_persistence_fails(self, client, app, monkeypatch):
        from app.resources import auth as auth_resource

        def broken_commit(*args, **kwargs):
            raise RuntimeError('database is down')

        monkeypatch.setattr(auth_resource.db.session, 'commit', broken_commit)

        response = client.post('/api/register', json={
            'username': 'dbfail', 'password': 'pass1234',
        })

        assert response.status_code == 500
        assert response.get_json()['message'] == '注册失败，请稍后重试'


class TestLoginBranches:
    def test_missing_credentials(self, client):
        response = client.post('/api/login', json={})

        assert response.status_code == 400
        assert '不能为空' in response.get_json()['message']

    def test_disabled_account_is_rejected(self, client, app):
        client.post('/api/register', json={
            'username': 'banned', 'password': 'pass1234', 'email': 'banned@test.com',
        })
        with app.app_context():
            user = User.query.filter_by(username='banned').first()
            user.status = 'banned'
            app.extensions['sqlalchemy'].session.commit()

        response = client.post('/api/login', json={
            'username': 'banned', 'password': 'pass1234',
        })

        assert response.status_code == 403
        assert '已被禁用' in response.get_json()['message']


class TestProfileUpdate:
    def test_rejects_email_used_by_another_user(self, client, auth_header):
        other_header = register_and_login(client, 'otheruser')

        response = client.put('/api/user/current', headers=other_header, json={
            'email': 'test@test.com',
        })

        assert response.status_code == 400
        assert '邮箱已被使用' in response.get_json()['message']

    def test_rejects_phone_used_by_another_user(self, client, auth_header):
        other_header = register_and_login(client, 'phoneman')
        client.put('/api/user/current', headers=other_header, json={'phone': '13900139000'})

        response = client.put('/api/user/current', headers=auth_header, json={
            'phone': '13900139000',
        })

        assert response.status_code == 400
        assert '手机号已被使用' in response.get_json()['message']

    def test_returns_500_when_profile_update_fails(self, client, auth_header, app, monkeypatch):
        from app.resources import auth as auth_resource

        def broken_commit(*args, **kwargs):
            raise RuntimeError('database is down')

        monkeypatch.setattr(auth_resource.db.session, 'commit', broken_commit)

        response = client.put('/api/user/current', headers=auth_header, json={
            'nickname': 'will-not-save',
        })

        assert response.status_code == 500
        assert response.get_json()['message'] == '更新失败'

    def test_change_password_requires_both_fields(self, client, auth_header):
        response = client.post('/api/user/change-password', headers=auth_header, json={
            'old_password': 'test123',
        })

        assert response.status_code == 400
        assert '请填写完整' in response.get_json()['message']


class TestUserAdministration:
    def test_normal_user_cannot_list_users(self, client, auth_header):
        response = client.get('/api/users', headers=auth_header)

        assert response.status_code == 403
        assert response.get_json()['message'] == '无权限'

    def test_admin_lists_users(self, client, admin_header):
        response = client.get('/api/users', headers=admin_header)

        assert response.status_code == 200
        usernames = {item['username'] for item in response.get_json()['data']}
        assert 'admin' in usernames

    @pytest.mark.parametrize('payload, expected', [
        ({'password': 'pass1234'}, '用户名和密码不能为空'),
        ({'username': 'someone', 'password': '123'}, '密码长度不能少于 6 位'),
        ({'username': 'someone', 'password': 'pass1234', 'status': 'zombie'}, '无效的状态'),
        ({'username': 'admin', 'password': 'pass1234'}, '用户名已存在'),
    ])
    def test_admin_create_user_validation(self, client, admin_header, payload, expected):
        response = client.post('/api/users', headers=admin_header, json=payload)

        assert response.status_code == 400
        assert expected in response.get_json()['message']

    def test_normal_user_cannot_update_another_user(self, client, auth_header):
        target = current_user_id(client, auth_header)
        other_header = register_and_login(client, 'intruder')

        response = client.put(f'/api/users/{target}', headers=other_header, json={
            'nickname': 'hacked',
        })

        assert response.status_code == 403

    def test_admin_update_missing_user_returns_404(self, client, admin_header):
        response = client.put('/api/users/999999', headers=admin_header, json={
            'nickname': 'ghost',
        })

        assert response.status_code == 404
        assert response.get_json()['message'] == '用户不存在'

    @pytest.mark.parametrize('payload, expected', [
        ({'role': 'super_admin'}, '无效的角色'),
        ({'status': 'zombie'}, '无效的状态'),
    ])
    def test_admin_update_rejects_invalid_enum(self, client, admin_header, auth_header, payload, expected):
        target = current_user_id(client, auth_header)

        response = client.put(f'/api/users/{target}', headers=admin_header, json=payload)

        assert response.status_code == 400
        assert expected in response.get_json()['message']

    def test_admin_can_update_role_and_status(self, client, admin_header, auth_header, app):
        target = current_user_id(client, auth_header)

        response = client.put(f'/api/users/{target}', headers=admin_header, json={
            'role': 'asset_admin',
            'status': 'inactive',
            'email': 'reassigned@test.com',
            'phone': '13700137000',
        })

        assert response.status_code == 200
        data = response.get_json()['data']
        assert data['role'] == 'asset_admin'
        assert data['status'] == 'inactive'
        assert data['email'] == 'reassigned@test.com'
        assert data['phone'] == '13700137000'

    def test_user_cannot_escalate_own_role(self, client, auth_header, app):
        target = current_user_id(client, auth_header)

        response = client.put(f'/api/users/{target}', headers=auth_header, json={
            'role': 'admin',
            'nickname': 'still-a-user',
        })

        assert response.status_code == 200
        assert response.get_json()['data']['role'] == 'user'
        with app.app_context():
            assert User.query.get(target).role == 'user'
