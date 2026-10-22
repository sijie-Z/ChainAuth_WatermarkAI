"""公开分享、证据链、下载台账、通知已读与园林档案维护测试"""
from datetime import datetime, timedelta

import pytest

from app.extensions import db
from app.models import (
    Asset, AssetShare, Certificate, DownloadRecord, Garden,
    LicenseApplication, NotificationRead, ShareDownload, User,
)


def _published_asset(app, user_id, **overrides):
    with app.app_context():
        garden = Garden(code='TST', name='测试园林', status='active')
        db.session.add(garden)
        db.session.flush()
        values = {
            'asset_code': 'TST-IMG-2026-001',
            'title': '测试园林影像',
            'asset_type': 'image',
            'file_format': 'JPG',
            'garden_id': garden.id,
            'creator_id': user_id,
            'owner_id': user_id,
            'uploader_id': user_id,
            'status': 'published',
            'file_hash': 'a' * 64,
            'watermark_status': 'embedded',
            'watermark_id': 'TST-WM-001',
            'watermark_embedded_at': datetime.utcnow(),
            'chain_status': 'confirmed',
            'chain_tx_hash': '0x' + 'b' * 64,
            'chain_timestamp': datetime.utcnow(),
            'certificate_id': 'CERT-TST-001',
            'publish_at': datetime.utcnow(),
            'view_count': 3,
            'download_count': 1,
        }
        values.update(overrides)
        asset = Asset(**values)
        db.session.add(asset)
        db.session.flush()

        certificate = Certificate(
            certificate_id='CERT-TST-001',
            asset_id=asset.id,
            tx_hash='0x' + 'b' * 64,
            file_hash='a' * 64,
            watermark_id='TST-WM-001',
            status='valid'
        )
        db.session.add(certificate)
        db.session.commit()
        return {
            'asset_id': asset.id,
            'garden_id': garden.id,
            'user_id': user_id,
        }


@pytest.fixture
def asset_fixture(app, auth_header):
    with app.app_context():
        user = User.query.filter_by(username='testuser').first()
        user_id = user.id
    return _published_asset(app, user_id)


def test_share_requires_access_code_then_returns_evidence(client, auth_header, asset_fixture):
    created = client.post(
        f"/api/assets/{asset_fixture['asset_id']}/shares",
        headers=auth_header,
        json={'expires_in_days': 7, 'access_code': 'GY2026', 'allow_download': True}
    )
    assert created.status_code == 200
    share = created.get_json()['data']
    assert share['has_access_code'] is True
    token = share['token']

    denied = client.get(f'/api/shares/{token}')
    assert denied.status_code == 401
    assert denied.get_json()['data']['requires_code'] is True

    wrong = client.get(f'/api/shares/{token}?code=0000')
    assert wrong.status_code == 401

    ok = client.get(f'/api/shares/{token}?code=GY2026')
    assert ok.status_code == 200
    data = ok.get_json()['data']
    assert data['asset']['asset_code'] == 'TST-IMG-2026-001'
    assert data['asset']['share']['allow_download'] is True
    assert data['evidence']['summary']['level'] == 'complete'
    assert [item['key'] for item in data['evidence']['items']][:4] == [
        'upload', 'watermark', 'chain', 'certificate'
    ]


def test_share_can_be_revoked(client, auth_header, asset_fixture):
    created = client.post(
        f"/api/assets/{asset_fixture['asset_id']}/shares",
        headers=auth_header,
        json={'expires_in_days': 1}
    )
    share = created.get_json()['data']
    assert client.get(f"/api/shares/{share['token']}").status_code == 200

    revoked = client.delete(f"/api/shares/{share['id']}", headers=auth_header)
    assert revoked.status_code == 200
    assert client.get(f"/api/shares/{share['token']}").status_code == 410


def test_share_rejects_unpublished_asset(client, auth_header, asset_fixture):
    with client.application.app_context():
        asset = db.session.get(Asset, asset_fixture['asset_id'])
        asset.status = 'draft'
        db.session.commit()

    response = client.post(
        f"/api/assets/{asset_fixture['asset_id']}/shares",
        headers=auth_header,
        json={}
    )
    assert response.status_code == 400


def test_evidence_endpoint_returns_ordered_items(client, auth_header, asset_fixture):
    response = client.get(
        f"/api/assets/{asset_fixture['asset_id']}/evidence",
        headers=auth_header
    )
    assert response.status_code == 200
    data = response.get_json()['data']
    assert data['summary']['verified'] is True
    assert data['summary']['file_hash'] == 'a' * 64
    states = {item['key']: item['state'] for item in data['items']}
    assert states['watermark'] == 'done'
    assert states['chain'] == 'done'
    assert states['certificate'] == 'done'
    assert states['publish'] == 'done'
    assert states['download'] == 'done'


