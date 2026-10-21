"""
水印接口边界测试

覆盖权限拒绝、服务层失败映射、溯源文件校验与操作日志展示。
算法调用一律 mock，避免在接口测试中做大图运算。
"""
import io
import uuid

import pytest

from app.extensions import db
from app.models.asset import Asset
from app.models.blockchain import Certificate
from app.models.log import OperationLog
from app.models.user import User
from app.services.watermark_service import WatermarkService


def register_and_login(client, username):
    client.post('/api/register', json={
        'username': username,
        'password': 'pass1234',
        'email': f'{username}@test.com',
    })
    response = client.post('/api/login', json={'username': username, 'password': 'pass1234'})
    return {'Authorization': f"Bearer {response.get_json()['data']['access_token']}"}


def set_watermark(app, asset_id, watermark_id='ZY-IMG-20260101000000-ABCD'):
    with app.app_context():
        asset = db.session.get(Asset, asset_id)
        asset.watermark_id = watermark_id
        asset.watermark_status = 'embedded'
        db.session.commit()
        return asset.asset_code


class TestEmbedEndpoint:
    def test_requires_asset_id(self, client, auth_header):
        response = client.post('/api/watermark/embed', json={}, headers=auth_header)

        assert response.status_code == 400
        assert '资产ID' in response.get_json()['message']

    def test_denies_non_owner(self, client, auth_header, sample_asset):
        other_header = register_and_login(client, 'watermarkoutsider')

        response = client.post(
            '/api/watermark/embed', json={'asset_id': sample_asset}, headers=other_header
        )

        assert response.status_code == 403
        assert response.get_json()['message'] == '无权限操作'

    def test_owner_success_response(self, client, auth_header, sample_asset, monkeypatch):
        monkeypatch.setattr(
            WatermarkService,
            'embed_watermark',
            lambda asset, user: {
                'success': True,
                'message': '水印嵌入成功',
                'watermark_id': 'ZY-IMG-20260101000000-ABCD',
                'watermarked_path': '/tmp/watermarked.png',
                'psnr': 41.5,
            },
        )

        response = client.post(
            '/api/watermark/embed', json={'asset_id': sample_asset}, headers=auth_header
        )

        assert response.status_code == 200
        data = response.get_json()['data']
        assert data['watermark_id'] == 'ZY-IMG-20260101000000-ABCD'
        assert data['psnr'] == 41.5

    @pytest.mark.parametrize('message, status', [
        ('不支持的资产类型: video', 400),
        ('水印嵌入失败: algorithm exploded', 500),
    ])
    def test_service_failure_status_mapping(self, client, auth_header, sample_asset, monkeypatch, message, status):
        monkeypatch.setattr(
            WatermarkService,
            'embed_watermark',
            lambda asset, user: {'success': False, 'message': message},
        )

        response = client.post(
            '/api/watermark/embed', json={'asset_id': sample_asset}, headers=auth_header
        )

        assert response.status_code == status
        assert response.get_json()['message'] == message


class TestExtractEndpoint:
    def test_requires_asset_id(self, client, auth_header):
        response = client.post('/api/watermark/extract', json={}, headers=auth_header)

        assert response.status_code == 400

    def test_denies_non_owner(self, client, auth_header, sample_asset):
        other_header = register_and_login(client, 'extractoutsider')

        response = client.post(
            '/api/watermark/extract', json={'asset_id': sample_asset}, headers=other_header
        )

        assert response.status_code == 403

    def test_owner_success_response(self, client, auth_header, sample_asset, monkeypatch):
        monkeypatch.setattr(
            WatermarkService,
            'extract_watermark',
            lambda asset, user: {
                'success': True,
                'message': '水印提取成功',
                'watermark_path': '/tmp/extracted.png',
                'nc_value': 0.92,
            },
        )

        response = client.post(
            '/api/watermark/extract', json={'asset_id': sample_asset}, headers=auth_header
        )

        assert response.status_code == 200
        data = response.get_json()['data']
        assert data['watermark_path'] == '/tmp/extracted.png'
        assert data['nc_value'] == 0.92

    @pytest.mark.parametrize('message, status', [
        ('不支持的资产类型: document', 400),
        ('水印提取失败: boom', 500),
    ])
    def test_service_failure_status_mapping(self, client, auth_header, sample_asset, monkeypatch, message, status):
        monkeypatch.setattr(
            WatermarkService,
            'extract_watermark',
            lambda asset, user: {'success': False, 'message': message},
        )

        response = client.post(
            '/api/watermark/extract', json={'asset_id': sample_asset}, headers=auth_header
        )

        assert response.status_code == status


class TestVerifyEndpoint:
    def test_verifies_embedded_watermark(self, client, auth_header, sample_asset, app):
        asset_code = set_watermark(app, sample_asset)

        response = client.post('/api/watermark/verify', json={
            'watermark_id': 'ZY-IMG-20260101000000-ABCD',
        })

        assert response.status_code == 200
        body = response.get_json()
        assert body['verified'] is True
        assert body['data']['asset_code'] == asset_code
        assert body['data']['watermark_id'] == 'ZY-IMG-20260101000000-ABCD'


