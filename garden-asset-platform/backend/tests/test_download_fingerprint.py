"""下载指纹副本测试"""
import uuid
from datetime import datetime, timedelta
from io import BytesIO

from PIL import Image

from app.extensions import db
from app.models import (
    Asset, AssetVersion, DownloadFingerprint, DownloadRecord, License, User
)


def make_jpeg(color=(30, 90, 70), size=(96, 72)):
    buffer = BytesIO()
    Image.new('RGB', size, color).save(buffer, 'JPEG')
    buffer.seek(0)
    return buffer


def register_and_login(client, username):
    client.post('/api/register', json={
        'username': username,
        'password': 'pass1234',
        'email': f'{username}@test.com',
    })
    response = client.post('/api/login', json={
        'username': username, 'password': 'pass1234'
    })
    return {'Authorization': f"Bearer {response.get_json()['data']['access_token']}"}


def setup_licensed_asset(client, app, tmp_path, owner_header):
    app.config['UPLOAD_FOLDER'] = str(tmp_path)
    response = client.post(
        '/api/assets/upload',
        data={
            'file': (make_jpeg(), 'fingerprint.jpg'),
            'title': '下载指纹测试影像',
            'asset_type': 'image'
        },
        headers=owner_header,
        content_type='multipart/form-data'
    )
    assert response.status_code == 200, response.get_json()
    asset_id = response.get_json()['data']['asset_id']
    licensee_header = register_and_login(client, 'fingerprint_user')
    with app.app_context():
        asset = db.session.get(Asset, asset_id)
        asset.status = 'published'
        version = AssetVersion.query.filter_by(
            asset_id=asset_id, version_no=1
        ).one()
        licensee = User.query.filter_by(username='fingerprint_user').one()
        license_row = License(
            license_code='LIC-FINGERPRINT-001',
            asset_id=asset_id,
            version_id=version.id,
            version_no=1,
            licensor_id=asset.uploader_id,
            licensee_id=licensee.id,
            license_type='academic',
            usage_scope='教学使用',
            territory='中国大陆',
            start_time=datetime.utcnow() - timedelta(days=1),
            end_time=datetime.utcnow() + timedelta(days=30),
            status='active',
        )
        db.session.add(license_row)
        db.session.commit()
        license_id = license_row.id
        licensee_id = licensee.id
    return asset_id, license_id, licensee_id, licensee_header


def test_licensed_download_creates_and_reuses_fingerprint(
    client, app, tmp_path, auth_header, admin_header
):
    asset_id, license_id, licensee_id, licensee_header = setup_licensed_asset(
        client, app, tmp_path, auth_header
    )

    response = client.get(
        f'/api/assets/{asset_id}/download?territory=中国大陆', headers=licensee_header
    )
    assert response.status_code == 200, response.get_json()
    code = response.headers.get('X-Download-Fingerprint')
    assert code and code.startswith('FP-')
    fingerprint_path = tmp_path / 'output.jpg'
    fingerprint_path.write_bytes(response.data)
    with Image.open(fingerprint_path) as image:
        assert image.size[1] > 72

    with app.app_context():
        fingerprint = DownloadFingerprint.query.filter_by(
            license_id=license_id, asset_id=asset_id
        ).one()
        assert fingerprint.fingerprint_code == code
        assert fingerprint.user_id == licensee_id
        record = DownloadRecord.query.filter_by(
            license_id=license_id, status='success'
        ).one()
        assert record.fingerprint_id == fingerprint.id
        license_row = db.session.get(License, license_id)
        assert license_row.download_count == 1

    # 同一授权再次下载复用同一指纹副本
    again = client.get(
        f'/api/assets/{asset_id}/download?territory=中国大陆', headers=licensee_header
    )
    assert again.status_code == 200
    assert again.headers.get('X-Download-Fingerprint') == code
    with app.app_context():
        assert DownloadFingerprint.query.count() == 1
        assert DownloadRecord.query.filter_by(license_id=license_id).count() == 2

    # 所有者下载不带授权指纹
    owner = client.get(
        f'/api/assets/{asset_id}/download', headers=auth_header
    )
    assert owner.status_code == 200
    assert owner.headers.get('X-Download-Fingerprint') is None

    # 管理员台账能看到指纹码
    ledger = client.get('/api/downloads', headers=admin_header)
    assert ledger.status_code == 200
    items = ledger.get_json()['data']['items']
    entry = next(item for item in items if item['license'])
    assert entry['fingerprint']['code'] == code


def test_download_ticket_streams_with_fingerprint(
    client, app, tmp_path, auth_header
):
    asset_id, license_id, licensee_id, licensee_header = setup_licensed_asset(
        client, app, tmp_path, auth_header
    )

    issued = client.post(
        f'/api/assets/{asset_id}/download-ticket',
        json={'territory': '中国大陆'},
        headers=licensee_header,
    )
    assert issued.status_code == 200, issued.get_json()
    data = issued.get_json()['data']
    assert data['ticket']
    assert data['expires_in'] > 0
    code = data['fingerprint_code']
    assert code and code.startswith('FP-')

    # 票据方式无需 Authorization 头，浏览器可直接流式下载
    download = client.get(
        f"/api/assets/{asset_id}/download?ticket={data['ticket']}"
    )
    assert download.status_code == 200, download.get_json()
    assert download.headers.get('X-Download-Fingerprint') == code
    assert 'attachment' in download.headers.get('Content-Disposition', '')

    with app.app_context():
        fingerprint = DownloadFingerprint.query.filter_by(
            license_id=license_id, asset_id=asset_id
        ).one()
        assert fingerprint.fingerprint_code == code
        record = DownloadRecord.query.filter_by(
            license_id=license_id, status='success'
        ).one()
        assert record.fingerprint_id == fingerprint.id
        assert db.session.get(License, license_id).download_count == 1


def test_download_ticket_rejects_tampering_and_wrong_asset(
    client, app, tmp_path, auth_header
):
    asset_id, _license_id, _licensee_id, _licensee_header = setup_licensed_asset(
        client, app, tmp_path, auth_header
    )

    issued = client.post(
        f'/api/assets/{asset_id}/download-ticket',
        json={},
        headers=auth_header,
    )
    ticket = issued.get_json()['data']['ticket']

    tampered = client.get(
        f'/api/assets/{asset_id}/download?ticket={ticket}x'
    )
    assert tampered.status_code == 401

    wrong_asset = client.get(
        f'/api/assets/{uuid.uuid4()}/download?ticket={ticket}'
    )
    assert wrong_asset.status_code == 401

    missing = client.get(
        f'/api/assets/{asset_id}/download?ticket=not-a-ticket'
    )
    assert missing.status_code == 401


def test_download_ticket_denies_user_without_license(
    client, app, tmp_path, auth_header
):
    asset_id, _license_id, _licensee_id, _licensee_header = setup_licensed_asset(
        client, app, tmp_path, auth_header
    )
    outsider_header = register_and_login(client, 'ticket_outsider')

    issued = client.post(
        f'/api/assets/{asset_id}/download-ticket',
        json={'territory': '中国大陆'},
        headers=outsider_header,
    )
    assert issued.status_code == 403
    assert '授权' in issued.get_json()['message']

    with app.app_context():
        outsider = User.query.filter_by(username='ticket_outsider').one()
        denied = DownloadRecord.query.filter_by(
            user_id=outsider.id, status='denied'
        ).one()
        assert '授权' in denied.denial_reason

    invalid = client.post(
        f'/api/assets/{asset_id}/download-ticket',
        json={'purpose': 'not-a-purpose'},
        headers=outsider_header,
    )
    assert invalid.status_code == 400
