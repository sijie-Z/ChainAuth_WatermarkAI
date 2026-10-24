"""资产回收站：删除、恢复与同文件重传"""
import io
from datetime import datetime, timedelta

from PIL import Image

from app.extensions import db
from app.models import Asset, License, LicenseApplication, User


def _jpeg_bytes(color=(20, 80, 60)):
    buffer = io.BytesIO()
    Image.new('RGB', (96, 72), color).save(buffer, 'JPEG')
    return buffer.getvalue()


def _upload(client, headers, title):
    return client.post(
        '/api/assets/upload',
        data={
            'file': (io.BytesIO(_jpeg_bytes()), 'lifecycle.jpg'),
            'title': title,
            'asset_type': 'image',
        },
        headers=headers,
        content_type='multipart/form-data',
    )


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


def test_deleted_asset_can_be_restored_and_reuploaded(
    client, app, auth_header
):
    first = _upload(client, auth_header, '待删除资产')
    assert first.status_code == 200, first.get_json()
    first_id = first.get_json()['data']['asset_id']

    deleted = client.delete(f'/api/assets/{first_id}', headers=auth_header)
    assert deleted.status_code == 200
    assert '回收站' in deleted.get_json()['message']

    # 已删除资产不应阻塞同文件重新上传
    second = _upload(client, auth_header, '重新上传')
    assert second.status_code == 200, second.get_json()
    second_id = second.get_json()['data']['asset_id']
    assert second_id != first_id

    restored = client.post(
        f'/api/assets/{first_id}/restore', headers=auth_header
    )
    assert restored.status_code == 200, restored.get_json()
    assert restored.get_json()['data']['status'] == 'draft'


def test_delete_revokes_licenses_and_cancels_pending_applications(
    client, app, auth_header, sample_asset
):
    with app.app_context():
        asset = db.session.get(Asset, sample_asset)
        owner = db.session.get(User, asset.owner_id)
        licensee = User(
            username='lifecycle_licensee',
            email='lifecycle_licensee@test.com',
            password_hash='x',
            role='user',
            status='active',
        )
        db.session.add(licensee)
        db.session.flush()
        db.session.add(License(
            license_code='LIC-LIFECYCLE-001',
            asset_id=asset.id,
            licensor_id=owner.id,
            licensee_id=licensee.id,
            license_type='personal',
            usage_scope='生命周期测试',
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow() + timedelta(days=10),
            status='active',
        ))
        db.session.add(LicenseApplication(
            application_code='APP-LIFECYCLE-001',
            asset_id=asset.id,
            applicant_id=licensee.id,
            license_type='personal',
            usage_scope='待审申请',
            status='pending',
            adm1_status='pending',
            adm2_status='pending',
        ))
        db.session.commit()

    response = client.delete(f'/api/assets/{sample_asset}', headers=auth_header)
    assert response.status_code == 200

    with app.app_context():
        license_row = License.query.filter_by(
            license_code='LIC-LIFECYCLE-001'
        ).one()
        application = LicenseApplication.query.filter_by(
            application_code='APP-LIFECYCLE-001'
        ).one()
        asset = db.session.get(Asset, sample_asset)
        assert license_row.status == 'revoked'
        assert application.status == 'cancelled'
        assert asset.deleted_at is not None
        assert asset.previous_status == 'published'


def test_unrelated_user_cannot_restore_deleted_asset(
    client, app, auth_header, sample_asset
):
    assert client.delete(
        f'/api/assets/{sample_asset}', headers=auth_header
    ).status_code == 200
    other_header = _login(client, 'restore_other', 'restore123')

    response = client.post(
        f'/api/assets/{sample_asset}/restore', headers=other_header
    )

    assert response.status_code == 403