def test_download_records_isolated_per_user_and_admin_ledger(client, auth_header, admin_header, asset_fixture):
    with client.application.app_context():
        db.session.add(DownloadRecord(
            user_id=asset_fixture['user_id'],
            asset_id=asset_fixture['asset_id'],
            ip_address='127.0.0.1'
        ))
        db.session.commit()

    mine = client.get('/api/downloads/my', headers=auth_header)
    assert mine.status_code == 200
    assert mine.get_json()['data']['total'] == 1
    assert mine.get_json()['data']['items'][0]['asset']['asset_code'] == 'TST-IMG-2026-001'

    forbidden = client.get('/api/downloads', headers=auth_header)
    assert forbidden.status_code == 403

    ledger = client.get('/api/downloads', headers=admin_header)
    assert ledger.status_code == 200
    data = ledger.get_json()['data']
    assert data['summary']['total'] == 1
    assert data['items'][0]['user']['username'] == 'testuser'


def test_notifications_can_be_marked_read(client, auth_header, asset_fixture):
    with client.application.app_context():
        db.session.add(LicenseApplication(
            application_code='APP-READ-TEST',
            asset_id=asset_fixture['asset_id'],
            applicant_id=asset_fixture['user_id'],
            license_type='personal',
            usage_scope='测试',
            status='pending',
            adm1_status='pending',
            adm2_status='pending',
        ))
        db.session.commit()

    first = client.get('/api/notifications', headers=auth_header).get_json()['data']
    item = next(item for item in first['items'] if item['key'].startswith('application-'))
    assert item['read'] is False
    assert first['unread_count'] >= 1

    marked = client.post(
        '/api/notifications/read',
        headers=auth_header,
        json={'keys': [item['key']]}
    )
    assert marked.status_code == 200

    second = client.get('/api/notifications', headers=auth_header).get_json()['data']
    assert next(i for i in second['items'] if i['key'] == item['key'])['read'] is True
    assert second['unread_count'] < first['unread_count']

    with client.application.app_context():
        assert NotificationRead.query.filter_by(
            notification_key=item['key']
        ).count() == 1


def test_admin_can_manage_gardens(client, admin_header):
    created = client.post('/api/gardens', headers=admin_header, json={
        'code': 'csy',
        'name': '沧浪亭',
        'area_size': 1.08,
        'build_year': 1044,
        'heritage_level': '世界文化遗产'
    })
    assert created.status_code == 200
    garden = created.get_json()['data']
    assert garden['code'] == 'CSY'
    garden_id = garden['id']

    updated = client.put(f'/api/gardens/{garden_id}', headers=admin_header, json={
        'description': '苏州现存最古老的园林'
    })
    assert updated.status_code == 200
    assert updated.get_json()['data']['description'] == '苏州现存最古老的园林'

    listing = client.get('/api/gardens?status=all', headers=admin_header)
    assert listing.status_code == 200
    assert any(item['id'] == garden_id for item in listing.get_json()['data'])

    deleted = client.delete(f'/api/gardens/{garden_id}', headers=admin_header)
    assert deleted.status_code == 200


def test_garden_delete_blocked_when_assets_exist(client, admin_header, asset_fixture):
    response = client.delete(
        f"/api/gardens/{asset_fixture['garden_id']}",
        headers=admin_header
    )
    assert response.status_code == 400
    assert '仍有' in response.get_json()['message']


def test_share_cannot_be_created_by_stranger(client, app, asset_fixture):
    client.post('/api/register', json={
        'username': 'stranger',
        'password': 'test123',
        'email': 'stranger@test.com'
    })
    login = client.post('/api/login', json={
        'username': 'stranger',
        'password': 'test123'
    })
    token = login.get_json()['data']['access_token']

    response = client.post(
        f"/api/assets/{asset_fixture['asset_id']}/shares",
        headers={'Authorization': f'Bearer {token}'},
        json={}
    )
    assert response.status_code == 403


def test_expired_share_is_gone(client, auth_header, asset_fixture):
    created = client.post(
        f"/api/assets/{asset_fixture['asset_id']}/shares",
        headers=auth_header,
        json={'expires_in_days': 1}
    )
    share = created.get_json()['data']

    with client.application.app_context():
        row = AssetShare.query.filter_by(token=share['token']).first()
        row.expires_at = datetime.utcnow() - timedelta(minutes=1)
        db.session.commit()

    assert client.get(f"/api/shares/{share['token']}").status_code == 410


def test_share_download_writes_ledger(client, app, auth_header, admin_header,
                                     asset_fixture, tmp_path):
    file_path = tmp_path / 'share-download.jpg'
    file_path.write_bytes(b'share-download-content')
    with app.app_context():
        asset = db.session.get(Asset, asset_fixture['asset_id'])
        asset.storage_path = str(file_path)
        db.session.commit()

    created = client.post(
        f"/api/assets/{asset_fixture['asset_id']}/shares",
        headers=auth_header,
        json={'expires_in_days': 1, 'allow_download': True, 'max_downloads': 3}
    )
    assert created.status_code == 200
    token = created.get_json()['data']['token']

    downloaded = client.get(f'/api/shares/{token}/download')
    assert downloaded.status_code == 200
    assert downloaded.data == b'share-download-content'

    with app.app_context():
        assert ShareDownload.query.filter_by(
            asset_id=asset_fixture['asset_id']
        ).count() == 1

    ledger = client.get('/api/downloads', headers=admin_header)
    assert ledger.status_code == 200
    data = ledger.get_json()['data']
    share_items = [item for item in data['items'] if item['channel'] == 'share']
    assert share_items
    assert share_items[0]['user'] is None
    assert data['summary']['share_total'] >= 1
