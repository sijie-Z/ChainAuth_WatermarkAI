"""权限收敛：非资产管理角色不能改删资产；审批人不能自批"""
import pytest

from app.extensions import db
from app.models import Asset, Garden, LicenseApplication, User


def _garden(app):
    with app.app_context():
        garden = Garden.query.first()
        if not garden:
            garden = Garden(code='PERM', name='权限测试园', status='active')
            db.session.add(garden)
            db.session.commit()
        return garden.id


def _asset(app, owner_id, garden_id, code='PERM-IMG-001'):
    with app.app_context():
        asset = Asset(
            asset_code=code,
            title='权限测试资产',
            asset_type='image',
            garden_id=garden_id,
            creator_id=owner_id,
            owner_id=owner_id,
            uploader_id=owner_id,
            status='published'
        )
        db.session.add(asset)
        db.session.commit()
        return asset.id


@pytest.fixture
def license_admin_header(client, app):
    client.post('/api/register', json={
        'username': 'licadmin',
        'password': 'test123',
        'email': 'licadmin@test.com'
    })
    with app.app_context():
        user = User.query.filter_by(username='licadmin').first()
        user.role = 'license_admin'
        db.session.commit()
    login = client.post('/api/login', json={
        'username': 'licadmin',
        'password': 'test123'
    })
    return {'Authorization': f"Bearer {login.get_json()['data']['access_token']}"}


def test_license_admin_cannot_edit_or_delete_others_asset(
    client, app, auth_header, license_admin_header
):
    with app.app_context():
        owner = User.query.filter_by(username='testuser').first()
        owner_id = owner.id
    asset_id = _asset(app, owner_id, _garden(app))

    edited = client.put(
        f'/api/assets/{asset_id}',
        headers=license_admin_header,
        json={'title': '越权修改'}
    )
    assert edited.status_code == 403

    deleted = client.delete(f'/api/assets/{asset_id}', headers=license_admin_header)
    assert deleted.status_code == 403


def test_approver_cannot_approve_own_application(client, app, admin_header):
    with app.app_context():
        admin = User.query.filter_by(username='admin').first()
        admin_id = admin.id
        garden_id = _garden(app)
        asset_id = _asset(app, admin_id, garden_id, code='PERM-IMG-002')
        application = LicenseApplication(
            application_code='APP-SELF-APPROVE',
            asset_id=asset_id,
            applicant_id=admin_id,
            license_type='personal',
            usage_scope='测试自批',
            status='pending',
            adm1_status='pending',
            adm2_status='pending'
        )
        db.session.add(application)
        db.session.commit()
        application_id = application.id

    response = client.post(
        f'/api/license/approve/{application_id}',
        headers=admin_header,
        json={'action': 'approve', 'comment': '自批'}
    )
    assert response.status_code == 403
    assert '自己' in response.get_json()['message']


def test_system_status_is_admin_only_and_reports_simulation(
    client, auth_header, admin_header
):
    assert client.get('/api/system/status', headers=auth_header).status_code == 403

    response = client.get('/api/system/status', headers=admin_header)
    assert response.status_code == 200
    data = response.get_json()['data']
    assert data['blockchain']['simulated'] is True
    assert data['ai']['enabled'] is False
    assert data['redis']['enabled'] in (True, False)
