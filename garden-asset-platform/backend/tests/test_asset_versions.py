"""资产版本历史测试

覆盖：上传自动生成 v1、上传新版本、版本列表、历史版本下载、恢复旧版本、
权限与可见性。
"""
import os
from datetime import datetime
from io import BytesIO

import pytest
from PIL import Image

from app.extensions import db
from app.models.asset import Asset, AssetVersion
from app.models.blockchain import Certificate


def make_jpeg(color=(47, 107, 90), size=(80, 60)):
    buffer = BytesIO()
    Image.new('RGB', size, color).save(buffer, 'JPEG')
    buffer.seek(0)
    return buffer


@pytest.fixture
def other_header(client):
    """另一个普通用户（不是资产所有者）"""
    client.post('/api/register', json={
        'username': 'otheruser',
        'password': 'other123',
        'email': 'other@test.com'
    })
    response = client.post('/api/login', json={
        'username': 'otheruser',
        'password': 'other123'
    })
    token = response.get_json()['data']['access_token']
    return {'Authorization': f'Bearer {token}'}


def upload_asset(client, app, tmp_path, headers, color=(10, 30, 50), title='版本测试影像'):
    app.config['UPLOAD_FOLDER'] = str(tmp_path)
    response = client.post(
        '/api/assets/upload',
        data={
            'file': (make_jpeg(color), '初稿.jpg'),
            'title': title,
            'asset_type': 'image'
        },
        headers=headers,
        content_type='multipart/form-data'
    )
    assert response.status_code == 200, response.get_json()
    return response.get_json()['data']['asset_id']


def upload_version(client, headers, asset_id, color, note=None):
    data = {'file': (make_jpeg(color), '新版本.jpg')}
    if note is not None:
        data['change_note'] = note
    return client.post(
        f'/api/assets/{asset_id}/versions',
        data=data,
        headers=headers,
        content_type='multipart/form-data'
    )


def update_asset(app, asset_id, **fields):
    with app.app_context():
        asset = db.session.get(Asset, asset_id)
        for key, value in fields.items():
            setattr(asset, key, value)
        db.session.commit()


def get_version(app, asset_id, version_no):
    with app.app_context():
        version = AssetVersion.query.filter_by(
            asset_id=asset_id, version_no=version_no
        ).first()
        assert version is not None
        return {
            'id': version.id,
            'file_path': version.file_path,
            'file_hash': version.file_hash,
            'version_no': version.version_no
        }


def test_upload_creates_initial_version(client, app, tmp_path, auth_header):
    asset_id = upload_asset(client, app, tmp_path, auth_header)

    with app.app_context():
        asset = db.session.get(Asset, asset_id)
        versions = AssetVersion.query.filter_by(asset_id=asset_id).all()
        assert len(versions) == 1
        version = versions[0]
        assert version.version_no == 1
        assert version.change_note == '初始版本'
        assert version.file_hash == asset.file_hash
        assert version.file_size == asset.file_size
        assert version.thumbnail_path == asset.thumbnail_path
        assert version.created_by == asset.uploader_id
        assert os.path.isfile(version.file_path)

    response = client.get(f'/api/assets/{asset_id}/versions', headers=auth_header)
    assert response.status_code == 200
    payload = response.get_json()['data']
    assert payload['total'] == 1
    assert payload['current_version_no'] == 1
    assert payload['items'][0]['version_no'] == 1
    assert payload['items'][0]['is_current'] is True
    assert payload['items'][0]['creator_name']


