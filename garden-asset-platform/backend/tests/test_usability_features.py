"""收藏、相关资产、搜索排序、申请撤回、合同与待办提醒测试"""
from datetime import datetime, timedelta
from io import BytesIO

import pytest
from PIL import Image

from app.extensions import db
from app.models import Asset, Garden, License, LicenseApplication, User


def _jpeg_bytes():
    buffer = BytesIO()
    Image.new('RGB', (320, 240), (47, 107, 90)).save(buffer, 'JPEG')
    buffer.seek(0)
    return buffer


@pytest.fixture
def owner_asset(app, auth_header):
    with app.app_context():
        user = User.query.filter_by(username='testuser').first()
        garden = Garden(code='TS', name='测试园', status='active')
        db.session.add(garden)
        db.session.flush()

        assets = []
        for index in range(3):
            asset = Asset(
                asset_code=f'TS-IMG-2026-{index:03d}',
                title=f'测试园林影像 {index}',
                description='用于搜索与相关资产测试',
                asset_type='image',
                garden_id=garden.id,
                creator_id=user.id,
                owner_id=user.id,
                uploader_id=user.id,
                status='published',
                view_count=index * 10,
                download_count=index,
            )
            db.session.add(asset)
            assets.append(asset)
        db.session.commit()
        return {
            'user_id': user.id,
            'garden_id': garden.id,
            'asset_ids': [asset.id for asset in assets],
        }


def test_favorite_is_idempotent(client, auth_header, owner_asset):
    asset_id = owner_asset['asset_ids'][0]

    state = client.get(f'/api/assets/{asset_id}/favorite', headers=auth_header)
    assert state.status_code == 200
    assert state.get_json()['data']['favorited'] is False

    first = client.post(f'/api/assets/{asset_id}/favorite', headers=auth_header)
    second = client.post(f'/api/assets/{asset_id}/favorite', headers=auth_header)
    assert first.status_code == second.status_code == 200
    assert second.get_json()['data']['favorited'] is True

    listing = client.get('/api/favorites', headers=auth_header)
    assert listing.status_code == 200
    assert listing.get_json()['data']['total'] == 1
    assert listing.get_json()['data']['items'][0]['id'] == asset_id

    assert client.delete(f'/api/assets/{asset_id}/favorite', headers=auth_header).status_code == 200
    assert client.delete(f'/api/assets/{asset_id}/favorite', headers=auth_header).status_code == 200


def test_related_assets_stay_in_same_garden(client, auth_header, owner_asset):
    response = client.get(
        f"/api/assets/{owner_asset['asset_ids'][0]}/related",
        headers=auth_header
    )

    assert response.status_code == 200
    related = response.get_json()['data']
    assert len(related) == 2
    assert {item['garden_id'] for item in related} == {owner_asset['garden_id']}


def test_keyword_search_and_sort(client, auth_header, owner_asset):
    search = client.get('/api/assets?keyword=TS-IMG-2026-001', headers=auth_header)
    assert search.status_code == 200
    assert search.get_json()['data']['total'] == 1

    popular = client.get('/api/assets?sort=popular', headers=auth_header)
    assert popular.status_code == 200
    view_counts = [item['view_count'] for item in popular.get_json()['data']['items']]
    assert view_counts == sorted(view_counts, reverse=True)


def test_application_can_be_cancelled_by_applicant(client, auth_header, owner_asset):
    with client.application.app_context():
        application = LicenseApplication(
            application_code='APP-CANCEL-TEST',
            asset_id=owner_asset['asset_ids'][0],
            applicant_id=owner_asset['user_id'],
            license_type='personal',
            usage_scope='测试用途',
            status='pending',
            adm1_status='pending',
            adm2_status='pending',
        )
        db.session.add(application)
        db.session.commit()
        application_id = application.id

    response = client.post(
        f'/api/license/applications/{application_id}/cancel',
        headers=auth_header
    )
    assert response.status_code == 200
    with client.application.app_context():
        assert db.session.get(LicenseApplication, application_id).status == 'cancelled'

    again = client.post(
        f'/api/license/applications/{application_id}/cancel',
        headers=auth_header
    )
    assert again.status_code == 400