class TestTraceEndpoint:
    def test_rejects_missing_filename(self, client):
        response = client.post(
            '/api/watermark/trace',
            data={'file': (io.BytesIO(b'data'), '')},
            content_type='multipart/form-data',
        )

        assert response.status_code == 400
        assert '未选择文件' in response.get_json()['message']

    def test_rejects_unsupported_extension(self, client):
        response = client.post(
            '/api/watermark/trace',
            data={'file': (io.BytesIO(b'data'), 'probe.txt')},
            content_type='multipart/form-data',
        )

        assert response.status_code == 400
        assert '不支持的文件类型' in response.get_json()['message']

    def test_rejects_oversized_file(self, client, app):
        app.config['TRACE_MAX_CONTENT_LENGTH'] = 10

        response = client.post(
            '/api/watermark/trace',
            data={'file': (io.BytesIO(b'x' * 2048), 'probe.png')},
            content_type='multipart/form-data',
        )

        assert response.status_code == 400
        assert '文件大小超过限制' in response.get_json()['message']

    def test_trace_finds_asset_and_certificate(self, client, app, sample_asset, monkeypatch):
        asset_code = set_watermark(app, sample_asset)
        with app.app_context():
            db.session.add(Certificate(
                certificate_id=f'CERT-{uuid.uuid4().hex[:10].upper()}',
                asset_id=sample_asset,
                tx_hash='0x' + uuid.uuid4().hex * 2,
                watermark_id='ZY-IMG-20260101000000-ABCD',
                file_hash=uuid.uuid4().hex * 2,
            ))
            db.session.commit()

        monkeypatch.setattr(
            WatermarkService,
            'trace_from_file',
            lambda path: {
                'success': True,
                'watermark_id': 'ZY-IMG-20260101000000-ABCD',
                'nc_value': 0.9,
            },
        )
        response = client.post(
            '/api/watermark/trace',
            data={'file': (io.BytesIO(b'\x89PNG\r\n\x1a\n'), 'probe.png')},
            content_type='multipart/form-data',
        )

        assert response.status_code == 200
        body = response.get_json()
        assert body['verified'] is True
        assert body['data']['asset_code'] == asset_code
        assert body['data']['certificate_id'].startswith('CERT-')
        assert body['data']['tx_hash'].startswith('0x')

    def test_trace_reports_unknown_watermark(self, client, monkeypatch):
        monkeypatch.setattr(
            WatermarkService,
            'trace_from_file',
            lambda path: {'success': True, 'watermark_id': 'ZY-IMG-UNKNOWN', 'nc_value': 0.4},
        )

        response = client.post(
            '/api/watermark/trace',
            data={'file': (io.BytesIO(b'\x89PNG\r\n\x1a\n'), 'probe.png')},
            content_type='multipart/form-data',
        )

        assert response.status_code == 200
        assert response.get_json()['verified'] is False
        assert '未找到匹配' in response.get_json()['message']

    def test_trace_reports_no_extracted_watermark(self, client, monkeypatch):
        monkeypatch.setattr(
            WatermarkService,
            'trace_from_file',
            lambda path: {'success': False, 'message': '未能提取有效水印ID', 'nc_value': 0.0},
        )

        response = client.post(
            '/api/watermark/trace',
            data={'file': (io.BytesIO(b'\x89PNG\r\n\x1a\n'), 'probe.png')},
            content_type='multipart/form-data',
        )

        assert response.status_code == 200
        assert response.get_json()['verified'] is False
        assert response.get_json()['message'] == '未能提取有效水印ID'


class TestLogsEndpoint:
    def test_forbidden_for_normal_user(self, client, auth_header):
        response = client.get('/api/watermark/logs', headers=auth_header)

        assert response.status_code == 403

    def test_admin_sees_watermark_operations(self, client, admin_header, auth_header, sample_asset, app):
        with app.app_context():
            user = User.query.filter_by(username='testuser').first()
            db.session.add(OperationLog(
                user_id=user.id,
                action='watermark_embed',
                module='watermark',
                target_type='asset',
                target_id=sample_asset,
            ))
            db.session.add(OperationLog(
                user_id=user.id,
                action='cleanup',
                module='watermark',
            ))
            db.session.commit()
            asset = db.session.get(Asset, sample_asset)

        response = client.get('/api/watermark/logs', headers=admin_header)

        assert response.status_code == 200
        entries = response.get_json()['data']
        by_operation = {entry['operation']: entry for entry in entries}
        assert by_operation['embed']['asset_code'] == asset.asset_code
        assert by_operation['embed']['operator'] == 'testuser'
        assert by_operation['cleanup']['asset_code'] is None
