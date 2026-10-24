"""异步任务队列测试

覆盖入队去重、worker 执行、失败重试、权限与超时对账。
水印算法用 monkeypatch 替身，队列行为才是本文件的测试目标。
"""
import os
from datetime import datetime, timedelta
from io import BytesIO

import pytest
from PIL import Image

from app.extensions import db
from app.models.asset import Asset
from app.models.task import AsyncTask
from app.services import task_service
from app.services.watermark_service import WatermarkService


def make_jpeg(color=(31, 77, 64), size=(48, 36)):
    buffer = BytesIO()
    Image.new('RGB', size, color).save(buffer, 'JPEG')
    buffer.seek(0)
    return buffer


def upload_asset(client, app, tmp_path, headers, color=(10, 30, 50), title='异步任务影像'):
    app.config['UPLOAD_FOLDER'] = str(tmp_path)
    response = client.post(
        '/api/assets/upload',
        data={
            'file': (make_jpeg(color), '任务测试.jpg'),
            'title': title,
            'asset_type': 'image'
        },
        headers=headers,
        content_type='multipart/form-data'
    )
    assert response.status_code == 200, response.get_json()
    return response.get_json()['data']['asset_id']


def fake_embed_success(monkeypatch):
    def fake_embed(asset, user=None, watermark_path=None):
        asset.watermark_status = 'embedded'
        asset.watermark_id = 'WM-ASYNC-TEST'
        asset.watermark_embedded_at = datetime.utcnow()
        db.session.commit()
        return {
            'success': True,
            'message': '水印嵌入成功',
            'watermark_id': asset.watermark_id,
            'watermarked_path': '/tmp/fake-watermarked.png',
            'psnr': 40.1,
        }
    monkeypatch.setattr(WatermarkService, 'embed_watermark', fake_embed)


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


def test_async_watermark_enqueue_dedupe_and_process(client, app, tmp_path, auth_header, monkeypatch):
    asset_id = upload_asset(client, app, tmp_path, auth_header)
    fake_embed_success(monkeypatch)

    response = client.post(
        '/api/watermark/embed',
        json={'asset_id': asset_id, 'async': True},
        headers=auth_header,
    )
    assert response.status_code == 202, response.get_json()
    payload = response.get_json()['data']
    task_id = payload['task_id']
    assert payload['created'] is True

    # 队列中已有同一版本任务时复用，不重复入队
    again = client.post(
        '/api/watermark/embed',
        json={'asset_id': asset_id, 'async': True},
        headers=auth_header,
    )
    assert again.status_code == 202
    assert again.get_json()['data']['task_id'] == task_id
    assert again.get_json()['data']['created'] is False

    with app.app_context():
        asset = db.session.get(Asset, asset_id)
        assert asset.watermark_status == 'pending'
        assert AsyncTask.query.count() == 1

        processed = task_service.process_pending()
        assert processed == 1

        task = db.session.get(AsyncTask, task_id)
        assert task.status == 'succeeded'
        assert task.progress == 100
        assert task.result['watermark_id'] == 'WM-ASYNC-TEST'
        assert task.attempts == 1

        db.session.refresh(asset)
        assert asset.watermark_status == 'embedded'
        assert asset.watermark_id == 'WM-ASYNC-TEST'


def test_async_chain_creates_version_certificate(client, app, tmp_path, auth_header, monkeypatch):
    asset_id = upload_asset(client, app, tmp_path, auth_header)
    fake_embed_success(monkeypatch)

    assert client.post(
        '/api/watermark/embed',
        json={'asset_id': asset_id, 'async': True},
        headers=auth_header,
    ).status_code == 202
    with app.app_context():
        task_service.process_pending()

    response = client.post(
        '/api/blockchain/register',
        json={'asset_id': asset_id, 'async': True},
        headers=auth_header,
    )
    assert response.status_code == 202, response.get_json()
    task_id = response.get_json()['data']['task_id']

    with app.app_context():
        task_service.process_pending()
        task = db.session.get(AsyncTask, task_id)
        assert task.status == 'succeeded'
        assert task.result['certificate_id'].startswith('CERT-')

        asset = db.session.get(Asset, asset_id)
        assert asset.chain_status == 'confirmed'
        assert asset.certificate_id == task.result['certificate_id']

        from app.models.asset import AssetVersion
        from app.models.blockchain import Certificate
        version = AssetVersion.query.filter_by(
            asset_id=asset_id, version_no=1
        ).one()
        certificate = Certificate.query.filter_by(
            certificate_id=asset.certificate_id
        ).one()
        assert certificate.version_id == version.id
        assert certificate.version_no == 1


