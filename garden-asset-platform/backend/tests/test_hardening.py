"""
安全与可见性回归测试：
- 中文文件名上传不再 500
- 普通用户不能列出/读取他人草稿
- 授权审批必须角色正确、action 合法
- 登出后 access token 立即失效；禁用用户的旧 token 被拒绝
- 我的申请接口返回审批中的申请
- 16 位图像水印可嵌入并还原 ID
"""
import io
import uuid
from datetime import datetime, timedelta

import numpy as np
from PIL import Image

from app.extensions import db
from app.models.asset import Asset
from app.models.license import License, LicenseApplication
from app.models.user import User


def make_png(size=64, color=(40, 90, 70)):
    image = Image.new('RGB', (size, size), color)
    buffer = io.BytesIO()
    image.save(buffer, format='PNG')
    buffer.seek(0)
    return buffer


def register_and_login(client, username):
    client.post('/api/register', json={
        'username': username,
        'password': 'pass1234',
        'email': f'{username}@test.com',
    })
    response = client.post('/api/login', json={
        'username': username,
        'password': 'pass1234',
    })
    token = response.get_json()['data']['access_token']
    return {'Authorization': f'Bearer {token}'}


def create_asset(app, owner_id, status='draft'):
    with app.app_context():
        asset = Asset(
            asset_code=f'TST-IMG-{uuid.uuid4().hex[:8]}',
            title=f'测试资产-{uuid.uuid4().hex[:6]}',
            asset_type='image',
            file_format='PNG',
            file_hash=uuid.uuid4().hex,
            storage_path='tests/fixtures/not-needed.png',
            creator_id=owner_id,
            uploader_id=owner_id,
            owner_id=owner_id,
            status=status,
        )
        db.session.add(asset)
        db.session.commit()
        return asset.id


def test_upload_accepts_chinese_filename(client, auth_header):
    response = client.post(
        '/api/assets/upload',
        headers=auth_header,
        data={
            'file': (make_png(), '拙政园荷花.png'),
            'title': '中文文件名资产',
            'asset_type': 'image',
        },
        content_type='multipart/form-data',
    )
    assert response.status_code == 200, response.get_json()
    assert response.get_json()['data']['asset_id']


def test_non_admin_cannot_list_or_read_drafts(client, auth_header, admin_header, app):
    with app.app_context():
        owner = User.query.filter_by(username='testuser').first()
        draft_id = create_asset(app, owner.id, status='draft')

    # 普通用户不能按 draft 状态列全站草稿
    response = client.get('/api/assets?status=draft', headers=auth_header)
    assert response.status_code == 403

    # 管理员可以按 draft 筛选
    response = client.get('/api/assets?status=draft', headers=admin_header)
    assert response.status_code == 200
    assert any(item['id'] == draft_id for item in response.get_json()['data']['items'])

    # 所有者可以在 /assets/my 看到自己的草稿
    response = client.get('/api/assets/my?status=draft', headers=auth_header)
    assert response.status_code == 200
    assert any(item['id'] == draft_id for item in response.get_json()['data']['items'])

    # 其他用户读取详情应 404（不泄露存在性）
    other_header = register_and_login(client, 'otheruser')
    response = client.get(f'/api/assets/{draft_id}', headers=other_header)
    assert response.status_code == 404


def test_license_approve_requires_role_and_valid_action(client, auth_header, adm1_header, sample_asset):
    response = client.post('/api/license/apply', headers=auth_header, json={
        'asset_id': sample_asset,
        'license_type': 'personal',
        'purpose': '回归测试',
    })
    assert response.status_code == 200, response.get_json()
    application_id = response.get_json()['data']['id']

    # 普通用户不能审批
    response = client.post(
        f'/api/license/approve/{application_id}',
        headers=auth_header,
        json={'action': 'approve'},
    )
    assert response.status_code == 403

    # 非法 action 不会被当成拒绝
    response = client.post(
        f'/api/license/approve/{application_id}',
        headers=adm1_header,
        json={'action': 'yes'},
    )
    assert response.status_code == 400

    with client.application.app_context():
        application = db.session.get(LicenseApplication, application_id)
        assert application.status == 'pending'

    # 合法的一级审批
    response = client.post(
        f'/api/license/approve/{application_id}',
        headers=adm1_header,
        json={'action': 'approve', 'comment': 'ok'},
    )
    assert response.status_code == 200


def test_logout_revokes_access_token(client, auth_header):
    assert client.get('/api/user/current', headers=auth_header).status_code == 200
    assert client.post('/api/logout', headers=auth_header).status_code == 200
    assert client.get('/api/user/current', headers=auth_header).status_code == 401


def test_disabled_user_token_is_rejected(client, auth_header, admin_header):
    me = client.get('/api/user/current', headers=auth_header).get_json()['data']
    response = client.put(
        f"/api/users/{me['id']}",
        headers=admin_header,
        json={'status': 'inactive'},
    )
    assert response.status_code == 200
    assert client.get('/api/user/current', headers=auth_header).status_code == 401


def test_my_applications_lists_pending_application(client, auth_header, sample_asset):
    response = client.post('/api/license/apply', headers=auth_header, json={
        'asset_id': sample_asset,
        'license_type': 'academic',
        'purpose': '论文研究',
    })
    assert response.status_code == 200
    application_id = response.get_json()['data']['id']

    response = client.get('/api/license/my-applications', headers=auth_header)
    assert response.status_code == 200
    items = response.get_json()['data']['items']
    assert any(item['id'] == application_id and item['status'] == 'pending' for item in items)


def test_expired_license_cannot_download(client, auth_header, app):
    with app.app_context():
        owner = User.query.filter_by(username='testuser').first()
        asset_id = create_asset(app, owner.id, status='published')

    other_header = register_and_login(client, 'expireduser')
    with app.app_context():
        licensee = User.query.filter_by(username='expireduser').first()
        license_record = License(
            license_code=f'LIC-{uuid.uuid4().hex[:12].upper()}',
            asset_id=asset_id,
            licensor_id=owner.id,
            licensee_id=licensee.id,
            license_type='personal',
            usage_scope='test',
            start_time=datetime.utcnow() - timedelta(days=10),
            end_time=datetime.utcnow() - timedelta(days=1),
            status='active',
        )
        db.session.add(license_record)
        db.session.commit()

    response = client.get(f'/api/assets/{asset_id}/download', headers=other_header)
    assert response.status_code == 403


def test_16bit_image_watermark_roundtrip(tmp_path):
    from algorithm.raster.embed import embed_raster_watermark
    from algorithm.raster.extract import extract_raster_watermark

    gradient = np.linspace(0, 65535, 256 * 256, dtype=np.uint16).reshape(256, 256)
    source_path = tmp_path / 'gray16.png'
    Image.fromarray(gradient).save(source_path)

    embed_result = embed_raster_watermark(
        image_path=str(source_path),
        watermark_path='data/watermark/default.png',
        output_folder=str(tmp_path / 'embedded'),
        method='dct',
        garden_code='TST',
    )
    assert embed_result['watermark_id'].startswith('TST-IMG-')

    extract_result = extract_raster_watermark(
        watermarked_path=embed_result['watermarked_path'],
        original_watermark_path='data/watermark/default.png',
        output_folder=str(tmp_path / 'extracted'),
    )
    assert extract_result['watermark_id'] == embed_result['watermark_id']
