"""
端到端与回归测试：
- 上传资产自动写入 uploader_id
- 水印 ID 可提取、NC 达标、彩色图不丢色
- 授权申请对 adm1/adm2 可见并能完成双审批
"""
import io

import pytest
from PIL import Image

from app.extensions import db
from app.models.asset import Asset
from app.models.license import License, LicenseApplication
from app.models.user import User
from algorithm.raster.embed import embed_raster_watermark_color
from algorithm.raster.extract import extract_raster_watermark


def make_png(size=64, seed=0):
    image = Image.new('RGB', (size, size), (30 + seed, 80, 60))
    buffer = io.BytesIO()
    image.save(buffer, format='PNG')
    buffer.seek(0)
    return buffer


def test_upload_sets_uploader_id(client, auth_header):
    response = client.post(
        '/api/assets/upload',
        headers=auth_header,
        data={
            'file': (make_png(), 'e2e.png'),
            'title': '回归测试资产',
            'asset_type': 'image',
        },
        content_type='multipart/form-data',
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload['code'] == 200
    asset_id = payload['data']['asset_id']

    with client.application.app_context():
        asset = db.session.get(Asset, asset_id)
        assert asset is not None
        assert asset.uploader_id is not None
        assert asset.uploader_id == asset.creator_id


def test_watermark_roundtrip_returns_id_and_keeps_color(tmp_path):
    source_path = tmp_path / 'source.png'
    image = Image.new('RGB', (256, 256), (40, 90, 70))
    for x in range(256):
        for y in range(256):
            image.putpixel((x, y), (30 + x // 2, 80 + y // 2, 60))
    image.save(source_path)

    embed_result = embed_raster_watermark_color(
        image_path=str(source_path),
        watermark_path='data/watermark/default.png',
        output_folder=str(tmp_path / 'embedded'),
        method='dct',
        garden_code='TST',
    )

    assert embed_result['watermark_id'].startswith('TST-IMG-')
    assert embed_result['psnr'] > 30

    with Image.open(embed_result['watermarked_path']) as watermarked:
        assert watermarked.mode == 'RGB'

    extract_result = extract_raster_watermark(
        watermarked_path=embed_result['watermarked_path'],
        original_watermark_path='data/watermark/default.png',
        output_folder=str(tmp_path / 'extracted'),
    )

    assert extract_result['watermark_id'] == embed_result['watermark_id']
    assert extract_result['nc_value'] >= 0.9


def test_dual_approval_flow_and_license_creation(client, auth_header, adm1_header, adm2_header, app):
    with app.app_context():
        applicant = User.query.filter_by(username='testuser').first()
        assert applicant is not None

        # 模拟历史数据：uploader_id 为空，只有 owner/creator
        asset = Asset(
            asset_code='TST-IMG-20261020000000-0001',
            title='双审批回归资产',
            asset_type='image',
            file_format='PNG',
            file_hash='0' * 64,
            storage_path='tests/fixtures/not-needed.png',
            creator_id=applicant.id,
            owner_id=applicant.id,
            uploader_id=None,
            status='published',
        )
        db.session.add(asset)
        db.session.commit()
        asset_id = asset.id

    response = client.post(
        '/api/license/apply',
        headers=auth_header,
        json={'asset_id': asset_id, 'license_type': 'personal', 'purpose': '回归测试'},
    )
    assert response.status_code == 200
    application_id = response.get_json()['data']['id']

    # adm1 待审批列表可以看到未分配的申请
    response = client.get('/api/license/pending', headers=adm1_header)
    assert response.status_code == 200
    pending_ids = [item['id'] for item in response.get_json()['data']]
    assert application_id in pending_ids

    response = client.post(
        f'/api/license/approve/{application_id}',
        headers=adm1_header,
        json={'action': 'approve', 'comment': 'adm1 ok'},
    )
    assert response.status_code == 200

    # adm2 待审批列表可以看到一级已通过的申请
    response = client.get('/api/license/pending', headers=adm2_header)
    assert response.status_code == 200
    pending_ids = [item['id'] for item in response.get_json()['data']]
    assert application_id in pending_ids

    response = client.post(
        f'/api/license/approve/{application_id}',
        headers=adm2_header,
        json={'action': 'approve', 'comment': 'adm2 ok'},
    )
    assert response.status_code == 200

    with app.app_context():
        application = db.session.get(LicenseApplication, application_id)
        assert application.status == 'approved'

        license_record = License.query.filter_by(
            asset_id=asset_id, licensee_id=application.applicant_id
        ).first()
        assert license_record is not None
        assert license_record.status == 'active'
        # 历史数据 uploader_id 为空时，回退到 owner/creator
        assert license_record.licensor_id == application.asset.owner_id

    response = client.get('/api/license/my', headers=auth_header)
    assert response.status_code == 200
    items = response.get_json()['data']['items']
    assert any(item['asset_id'] == asset_id and item['status'] == 'active' for item in items)