def test_failed_task_retry(client, app, tmp_path, auth_header, monkeypatch):
    asset_id = upload_asset(client, app, tmp_path, auth_header)

    def fake_embed_failure(asset, user=None, watermark_path=None):
        return {'success': False, 'message': '不支持的资产类型: image'}

    monkeypatch.setattr(WatermarkService, 'embed_watermark', fake_embed_failure)

    response = client.post(
        '/api/watermark/embed',
        json={'asset_id': asset_id, 'async': True},
        headers=auth_header,
    )
    task_id = response.get_json()['data']['task_id']

    with app.app_context():
        task_service.process_pending()
        task = db.session.get(AsyncTask, task_id)
        assert task.status == 'failed'
        assert '不支持的资产类型' in task.error_message
        asset = db.session.get(Asset, asset_id)
        assert asset.watermark_status == 'failed'

    fake_embed_success(monkeypatch)
    retry = client.post(f'/api/tasks/{task_id}/retry', headers=auth_header)
    assert retry.status_code == 200, retry.get_json()
    assert retry.get_json()['data']['status'] == 'queued'

    with app.app_context():
        task_service.process_pending()
        task = db.session.get(AsyncTask, task_id)
        assert task.status == 'succeeded'
        assert db.session.get(Asset, asset_id).watermark_status == 'embedded'


def test_task_visibility_limited_to_owner_and_admin(client, app, tmp_path, auth_header, monkeypatch):
    asset_id = upload_asset(client, app, tmp_path, auth_header)
    fake_embed_success(monkeypatch)
    response = client.post(
        '/api/watermark/embed',
        json={'asset_id': asset_id, 'async': True},
        headers=auth_header,
    )
    task_id = response.get_json()['data']['task_id']

    outsider = register_and_login(client, 'taskoutsider')
    denied = client.get(f'/api/tasks/{task_id}', headers=outsider)
    assert denied.status_code == 404

    own = client.get(f'/api/tasks/{task_id}', headers=auth_header)
    assert own.status_code == 200
    assert own.get_json()['data']['task_type'] == 'watermark_embed'


def test_reconcile_stuck_task_requeues(app):
    with app.app_context():
        task = AsyncTask(
            task_type='watermark_embed',
            status='running',
            attempts=1,
            max_attempts=3,
            started_at=datetime.utcnow() - timedelta(hours=1),
        )
        db.session.add(task)
        db.session.commit()
        task_id = task.id

        result = task_service.reconcile_stuck(timeout_minutes=10)
        assert result['requeued'] == 1

        task = db.session.get(AsyncTask, task_id)
        assert task.status == 'queued'
        assert '超时' in task.error_message


def test_task_cancel_restores_asset_state(client, app, tmp_path, auth_header, monkeypatch):
    asset_id = upload_asset(client, app, tmp_path, auth_header)
    fake_embed_success(monkeypatch)
    response = client.post(
        '/api/watermark/embed',
        json={'asset_id': asset_id, 'async': True},
        headers=auth_header,
    )
    task_id = response.get_json()['data']['task_id']

    cancelled = client.post(f'/api/tasks/{task_id}/cancel', headers=auth_header)
    assert cancelled.status_code == 200

    with app.app_context():
        task = db.session.get(AsyncTask, task_id)
        assert task.status == 'cancelled'
        assert db.session.get(Asset, asset_id).watermark_status == 'none'
