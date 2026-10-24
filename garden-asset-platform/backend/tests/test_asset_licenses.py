"""资产所有者查看授权/申请记录"""
from datetime import datetime, timedelta

from app.extensions import db
from app.models import Asset, License, LicenseApplication, User


def _create_records(app, asset_id):
    with app.app_context():
        asset = db.session.get(Asset, asset_id)
        owner = db.session.get(User, asset.owner_id)
        licensee = User(
            username='asset_licensee',
            email='asset_licensee@test.com',
            password_hash='x',
            role='user',
            status='active',
        )
        db.session.add(licensee)
        db.session.flush()

        license_row = License(
            license_code='LIC-ASSET-VIEW-001',
            asset_id=asset.id,
            licensor_id=owner.id,
            licensee_id=licensee.id,
            license_type='personal',
            usage_scope='资产所有者可见性测试',
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow() + timedelta(days=30),
            status='active',
        )
        application = LicenseApplication(
            application_code='APP-ASSET-VIEW-001',
            asset_id=asset.id,
            applicant_id=licensee.id,
            license_type='personal',
            usage_scope='资产所有者可见性测试',
            status='pending',
            adm1_status='pending',
            adm2_status='pending',
        )
        db.session.add_all([license_row, application])
        db.session.commit()


def _login(client, username, password):
    client.post('/api/register', json={
        'username': username,
        'password': password,
        'email': f'{username}@test.com',
    })
    response = client.post('/api/login', json={
        'username': username,
        'password': password,
    })
    return {'Authorization': f"Bearer {response.get_json()['data']['access_token']}"}


def test_owner_can_list_asset_licenses_and_applications(
    client, app, auth_header, sample_asset
):
    _create_records(app, sample_asset)

    response = client.get(
        f'/api/assets/{sample_asset}/licenses', headers=auth_header
    )

    assert response.status_code == 200
    data = response.get_json()['data']
    assert data['asset_code'] == 'ZY-IMG-20260101-001'
    assert len(data['licenses']) == 1
    assert data['licenses'][0]['licensee_name'] == 'asset_licensee'
    assert data['licenses'][0]['can_revoke'] is True
    assert len(data['applications']) == 1
    assert data['applications'][0]['applicant_name'] == 'asset_licensee'


def test_unrelated_user_cannot_list_asset_licenses(
    client, app, auth_header, sample_asset
):
    _create_records(app, sample_asset)
    other_header = _login(client, 'license_viewer', 'viewer123')

    response = client.get(
        f'/api/assets/{sample_asset}/licenses', headers=other_header
    )

    assert response.status_code == 403
