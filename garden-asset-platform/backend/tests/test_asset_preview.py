"""资产在线预览权限测试"""
import uuid
from datetime import datetime, timedelta
from io import BytesIO

from PIL import Image

from app.extensions import db
from app.models import Asset, License, User


def make_jpeg(color=(40, 80, 60), size=(64, 48)):
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


def upload(client, app, tmp_path, headers, published=True):
    app.config['UPLOAD_FOLDER'] = str(tmp_path)
    response = client.post(
        '/api/assets/upload',
        data={
            'file': (make_jpeg(), 'preview.jpg'),
            'title': '预览测试影像',
            'asset_type': 'image'
        },
        headers=headers,
        content_type='multipart/form-data'
    )
    assert response.status_code == 200, response.get_json()
    asset_id = response.get_json()['data']['asset_id']
    if published:
        with app.app_context():
            asset = db.session.get(Asset, asset_id)
            asset.status = 'published'
            db.session.commit()
    return asset_id


def test_preview_requires_license_for_published_asset(
    client, app, tmp_path, auth_header, admin_header
):
    asset_id = upload(client, app, tmp_path, auth_header)
    stranger = register_and_login(client, 'preview_stranger')
    denied = client.get(
        f'/api/assets/{asset_id}/preview', headers=stranger
    )
    assert denied.status_code == 403

    licensed = register_and_login(client, 'preview_licensed')
    with app.app_context():
        asset = db.session.get(Asset, asset_id)
        user = User.query.filter_by(username='preview_licensed').one()
        db.session.add(License(
            license_code='LIC-PREVIEW-001',
            asset_id=asset_id,
            licensor_id=asset.uploader_id,
            licensee_id=user.id,
            license_type='academic',
            usage_scope='预览',
            start_time=datetime.utcnow() - timedelta(days=1),
            end_time=datetime.utcnow() + timedelta(days=30),
            status='active',
        ))
        db.session.commit()

    allowed = client.get(
        f'/api/assets/{asset_id}/preview', headers=licensed
    )
    assert allowed.status_code == 200
    assert allowed.mimetype == 'image/jpeg'
    assert allowed.data
    with app.app_context():
        assert db.session.get(Asset, asset_id).download_count == 0

    owner = client.get(
        f'/api/assets/{asset_id}/preview', headers=auth_header
    )
    assert owner.status_code == 200


def test_preview_draft_limited_to_owner_and_admin(
    client, app, tmp_path, auth_header, admin_header
):
    asset_id = upload(client, app, tmp_path, auth_header, published=False)
    outsider = register_and_login(client, 'preview_outsider')
    assert client.get(
        f'/api/assets/{asset_id}/preview', headers=outsider
    ).status_code == 403
    assert client.get(
        f'/api/assets/{asset_id}/preview', headers=auth_header
    ).status_code == 200
    assert client.get(
        f'/api/assets/{asset_id}/preview', headers=admin_header
    ).status_code == 200


def test_preview_ticket_allows_direct_reads_and_rejects_tampering(
    client, app, tmp_path, auth_header
):
    asset_id = upload(client, app, tmp_path, auth_header)
    licensed = register_and_login(client, 'preview_ticket_user')
    with app.app_context():
        asset = db.session.get(Asset, asset_id)
        user = User.query.filter_by(username='preview_ticket_user').one()
        db.session.add(License(
            license_code='LIC-PREVIEW-TICKET-001',
            asset_id=asset_id,
            licensor_id=asset.uploader_id,
            licensee_id=user.id,
            license_type='academic',
            usage_scope='预览',
            start_time=datetime.utcnow() - timedelta(days=1),
            end_time=datetime.utcnow() + timedelta(days=30),
            status='active',
        ))
        db.session.commit()

    issued = client.post(
        f'/api/assets/{asset_id}/preview-ticket', headers=licensed
    )
    assert issued.status_code == 200, issued.get_json()
    ticket = issued.get_json()['data']['ticket']

    direct = client.get(
        f'/api/assets/{asset_id}/preview?ticket={ticket}'
    )
    assert direct.status_code == 200
    assert direct.mimetype == 'image/jpeg'
    assert direct.data
    assert 'bytes' in direct.headers.get('Accept-Ranges', '')

    with app.app_context():
        assert db.session.get(Asset, asset_id).download_count == 0

    tampered = client.get(
        f'/api/assets/{asset_id}/preview?ticket={ticket}x'
    )
    assert tampered.status_code == 401
    wrong_asset = client.get(
        f'/api/assets/{uuid.uuid4()}/preview?ticket={ticket}'
    )
    assert wrong_asset.status_code == 401

    outsider = register_and_login(client, 'preview_ticket_outsider')
    denied = client.post(
        f'/api/assets/{asset_id}/preview-ticket', headers=outsider
    )
    assert denied.status_code == 403
