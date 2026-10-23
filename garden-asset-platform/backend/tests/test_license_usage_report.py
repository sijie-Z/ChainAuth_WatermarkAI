"""授权使用报表与换版通知测试"""
from datetime import datetime, timedelta
from io import BytesIO

from PIL import Image

from app.extensions import db
from app.models import (
    Asset, AssetVersion, DownloadRecord, License, NotificationEvent, User
)


def make_jpeg(color=(30, 90, 70), size=(64, 48)):
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


def upload_published_asset(
    client, app, tmp_path, headers, title='使用报表资产', color=(30, 90, 70)
):
    app.config['UPLOAD_FOLDER'] = str(tmp_path)
    response = client.post(
        '/api/assets/upload',
        data={
            'file': (make_jpeg(color), 'usage.jpg'),
            'title': title,
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
        db.session.commit()
    return asset_id


def make_license(app, asset_id, licensee_id, code, **overrides):
    now = datetime.utcnow()
    values = {
        'license_code': code,
        'asset_id': asset_id,
        'licensor_id': 1,
        'licensee_id': licensee_id,
        'license_type': 'academic',
        'usage_scope': '教学使用',
        'territory': '中国大陆',
        'start_time': now - timedelta(days=1),
        'end_time': now + timedelta(days=30),
        'status': 'active',
        'download_count': 0,
    }
    values.update(overrides)
    license_row = License(**values)
    db.session.add(license_row)
    db.session.commit()
    return license_row.id


def test_usage_report_summary_rows_and_filters(
    client, app, tmp_path, auth_header, admin_header
):
    asset_a = upload_published_asset(client, app, tmp_path, auth_header, '报表资产A')
    asset_b = upload_published_asset(
        client, app, tmp_path, auth_header, '报表资产B', color=(90, 20, 20)
    )
    licensee_header = register_and_login(client, 'usage_user')
    with app.app_context():
        licensee = User.query.filter_by(username='usage_user').one()
        version_a = AssetVersion.query.filter_by(
            asset_id=asset_a, version_no=1
        ).one()
        version_b1 = AssetVersion.query.filter_by(
            asset_id=asset_b, version_no=1
        ).one()
        version_b2 = AssetVersion(
            asset_id=asset_b,
            version_no=2,
            file_path=version_b1.file_path,
            file_name='v2.jpg',
            file_format='JPG',
            file_size=version_b1.file_size,
            file_hash=version_b1.file_hash,
            change_note='报表换版',
        )
        db.session.add(version_b2)
        db.session.commit()

        active_id = make_license(
            app, asset_a, licensee.id, 'LIC-USAGE-ACTIVE',
            version_id=version_a.id, version_no=1,
            max_downloads=5, download_count=2,
        )
        outdated_id = make_license(
            app, asset_b, licensee.id, 'LIC-USAGE-OUTDATED',
            version_id=version_b1.id, version_no=1,
        )
        revoked_id = make_license(
            app, asset_a, licensee.id, 'LIC-USAGE-REVOKED',
            status='revoked',
        )
        expired_id = make_license(
            app, asset_a, licensee.id, 'LIC-USAGE-EXPIRED',
            start_time=datetime.utcnow() - timedelta(days=40),
            end_time=datetime.utcnow() - timedelta(days=1),
        )
        now = datetime.utcnow()
        db.session.add_all([
            DownloadRecord(
                user_id=licensee.id, asset_id=asset_a, license_id=active_id,
                status='success', usage_purpose='teaching_research',
                territory='中国大陆', created_at=now,
            ),
            DownloadRecord(
                user_id=licensee.id, asset_id=asset_b, license_id=outdated_id,
                status='denied', denial_reason='该授权对应 v1，资产当前为 v2',
                created_at=now,
            ),
            DownloadRecord(
                user_id=licensee.id, asset_id=asset_a, license_id=active_id,
                status='denied', denial_reason='该授权下载次数已用完',
                created_at=now,
            ),
            DownloadRecord(
                user_id=licensee.id, asset_id=asset_a, license_id=active_id,
                status='denied', denial_reason='申报地域与授权不符',
                created_at=now,
            ),
        ])
        db.session.commit()

    response = client.get('/api/license/usage-report?days=30', headers=admin_header)
    assert response.status_code == 200, response.get_json()
    data = response.get_json()['data']
    summary = data['summary']
    assert summary['total'] == 4
    assert summary['active'] == 2
    assert summary['expired'] == 1
    assert summary['revoked'] == 1
    assert summary['version_outdated'] == 1
    assert summary['quota_licenses'] == 1
    assert summary['quota_total'] == 5
    assert summary['quota_used'] == 2
    assert summary['downloads'] == 1
    assert summary['denied'] == 3
    assert summary['downloads_today'] == 1
    assert data['rows']['total'] == 4
    assert len(data['trend']) == 30
    categories = {item['key']: item['count'] for item in data['denial_categories']}
    assert categories['version'] == 1
    assert categories['quota'] == 1
    assert categories['territory'] == 1

    outdated_row = next(
        row for row in data['rows']['items']
        if row['license_code'] == 'LIC-USAGE-OUTDATED'
    )
    assert outdated_row['version_outdated'] is True
    assert outdated_row['current_version_no'] == 2
    assert outdated_row['denied_count'] == 1

    active = client.get(
        '/api/license/usage-report?status=active', headers=admin_header
    ).get_json()['data']
    assert active['rows']['total'] == 2

    outdated = client.get(
        '/api/license/usage-report?version_outdated=1', headers=admin_header
    ).get_json()['data']
    assert outdated['rows']['total'] == 1
    assert outdated['rows']['items'][0]['license_code'] == 'LIC-USAGE-OUTDATED'

    forbidden = client.get(
        '/api/license/usage-report', headers=licensee_header
    )
    assert forbidden.status_code == 403

    bad_days = client.get(
        '/api/license/usage-report?days=abc', headers=admin_header
    )
    assert bad_days.status_code == 400


def test_new_version_notifies_licensee(
    client, app, tmp_path, auth_header
):
    asset_id = upload_published_asset(client, app, tmp_path, auth_header)
    licensee_header = register_and_login(client, 'version_notified_user')
    with app.app_context():
        licensee = User.query.filter_by(username='version_notified_user').one()
        version = AssetVersion.query.filter_by(
            asset_id=asset_id, version_no=1
        ).one()
        license_row = License(
            license_code='LIC-VERSION-NOTIFY',
            asset_id=asset_id,
            licensor_id=1,
            licensee_id=licensee.id,
            license_type='academic',
            usage_scope='教学',
            version_id=version.id,
            version_no=1,
            start_time=datetime.utcnow() - timedelta(days=1),
            end_time=datetime.utcnow() + timedelta(days=30),
            status='active',
        )
        db.session.add(license_row)
        db.session.commit()
        licensee_id = licensee.id

    response = client.post(
        f'/api/assets/{asset_id}/versions',
        data={
            'file': (make_jpeg((100, 20, 20)), 'v2.jpg'),
            'change_note': '换版通知测试'
        },
        headers=auth_header,
        content_type='multipart/form-data'
    )
    assert response.status_code == 200, response.get_json()

    with app.app_context():
        event = NotificationEvent.query.filter_by(
            user_id=licensee_id,
            event_type='license_version_outdated',
        ).one()
        assert 'v2' in event.title
        assert '重新申请' in event.description
        assert event.link.endswith('?tab=versions')
