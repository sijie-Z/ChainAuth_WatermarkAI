"""
测试配置
"""
import pytest
from app import create_app
from app.extensions import db
from app.models.user import User
from app.models.garden import Garden
from app.models.asset import Asset


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
    client.post('/api/register', json={
        'username': 'testuser',
        'password': 'test123',
        'email': 'test@test.com'
    })

    response = client.post('/api/login', json={
        'username': 'testuser',
        'password': 'test123'
    })

    data = response.get_json()
    token = data['data']['access_token']

    return {'Authorization': f'Bearer {token}'}


@pytest.fixture
def admin_header(client, app):
    """创建管理员认证头"""
    # 注册用户（角色会被强制设为 user）
    client.post('/api/register', json={
        'username': 'admin',
        'password': 'admin123',
        'email': 'admin@test.com'
    })

    # 直接在数据库中提升为管理员
    with app.app_context():
        user = User.query.filter_by(username='admin').first()
        user.role = 'admin'
        db.session.commit()

    response = client.post('/api/login', json={
        'username': 'admin',
        'password': 'admin123'
    })

    data = response.get_json()
    token = data['data']['access_token']

    return {'Authorization': f'Bearer {token}'}


@pytest.fixture
def adm1_header(client, app):
    """创建资产管理员认证头"""
    client.post('/api/register', json={
        'username': 'adm1',
        'password': 'adm1123',
        'email': 'adm1@test.com'
    })
    with app.app_context():
        user = User.query.filter_by(username='adm1').first()
        user.role = 'adm1'
        db.session.commit()
    response = client.post('/api/login', json={'username': 'adm1', 'password': 'adm1123'})
    token = response.get_json()['data']['access_token']
    return {'Authorization': f'Bearer {token}'}


@pytest.fixture
def adm2_header(client, app):
    """创建授权管理员认证头"""
    client.post('/api/register', json={
        'username': 'adm2',
        'password': 'adm2123',
        'email': 'adm2@test.com'
    })
    with app.app_context():
        user = User.query.filter_by(username='adm2').first()
        user.role = 'adm2'
        db.session.commit()
    response = client.post('/api/login', json={'username': 'adm2', 'password': 'adm2123'})
    token = response.get_json()['data']['access_token']
    return {'Authorization': f'Bearer {token}'}


@pytest.fixture
def sample_garden(app):
    """创建示例园林"""
    with app.app_context():
        garden = Garden(
            code='ZY',
            name='拙政园',
            name_en='Humble Administrator\'s Garden',
            description='苏州著名园林',
            location='苏州市姑苏区东北街178号',
            status='active'
        )
        db.session.add(garden)
        db.session.commit()
        garden_id = garden.id
    return garden_id


@pytest.fixture
def sample_asset(app, sample_garden):
    """创建示例资产"""
    with app.app_context():
        # 获取一个用户ID
        user = User.query.first()
        user_id = user.id if user else 1

        asset = Asset(
            asset_code='ZY-IMG-20260101-001',
            title='拙政园荷风四面亭',
            description='测试资产',
            asset_type='image',
            file_format='JPG',
            garden_id=sample_garden,
            creator_id=user_id,
            uploader_id=user_id,
            owner_id=user_id,
            status='published'
        )
        db.session.add(asset)
        db.session.commit()
        asset_id = asset.id
    return asset_id