def test_contract_generated_for_licensee(client, auth_header, owner_asset):
    with client.application.app_context():
        license = License(
            license_code='LIC-CONTRACT-TEST',
            asset_id=owner_asset['asset_ids'][0],
            licensor_id=owner_asset['user_id'],
            licensee_id=owner_asset['user_id'],
            license_type='personal',
            usage_scope='测试用途',
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow() + timedelta(days=30),
            status='active',
        )
        db.session.add(license)
        db.session.commit()
        license_id = license.id

    response = client.get(f'/api/license/{license_id}/contract', headers=auth_header)
    assert response.status_code == 200
    content = response.get_json()['data']['contract_content']
    assert '授权合同' in content
    assert 'LIC-CONTRACT-TEST' in content


def test_notifications_include_pending_application(client, auth_header, owner_asset):
    with client.application.app_context():
        application = LicenseApplication(
            application_code='APP-NOTIFY-TEST',
            asset_id=owner_asset['asset_ids'][0],
            applicant_id=owner_asset['user_id'],
            license_type='personal',
            usage_scope='测试用途',
            status='pending',
            adm1_status='pending',
            adm2_status='pending',
        )
        db.session.add(application)
        db.session.commit()

    response = client.get('/api/notifications', headers=auth_header)
    assert response.status_code == 200
    data = response.get_json()['data']
    assert data['count'] >= 1
    assert any(item['title'] == '授权申请待一级审批' for item in data['items'])


def test_asset_detail_returns_chain_and_watermark_fields(client, auth_header, owner_asset):
    with client.application.app_context():
        asset = db.session.get(Asset, owner_asset['asset_ids'][0])
        asset.watermark_status = 'embedded'
        asset.watermark_id = 'TS-WM-001'
        asset.watermark_embedded_at = datetime.utcnow()
        asset.chain_status = 'confirmed'
        asset.chain_tx_hash = '0x' + 'a' * 64
        asset.chain_timestamp = datetime.utcnow()
        db.session.commit()

    response = client.get(f"/api/assets/{owner_asset['asset_ids'][0]}", headers=auth_header)
    data = response.get_json()['data']
    assert data['watermark_id'] == 'TS-WM-001'
    assert data['chain_tx_hash'].startswith('0x')
    assert data['watermark_embedded_at']


def test_logs_endpoint_requires_admin(client, auth_header):
    assert client.get('/api/logs', headers=auth_header).status_code == 403


def test_admin_can_query_logs(client, admin_header):
    response = client.get('/api/logs?per_page=5', headers=admin_header)
    assert response.status_code == 200
    assert 'items' in response.get_json()['data']


def test_admin_can_reset_user_password(client, auth_header, admin_header):
    with client.application.app_context():
        user = User.query.filter_by(username='testuser').first()
        user_id = user.id

    response = client.put(
        f'/api/users/{user_id}',
        headers=admin_header,
        json={'password': 'newpass123'}
    )
    assert response.status_code == 200

    login = client.post('/api/login', json={
        'username': 'testuser',
        'password': 'newpass123'
    })
    assert login.status_code == 200


def test_admin_cannot_disable_self(client, app, admin_header):
    with app.app_context():
        admin = User.query.filter_by(username='admin').first()
        admin_id = admin.id

    response = client.put(
        f'/api/users/{admin_id}',
        headers=admin_header,
        json={'status': 'inactive'}
    )
    assert response.status_code == 400


def test_upload_persists_tags(client, auth_header):
    response = client.post(
        '/api/assets/upload',
        data={
            'file': (_jpeg_bytes(), '标签测试.jpg'),
            'title': '标签测试影像',
            'asset_type': 'image',
            'tags': '["古典建筑", "山水景观"]',
        },
        headers=auth_header,
        content_type='multipart/form-data',
    )
    assert response.status_code == 200
    asset_id = response.get_json()['data']['asset_id']

    tags = client.get(f'/api/assets/{asset_id}/tags', headers=auth_header)
    assert tags.status_code == 200
    names = {item['name'] for item in tags.get_json()['data']}
    assert names == {'古典建筑', '山水景观'}
