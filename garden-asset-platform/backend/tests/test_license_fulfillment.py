"""授权履约：撤销、续期、独家互斥与生效时间"""
from datetime import datetime, timedelta

import pytest

from app.extensions import db
from app.models import Asset, Garden, License, LicenseApplication, User


def _login(client, username, password):
    response = client.post('/api/login', json={
        'username': username,
        'password': password
    })
    assert response.status_code == 200
    return {'Authorization': f"Bearer {response.get_json()['data']['access_token']}"}


@pytest.fixture
def licensee_header(client):
    client.post('/api/register', json={
        'username': 'licensee',
        'password': 'test123',
        'email': 'licensee@test.com'
    })
    return _login(client, 'licensee', 'test123')


@pytest.fixture
def licensed_asset(app, auth_header, licensee_header):
    with app.app_context():
        owner = User.query.filter_by(username='testuser').first()
        licensee = User.query.filter_by(username='licensee').first()
        garden = Garden(code='FUL', name='履约测试园', status='active')
        db.session.add(garden)
        db.session.flush()
        asset = Asset(
            asset_code='FUL-IMG-001',
            title='履约测试资产',
            asset_type='image',
            garden_id=garden.id,
            creator_id=owner.id,
            owner_id=owner.id,
            uploader_id=owner.id,
            status='published'
        )
        db.session.add(asset)
        db.session.flush()
        license_row = License(
            license_code='LIC-FUL-001',
            asset_id=asset.id,
            licensor_id=owner.id,
            licensee_id=licensee.id,
            license_type='non_commercial',
            usage_scope='测试',
            start_time=datetime.utcnow() - timedelta(days=1),
            end_time=datetime.utcnow() + timedelta(days=30),
            status='active'
        )
        db.session.add(license_row)
        db.session.commit()
        return {
            'asset_id': asset.id,
            'license_id': license_row.id,
            'owner_id': owner.id,
            'licensee_id': licensee.id
        }


def test_owner_can_revoke_and_licensee_loses_download(
    client, app, auth_header, licensee_header, licensed_asset
):
    response = client.post(
        f"/api/license/{licensed_asset['license_id']}/revoke",
        headers=auth_header,
        json={'reason': '项目取消'}
    )
    assert response.status_code == 200
    assert response.get_json()['data']['status'] == 'revoked'

    download = client.get(
        f"/api/assets/{licensed_asset['asset_id']}/download",
        headers=licensee_header
    )
    assert download.status_code == 403

    notifications = client.get('/api/notifications', headers=licensee_header)
    titles = [item['title'] for item in notifications.get_json()['data']['items']]
    assert '授权已被撤销' in titles


def test_licensee_cannot_revoke_or_renew(
    client, auth_header, licensee_header, licensed_asset
):
    revoke = client.post(
        f"/api/license/{licensed_asset['license_id']}/revoke",
        headers=licensee_header,
        json={}
    )
    assert revoke.status_code == 403
    renew = client.post(
        f"/api/license/{licensed_asset['license_id']}/renew",
        headers=licensee_header,
        json={'end_time': (datetime.utcnow() + timedelta(days=365)).strftime('%Y-%m-%d')}
    )
    assert renew.status_code == 403


def test_owner_can_renew_license(client, app, auth_header, licensed_asset):
    new_end = (datetime.utcnow() + timedelta(days=365)).strftime('%Y-%m-%d')
    response = client.post(
        f"/api/license/{licensed_asset['license_id']}/renew",
        headers=auth_header,
        json={'end_time': new_end}
    )
    assert response.status_code == 200
    assert response.get_json()['data']['end_time'].startswith(new_end)


def test_future_license_does_not_allow_download(
    client, app, auth_header, licensee_header, licensed_asset
):
    with app.app_context():
        license_row = db.session.get(License, licensed_asset['license_id'])
        license_row.start_time = datetime.utcnow() + timedelta(days=5)
        db.session.commit()

    download = client.get(
        f"/api/assets/{licensed_asset['asset_id']}/download",
        headers=licensee_header
    )
    assert download.status_code == 403


def test_exclusive_application_conflicts_with_active_license(
    client, app, admin_header, licensed_asset
):
    with app.app_context():
        applicant = User.query.filter_by(username='licensee').first()
        application = LicenseApplication(
            application_code='APP-FUL-EXCLUSIVE',
            asset_id=licensed_asset['asset_id'],
            applicant_id=applicant.id,
            license_type='exclusive',
            is_exclusive=True,
            usage_scope='独家使用',
            status='adm1_approved',
            adm1_status='approved',
            adm2_status='pending'
        )
        db.session.add(application)
        db.session.commit()
        application_id = application.id

    response = client.post(
        f'/api/license/approve/{application_id}',
        headers=admin_header,
        json={'action': 'approve', 'comment': '同意'}
    )
    assert response.status_code == 409
    assert '独家' in response.get_json()['message']
