"""断点续传上传"""
import io
import uuid

from PIL import Image

from app.extensions import db
from app.models import Asset, AssetVersion


def _jpeg_bytes(color=(40, 90, 70)):
    buffer = io.BytesIO()
    Image.new('RGB', (48, 36), color).save(buffer, 'JPEG')
    return buffer.getvalue()


def _start_session(client, headers, payload_bytes, title='断点续传测试'):
    response = client.post('/api/assets/upload/session', headers=headers, json={
        'filename': 'resume.jpg',
        'size': len(payload_bytes),
        'asset_type': 'image',
        'title': title,
        'description': '分块上传',
        'tags': ['断点续传'],
    })
    assert response.status_code == 200, response.get_json()
    return response.get_json()['data']


def _put_chunk(client, headers, upload_id, offset, chunk):
    return client.put(
        f'/api/assets/upload/session/{upload_id}',
        data=chunk,
        headers={**headers, 'X-Upload-Offset': str(offset)},
        content_type='application/octet-stream',
    )


def test_resumable_upload_resumes_and_completes(client, app, auth_header):
    payload = _jpeg_bytes()
    session = _start_session(client, auth_header, payload)
    upload_id = session['upload_id']
    split = len(payload) // 2

    first = _put_chunk(client, auth_header, upload_id, 0, payload[:split])
    assert first.status_code == 200, first.get_json()
    assert first.get_json()['data']['received_size'] == split

    # 模拟中断后先查询状态，再从已接收位置继续
    status = client.get(
        f'/api/assets/upload/session/{upload_id}', headers=auth_header
    )
    assert status.get_json()['data']['received_size'] == split

    mismatch = _put_chunk(client, auth_header, upload_id, 0, payload[split:])
    assert mismatch.status_code == 409
    assert mismatch.get_json()['data']['received_size'] == split

    second = _put_chunk(
        client, auth_header, upload_id, split, payload[split:]
    )
    assert second.status_code == 200, second.get_json()

    completed = client.post(
        f'/api/assets/upload/session/{upload_id}/complete',
        headers=auth_header,
    )
    assert completed.status_code == 200, completed.get_json()
    asset_id = completed.get_json()['data']['asset_id']

    with app.app_context():
        asset = db.session.get(Asset, asset_id)
        assert asset.title == '断点续传测试'
        assert asset.file_hash
        assert asset.status == 'draft'
        version = AssetVersion.query.filter_by(
            asset_id=asset_id, version_no=1
        ).one()
        assert version.file_hash == asset.file_hash
        assert Asset.query.filter_by(file_hash=asset.file_hash).count() == 1

    detail = client.get(f'/api/assets/{asset_id}', headers=auth_header)
    assert detail.status_code == 200


def test_resumable_upload_rejects_incomplete_and_foreign_session(
    client, app, auth_header
):
    payload = _jpeg_bytes((10, 30, 60))
    session = _start_session(
        client, auth_header, payload, title='未完成会话'
    )
    upload_id = session['upload_id']

    incomplete = client.post(
        f'/api/assets/upload/session/{upload_id}/complete',
        headers=auth_header,
    )
    assert incomplete.status_code == 400

    client.post('/api/register', json={
        'username': 'resume_other',
        'password': 'pass1234',
        'email': 'resume_other@test.com',
    })
    login = client.post('/api/login', json={
        'username': 'resume_other', 'password': 'pass1234'
    })
    other_header = {
        'Authorization': f"Bearer {login.get_json()['data']['access_token']}"
    }
    denied = _put_chunk(client, other_header, upload_id, 0, payload)
    assert denied.status_code == 404


def test_resumable_upload_duplicate_file_is_rejected(
    client, app, auth_header
):
    payload = _jpeg_bytes((90, 40, 30))
    first = _start_session(
        client, auth_header, payload, title='第一次上传'
    )
    assert _put_chunk(
        client, auth_header, first['upload_id'], 0, payload
    ).status_code == 200
    assert client.post(
        f"/api/assets/upload/session/{first['upload_id']}/complete",
        headers=auth_header,
    ).status_code == 200

    second = _start_session(
        client, auth_header, payload, title='重复上传'
    )
    assert _put_chunk(
        client, auth_header, second['upload_id'], 0, payload
    ).status_code == 200
    duplicate = client.post(
        f"/api/assets/upload/session/{second['upload_id']}/complete",
        headers=auth_header,
    )
    assert duplicate.status_code == 400
    assert '已上传过' in duplicate.get_json()['message']
