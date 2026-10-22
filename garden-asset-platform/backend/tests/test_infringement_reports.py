"""侵权线索提交与后台研判测试"""
import os
from io import BytesIO

from PIL import Image

from app.extensions import db
from app.models import (
    Asset, InfringementReport, NotificationEvent, User
)
from app.services.watermark_service import WatermarkService


def make_jpeg(color=(40, 80, 60), size=(64, 48)):
    buffer = BytesIO()
    Image.new('RGB', size, color).save(buffer, 'JPEG')
    buffer.seek(0)
    return buffer


def upload_published_asset(client, app, tmp_path, headers, watermark_id='WM-REPORT-1'):
    app.config['UPLOAD_FOLDER'] = str(tmp_path)
    response = client.post(
        '/api/assets/upload',
        data={
            'file': (make_jpeg(), 'report-asset.jpg'),
            'title': '侵权线索测试影像',
            'asset_type': 'image'
        },
        headers=headers,
        content_type='multipart/form-data'
    )
    assert response.status_code == 200, response.get_json()
    asset_id = response.get_json()['data']['asset_id']
    with app.app_context():
        asset = db.session.get(Asset, asset_id)
        asset.status = 'published'
        asset.watermark_status = 'embedded'
        asset.watermark_id = watermark_id
        db.session.commit()
    return asset_id


def submit_report(client, asset_id, headers=None, **overrides):
    data = {
        'asset_id': asset_id,
        'source_url': 'https://example.com/unauthorized',
        'description': '发现未授权转载',
        'contact': 'reporter@example.com',
    }
    data.update(overrides)
    return client.post(
        '/api/infringements/report',
        data=data,
        headers=headers,
        content_type='multipart/form-data',
    )


def test_anonymous_report_matches_asset_and_admin_can_review(
    client, app, tmp_path, auth_header, admin_header, monkeypatch
):
    asset_id = upload_published_asset(client, app, tmp_path, auth_header)
    monkeypatch.setattr(
        WatermarkService,
        'trace_from_file',
        lambda path: {
            'success': True,
            'watermark_id': 'WM-REPORT-1',
            'nc_value': 0.91,
        },
    )

    response = client.post(
        '/api/infringements/report',
        data={
            'file': (make_jpeg((10, 20, 30)), 'suspect.jpg'),
            'source_url': 'https://example.com/unauthorized',
            'description': '网页上使用了同款园林照片',
            'contact': 'anonymous@example.com',
        },
        content_type='multipart/form-data',
    )
    assert response.status_code == 200, response.get_json()
    payload = response.get_json()['data']
    assert payload['trace_verified'] is True
    assert payload['asset']['id'] == asset_id
    report_code = payload['report_code']

    with app.app_context():
        report = InfringementReport.query.filter_by(report_code=report_code).one()
        assert report.asset_id == asset_id
        assert report.status == 'pending'
        assert report.suspect_file_path and os.path.isfile(report.suspect_file_path)
        assert report.suspect_file_hash
        assert report.watermark_id == 'WM-REPORT-1'
        owner = User.query.filter_by(username='testuser').one()
        assert NotificationEvent.query.filter_by(
            user_id=owner.id, event_type='infringement_reported'
        ).count() == 1
        report_id = report.id

    listing = client.get('/api/infringements', headers=admin_header)
    assert listing.status_code == 200
    data = listing.get_json()['data']
    assert data['total'] == 1
    assert data['counts']['pending'] == 1
    item = data['items'][0]
    assert item['contact'] == 'anonymous@example.com'
    assert item['asset_code']

    detail = client.get(f'/api/infringements/{report_id}', headers=admin_header)
    assert detail.status_code == 200
    assert detail.get_json()['data']['can_review'] is True

    file_response = client.get(
        f'/api/infringements/{report_id}/file', headers=admin_header
    )
    assert file_response.status_code == 200
    assert file_response.data

    started = client.post(
        f'/api/infringements/{report_id}/review',
        json={'action': 'start', 'comment': '开始核实'},
        headers=admin_header,
    )
    assert started.status_code == 200
    assert started.get_json()['data']['status'] == 'reviewing'

    confirmed = client.post(
        f'/api/infringements/{report_id}/review',
        json={'action': 'confirm', 'comment': '确认未授权使用'},
        headers=admin_header,
    )
    assert confirmed.status_code == 200, confirmed.get_json()
    assert confirmed.get_json()['data']['status'] == 'confirmed'

    with app.app_context():
        owner = User.query.filter_by(username='testuser').one()
        assert NotificationEvent.query.filter_by(
            user_id=owner.id, event_type='infringement_confirmed'
        ).count() == 1

    final = client.post(
        f'/api/infringements/{report_id}/review',
        json={'action': 'reject'},
        headers=admin_header,
    )
    assert final.status_code == 400


def test_authenticated_report_appears_in_my_list(
    client, app, tmp_path, auth_header
):
    asset_id = upload_published_asset(
        client, app, tmp_path, auth_header, watermark_id='WM-REPORT-2'
    )
    response = submit_report(
        client, asset_id, headers=auth_header,
        reporter_name='测试用户', contact='test@test.com'
    )
    assert response.status_code == 200
    code = response.get_json()['data']['report_code']

    mine = client.get('/api/infringements/mine', headers=auth_header)
    assert mine.status_code == 200
    assert mine.get_json()['data']['items'][0]['report_code'] == code
    assert mine.get_json()['data']['items'][0]['status'] == 'pending'


def test_report_with_only_source_url_is_allowed(client, app):
    response = client.post(
        '/api/infringements/report',
        data={'source_url': 'https://example.com/page', 'description': '疑似盗用'},
        content_type='multipart/form-data',
    )
    assert response.status_code == 200, response.get_json()
    assert response.get_json()['data']['asset'] is None
    assert response.get_json()['data']['trace_verified'] is False


def test_report_requires_some_content(client, app):
    response = client.post(
        '/api/infringements/report', data={}, content_type='multipart/form-data'
    )
    assert response.status_code == 400
    assert '至少' in response.get_json()['message']


def test_report_rejects_unsupported_file_type(client, app):
    response = client.post(
        '/api/infringements/report',
        data={'file': (BytesIO(b'#!/bin/sh'), 'suspect.sh')},
        content_type='multipart/form-data',
    )
    assert response.status_code == 400
    assert '图片' in response.get_json()['message']


def test_report_list_requires_admin(client, auth_header):
    response = client.get('/api/infringements', headers=auth_header)
    assert response.status_code == 403