def test_upload_new_version_updates_asset_and_resets_watermark(
    client, app, tmp_path, auth_header
):
    asset_id = upload_asset(client, app, tmp_path, auth_header)

    with app.app_context():
        asset = db.session.get(Asset, asset_id)
        initial_hash = asset.file_hash
        asset.chain_status = 'confirmed'
        asset.chain_tx_hash = '0x' + 'ab' * 32
        asset.chain_timestamp = datetime(2026, 1, 2, 3, 4, 5)
        asset.certificate_id = 'CERT-TEST-0001'
        asset.watermark_status = 'embedded'
        asset.watermark_id = 'WM-001'
        asset.watermarked_path = 'uploads/watermarked/wm.jpg'
        asset.watermark_embedded_at = datetime(2026, 1, 2, 3, 0, 0)
        asset.vr_value = '0.7231'
        db.session.commit()

    response = upload_version(
        client, auth_header, asset_id, color=(200, 10, 10), note='更新为高清版本'
    )
    assert response.status_code == 200, response.get_json()

    data = response.get_json()['data']
    assert data['version']['version_no'] == 2
    assert data['version']['is_current'] is True
    assert data['version']['change_note'] == '更新为高清版本'
    assert data['version']['file_hash'] != initial_hash

    with app.app_context():
        asset = db.session.get(Asset, asset_id)
        assert asset.file_hash == data['version']['file_hash']
        # 新文件替换后旧水印与旧存证都不再代表当前文件
        assert asset.watermark_status == 'none'
        assert asset.watermark_id is None
        assert asset.watermarked_path is None
        assert asset.watermark_embedded_at is None
        assert asset.vr_value is None
        # 资产主表回到未存证；历史证书与交易仍保留
        assert asset.chain_status == 'none'
        assert asset.chain_tx_hash is None
        assert asset.chain_timestamp is None
        assert asset.certificate_id is None

        version = AssetVersion.query.filter_by(asset_id=asset_id, version_no=2).first()
        assert version.file_path == asset.storage_path
        assert version.file_path.startswith(str(tmp_path))
        assert os.path.isfile(version.file_path)

        v1 = AssetVersion.query.filter_by(asset_id=asset_id, version_no=1).first()
        assert v1.file_hash == initial_hash
        assert os.path.isfile(v1.file_path)


def test_version_list_order_and_current(client, app, tmp_path, auth_header):
    asset_id = upload_asset(client, app, tmp_path, auth_header)
    assert upload_version(client, auth_header, asset_id, (90, 10, 10)).status_code == 200
    assert upload_version(client, auth_header, asset_id, (10, 90, 10)).status_code == 200

    response = client.get(f'/api/assets/{asset_id}/versions', headers=auth_header)
    assert response.status_code == 200
    payload = response.get_json()['data']

    assert payload['total'] == 3
    assert payload['current_version_no'] == 3
    assert [item['version_no'] for item in payload['items']] == [3, 2, 1]
    assert [item['is_current'] for item in payload['items']] == [True, False, False]
    assert [item['change_note'] for item in payload['items']] == [
        '上传新版本', '上传新版本', '初始版本'
    ]


def test_download_version_returns_original_content(
    client, app, tmp_path, auth_header
):
    app.config['UPLOAD_FOLDER'] = str(tmp_path)
    initial_bytes = make_jpeg(color=(5, 100, 150)).getvalue()
    response = client.post(
        '/api/assets/upload',
        data={
            'file': (BytesIO(initial_bytes), '原图.jpg'),
            'title': '版本下载测试',
            'asset_type': 'image'
        },
        headers=auth_header,
        content_type='multipart/form-data'
    )
    assert response.status_code == 200
    asset_id = response.get_json()['data']['asset_id']

    assert upload_version(client, auth_header, asset_id, (150, 5, 5)).status_code == 200

    with app.app_context():
        asset = db.session.get(Asset, asset_id)
        asset_code = asset.asset_code
    v1 = get_version(app, asset_id, 1)

    download = client.get(
        f'/api/assets/{asset_id}/versions/{v1["id"]}/download',
        headers=auth_header
    )
    assert download.status_code == 200
    assert download.get_data() == initial_bytes
    disposition = download.headers.get('Content-Disposition', '')
    assert f'{asset_code}-v1.jpg' in disposition
    download.close()

    # 版本属于其他资产时按不存在处理
    other_asset_id = upload_asset(
        client, app, tmp_path, auth_header, color=(1, 2, 3), title='另一资产'
    )
    mismatch = client.get(
        f'/api/assets/{other_asset_id}/versions/{v1["id"]}/download',
        headers=auth_header
    )
    assert mismatch.status_code == 404


def test_restore_old_version_creates_new_current(
    client, app, tmp_path, auth_header
):
    asset_id = upload_asset(client, app, tmp_path, auth_header, color=(20, 40, 60))
    v1 = get_version(app, asset_id, 1)
    v1_hash = v1['file_hash']

    assert upload_version(client, auth_header, asset_id, (60, 40, 20)).status_code == 200
    with app.app_context():
        assert db.session.get(Asset, asset_id).file_hash != v1_hash

    response = client.post(
        f'/api/assets/{asset_id}/versions/{v1["id"]}/restore',
        headers=auth_header
    )
    assert response.status_code == 200, response.get_json()
    data = response.get_json()['data']
    assert data['version']['version_no'] == 3
    assert data['version']['change_note'] == '恢复自 v1'
    assert data['version']['file_hash'] == v1_hash
    assert data['version']['is_current'] is True

    with app.app_context():
        asset = db.session.get(Asset, asset_id)
        assert asset.file_hash == v1_hash
        assert asset.watermark_status == 'none'

        versions = AssetVersion.query.filter_by(asset_id=asset_id).order_by(
            AssetVersion.version_no
        ).all()
        assert [item.version_no for item in versions] == [1, 2, 3]
        assert versions[0].file_hash == v1_hash
        assert versions[2].file_hash == v1_hash
        # 恢复是复制为新文件，不覆盖 v1 文件
        assert versions[2].file_path != versions[0].file_path
        assert os.path.isfile(versions[0].file_path)
        assert os.path.isfile(versions[2].file_path)


