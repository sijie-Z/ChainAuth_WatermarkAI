"""断点续传上传"""
import io
import os
from datetime import datetime, timedelta

from PIL import Image

from app.extensions import db
from app.models import Asset, AssetVersion
from app.models.extra import UploadSession


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


def test_upload_session_list_shows_only_my_active_sessions(
    client, app, auth_header
):
    payload = _jpeg_bytes((20, 60, 90))
    first = _start_session(client, auth_header, payload, title='列表会话')
    split = len(payload) // 2
    assert _put_chunk(
        client, auth_header, first['upload_id'], 0, payload[:split]
    ).status_code == 200

    listing = client.get('/api/assets/upload/sessions', headers=auth_header)
    assert listing.status_code == 200
    items = listing.get_json()['data']['items']
    assert [item['upload_id'] for item in items] == [first['upload_id']]
    assert items[0]['received_size'] == split
    assert items[0]['expected_size'] == len(payload)

    # 其他用户看不到这个会话
    client.post('/api/register', json={
        'username': 'list_other',
        'password': 'pass1234',
        'email': 'list_other@test.com',
    })
    login = client.post('/api/login', json={
        'username': 'list_other', 'password': 'pass1234'
    })
    other_header = {
        'Authorization': f"Bearer {login.get_json()['data']['access_token']}"
    }
    other_list = client.get(
        '/api/assets/upload/sessions', headers=other_header
    )
    assert other_list.get_json()['data']['items'] == []

    # 完成后不再出现在未完成列表中
    assert _put_chunk(
        client, auth_header, first['upload_id'], split, payload[split:]
    ).status_code == 200
    completed = client.post(
        f"/api/assets/upload/session/{first['upload_id']}/complete",
        headers=auth_header,
    )
    assert completed.status_code == 200
    listing = client.get('/api/assets/upload/sessions', headers=auth_header)
    assert listing.get_json()['data']['items'] == []


def test_upload_session_cancel_removes_temp_files(client, app, auth_header):
    payload = _jpeg_bytes((60, 20, 30))
    session = _start_session(
        client, auth_header, payload, title='取消会话'
    )
    upload_id = session['upload_id']
    assert _put_chunk(
        client, auth_header, upload_id, 0, payload[:10]
    ).status_code == 200

    with app.app_context():
        row = db.session.get(UploadSession, upload_id)
        temp_dir = os.path.dirname(row.temp_path)
        assert os.path.isdir(temp_dir)

    cancelled = client.delete(
        f'/api/assets/upload/session/{upload_id}', headers=auth_header
    )
    assert cancelled.status_code == 200

    with app.app_context():
        row = db.session.get(UploadSession, upload_id)
        assert row.status == 'cancelled'
        assert not os.path.exists(os.path.dirname(row.temp_path))

    # 已取消的会话不能再追加分块
    after = _put_chunk(client, auth_header, upload_id, 10, payload[10:])
    assert after.status_code == 409

    # 已完成/不存在/他人的会话取消时给出明确结果
    second_cancel = client.delete(
        f'/api/assets/upload/session/{upload_id}', headers=auth_header
    )
    assert second_cancel.status_code == 200
    missing_cancel = client.delete(
        '/api/assets/upload/session/' + '0' * 32, headers=auth_header
    )
    assert missing_cancel.status_code == 404


def test_stale_upload_session_is_purged(client, app, auth_header):
    payload = _jpeg_bytes((30, 30, 120))
    session = _start_session(
        client, auth_header, payload, title='过期会话'
    )
    upload_id = session['upload_id']
    assert _put_chunk(
        client, auth_header, upload_id, 0, payload[:5]
    ).status_code == 200

    with app.app_context():
        row = db.session.get(UploadSession, upload_id)
        row.updated_at = datetime.utcnow() - timedelta(hours=72)
        temp_dir = os.path.dirname(row.temp_path)
        db.session.commit()

    listing = client.get('/api/assets/upload/sessions', headers=auth_header)
    assert listing.status_code == 200
    assert listing.get_json()['data']['items'] == []

    with app.app_context():
        row = db.session.get(UploadSession, upload_id)
        assert row.status == 'expired'
        assert not os.path.exists(temp_dir)


def test_complete_rejects_truncated_temp_file(client, app, auth_header):
    payload = _jpeg_bytes((80, 80, 80))
    session = _start_session(
        client, auth_header, payload, title='截断文件'
    )
    upload_id = session['upload_id']
    assert _put_chunk(
        client, auth_header, upload_id, 0, payload
    ).status_code == 200

    with app.app_context():
        row = db.session.get(UploadSession, upload_id)
        with open(row.temp_path, 'r+b') as handle:
            handle.truncate(len(payload) // 2)

    completed = client.post(
        f'/api/assets/upload/session/{upload_id}/complete',
        headers=auth_header,
    )
    assert completed.status_code == 400
    assert '大小' in completed.get_json()['message']


def test_resume_session_metadata_can_be_updated(client, app, auth_header):
    payload = _jpeg_bytes((15, 75, 45))
    session = _start_session(
        client, auth_header, payload, title='旧标题'
    )
    upload_id = session['upload_id']
    assert _put_chunk(
        client, auth_header, upload_id, 0, payload
    ).status_code == 200

    updated = client.patch(
        f'/api/assets/upload/session/{upload_id}',
        headers=auth_header,
        json={
            'title': '续传后新标题',
            'description': '续传时修改的描述',
            'tags': ['续传', '元数据'],
        },
    )
    assert updated.status_code == 200, updated.get_json()
    assert updated.get_json()['data']['title'] == '续传后新标题'

    invalid = client.patch(
        f'/api/assets/upload/session/{upload_id}',
        headers=auth_header,
        json={'title': '   '},
    )
    assert invalid.status_code == 400

    completed = client.post(
        f'/api/assets/upload/session/{upload_id}/complete',
        headers=auth_header,
    )
    assert completed.status_code == 200, completed.get_json()
    asset_id = completed.get_json()['data']['asset_id']

    with app.app_context():
        asset = db.session.get(Asset, asset_id)
        assert asset.title == '续传后新标题'
        assert asset.description == '续传时修改的描述'
        names = {tag.name for tag in asset.tags}
        assert {'续传', '元数据'} <= names


def test_resumable_duplicate_does_not_leak_foreign_asset(
    client, app, auth_header
):
    payload = _jpeg_bytes((110, 20, 35))
    first = _start_session(
        client, auth_header, payload, title='他人的私有草稿'
    )
    assert _put_chunk(
        client, auth_header, first['upload_id'], 0, payload
    ).status_code == 200
    assert client.post(
        f"/api/assets/upload/session/{first['upload_id']}/complete",
        headers=auth_header,
    ).status_code == 200

    client.post('/api/register', json={
        'username': 'dup_other',
        'password': 'pass1234',
        'email': 'dup_other@test.com',
    })
    login = client.post('/api/login', json={
        'username': 'dup_other', 'password': 'pass1234'
    })
    other_header = {
        'Authorization': f"Bearer {login.get_json()['data']['access_token']}"
    }
    second = _start_session(
        client, other_header, payload, title='同文件探测'
    )
    assert _put_chunk(
        client, other_header, second['upload_id'], 0, payload
    ).status_code == 200
    duplicate = client.post(
        f"/api/assets/upload/session/{second['upload_id']}/complete",
        headers=other_header,
    )
    assert duplicate.status_code == 400
    assert duplicate.get_json()['data'] is None