def test_evidence_marks_certificate_for_previous_version(
    client, app, tmp_path, auth_header
):
    asset_id = upload_asset(client, app, tmp_path, auth_header)
    with app.app_context():
        asset = db.session.get(Asset, asset_id)
        certificate = Certificate(
            certificate_id='CERT-VER-0001',
            asset_id=asset_id,
            tx_hash='0x' + 'cd' * 32,
            file_hash=asset.file_hash,
            status='valid'
        )
        db.session.add(certificate)
        asset.chain_status = 'confirmed'
        asset.chain_tx_hash = '0x' + 'cd' * 32
        asset.certificate_id = 'CERT-VER-0001'
        db.session.commit()

    assert upload_version(client, auth_header, asset_id, (70, 80, 90)).status_code == 200

    response = client.get(f'/api/assets/{asset_id}/evidence', headers=auth_header)
    assert response.status_code == 200
    items = {item['key']: item for item in response.get_json()['data']['items']}
    assert items['chain']['state'] == 'warning'
    assert '当前版本尚未存证' in items['chain']['description']
    assert items['certificate']['state'] == 'warning'
    assert '当前版本未存证' in items['certificate']['description']
    # 旧证书信息仍然展示，不被隐藏
    assert items['certificate']['fields']['证书文件指纹']


def test_version_permissions_and_visibility(
    client, app, tmp_path, auth_header, other_header, admin_header
):
    asset_id = upload_asset(client, app, tmp_path, auth_header)
    v1 = get_version(app, asset_id, 1)

    # 草稿资产：非所有者不可见
    assert client.get(
        f'/api/assets/{asset_id}/versions', headers=other_header
    ).status_code == 404
    # 非所有者不能上传新版本
    assert upload_version(
        client, other_header, asset_id, (30, 30, 30)
    ).status_code == 403
    # 非所有者不能下载历史版本
    assert client.get(
        f'/api/assets/{asset_id}/versions/{v1["id"]}/download',
        headers=other_header
    ).status_code == 403
    # 所有者可以查看草稿版本
    assert client.get(
        f'/api/assets/{asset_id}/versions', headers=auth_header
    ).status_code == 200

    # 发布后所有人可见，但仍只有所有者/管理员可下载与上传
    update_asset(app, asset_id, status='published')
    assert client.get(
        f'/api/assets/{asset_id}/versions', headers=other_header
    ).status_code == 200
    assert client.get(
        f'/api/assets/{asset_id}/versions/{v1["id"]}/download',
        headers=other_header
    ).status_code == 403
    assert upload_version(
        client, other_header, asset_id, (30, 30, 30)
    ).status_code == 403

    # 已删除：所有者不可见，管理员可见且不能上传
    update_asset(app, asset_id, status='deleted')
    assert client.get(
        f'/api/assets/{asset_id}/versions', headers=auth_header
    ).status_code == 404
    assert client.get(
        f'/api/assets/{asset_id}/versions', headers=admin_header
    ).status_code == 200
    assert upload_version(
        client, admin_header, asset_id, (30, 30, 30)
    ).status_code == 400


def test_new_version_on_published_asset_returns_to_draft(
    client, app, tmp_path, auth_header
):
    """替换已发布文件必须重新走水印、发布与审核，不能继续对外分发。"""
    asset_id = upload_asset(client, app, tmp_path, auth_header)
    update_asset(app, asset_id, status='published', publish_at=datetime.utcnow())

    response = upload_version(client, auth_header, asset_id, (90, 40, 30), '发布后修订')
    assert response.status_code == 200

    with app.app_context():
        asset = db.session.get(Asset, asset_id)
        assert asset.status == 'draft'
        assert asset.publish_at is None
        assert asset.watermark_status == 'none'
        assert asset.reject_reason is None

    # 已退回草稿后，授权用户也不能继续下载新文件
    detail = client.get(f'/api/assets/{asset_id}', headers=auth_header)
    assert detail.status_code == 200
    assert detail.get_json()['data']['status'] == 'draft'
