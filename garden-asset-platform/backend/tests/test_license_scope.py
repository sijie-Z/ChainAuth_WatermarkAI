"""授权范围执行测试

覆盖结构化范围（用途/渠道/格式/地域/次数）申请、审批落库与下载拦截，
以及拒绝记录进入下载台账。
"""
from datetime import datetime, timedelta
from io import BytesIO

from PIL import Image

from app.extensions import db
from app.models import Asset, DownloadRecord, License, User


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


def upload_published_asset(client, app, tmp_path, headers):
    app.config['UPLOAD_FOLDER'] = str(tmp_path)
    response = client.post(
        '/api/assets/upload',
        data={
            'file': (make_jpeg(), 'scope.jpg'),
            'title': '授权范围测试影像',
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
        asset.publish_at = datetime.utcnow()
        db.session.commit()
    return asset_id


def make_license(app, asset_id, licensee_id, **overrides):
    with app.app_context():
        asset = db.session.get(Asset, asset_id)
        values = {
            'license_code': f'LIC-SCOPE-{licensee_id}-{int(datetime.utcnow().timestamp())}',
            'asset_id': asset_id,
            'licensor_id': asset.uploader_id,
            'licensee_id': licensee_id,
            'license_type': 'academic',
            'usage_scope': '教学科研使用',
            'territory': '中国大陆',
            'usage_purpose_code': 'teaching_research',
            'allowed_channels': ['online'],
            'allowed_formats': ['JPG'],
            'max_downloads': None,
            'start_time': datetime.utcnow() - timedelta(days=1),
            'end_time': datetime.utcnow() + timedelta(days=30),
            'status': 'active',
        }
        values.update(overrides)
        license_row = License(**values)
        db.session.add(license_row)
        db.session.commit()
        return license_row.id


def test_download_requires_declared_scope_and_records_denial(
    client, app, tmp_path, auth_header
):
    asset_id = upload_published_asset(client, app, tmp_path, auth_header)
    licensee_header = register_and_login(client, 'scope_user')
    with app.app_context():
        licensee = User.query.filter_by(username='scope_user').one()
        license_id = make_license(app, asset_id, licensee.id)
        licensee_id = licensee.id

    # 未声明用途/地域：拒绝，并写入 denied 台账
    response = client.get(f'/api/assets/{asset_id}/download', headers=licensee_header)
    assert response.status_code == 403
    assert '使用目的' in response.get_json()['message']

    with app.app_context():
        record = DownloadRecord.query.filter_by(
            asset_id=asset_id, user_id=licensee_id
        ).one()
        assert record.status == 'denied'
        assert record.license_id == license_id
        assert '使用目的' in record.denial_reason

    # 用途与授权不符
    response = client.get(
        f'/api/assets/{asset_id}/download?purpose=commercial_marketing&territory=中国大陆',
        headers=licensee_header
    )
    assert response.status_code == 403
    assert '用途' in response.get_json()['message']

    # 符合范围：下载成功并累计授权下载次数
    response = client.get(
        f'/api/assets/{asset_id}/download?purpose=teaching_research&territory=中国大陆',
        headers=licensee_header
    )
    assert response.status_code == 200
    assert response.data

    with app.app_context():
        license_row = db.session.get(License, license_id)
        assert license_row.download_count == 1
        success = DownloadRecord.query.filter_by(
            asset_id=asset_id, user_id=licensee_id, status='success'
        ).one()
        assert success.usage_purpose == 'teaching_research'
        assert success.territory == '中国大陆'


def test_download_enforces_format_territory_and_quota(
    client, app, tmp_path, auth_header
):
    asset_id = upload_published_asset(client, app, tmp_path, auth_header)
    licensee_header = register_and_login(client, 'scope_limit_user')
    with app.app_context():
        licensee = User.query.filter_by(username='scope_limit_user').one()
        license_id = make_license(
            app, asset_id, licensee.id,
            allowed_formats=['PNG'],
            max_downloads=1,
            territory='中国港澳台',
        )
        licensee_id = licensee.id

    # 格式不在授权范围
    response = client.get(
        f'/api/assets/{asset_id}/download?purpose=teaching_research&territory=中国港澳台',
        headers=licensee_header
    )
    assert response.status_code == 403
    assert '格式' in response.get_json()['message']

    # 改为 JPG 后地域不符
    with app.app_context():
        license_row = db.session.get(License, license_id)
        license_row.allowed_formats = ['JPG']
        db.session.commit()

    response = client.get(
        f'/api/assets/{asset_id}/download?purpose=teaching_research&territory=中国大陆',
        headers=licensee_header
    )
    assert response.status_code == 403
    assert '地域' in response.get_json()['message']

    # 正确范围第一次成功
    response = client.get(
        f'/api/assets/{asset_id}/download?purpose=teaching_research&territory=中国港澳台',
        headers=licensee_header
    )
    assert response.status_code == 200

    # 第二次超过下载次数上限
    response = client.get(
        f'/api/assets/{asset_id}/download?purpose=teaching_research&territory=中国港澳台',
        headers=licensee_header
    )
    assert response.status_code == 403
    assert '次数' in response.get_json()['message']

    with app.app_context():
        denied = DownloadRecord.query.filter_by(
            asset_id=asset_id, user_id=licensee_id, status='denied'
        ).count()
        assert denied >= 3


def test_global_territory_accepts_any_known_region(
    client, app, tmp_path, auth_header
):
    asset_id = upload_published_asset(client, app, tmp_path, auth_header)
    licensee_header = register_and_login(client, 'scope_global_user')
    with app.app_context():
        licensee = User.query.filter_by(username='scope_global_user').one()
        make_license(
            app, asset_id, licensee.id,
            territory='全球',
            allowed_formats=['JPG'],
        )

    response = client.get(
        f'/api/assets/{asset_id}/download?purpose=teaching_research&territory=海外',
        headers=licensee_header
    )
    assert response.status_code == 200


def test_legacy_license_without_structured_scope_still_downloads(
    client, app, tmp_path, auth_header
):
    asset_id = upload_published_asset(client, app, tmp_path, auth_header)
    licensee_header = register_and_login(client, 'scope_legacy_user')
    with app.app_context():
        licensee = User.query.filter_by(username='scope_legacy_user').one()
        make_license(
            app, asset_id, licensee.id,
            usage_purpose_code=None,
            allowed_formats=None,
            max_downloads=None,
            territory='约定区域',
        )

    response = client.get(f'/api/assets/{asset_id}/download', headers=licensee_header)
    assert response.status_code == 200


def test_apply_validates_and_persists_scope(client, app, tmp_path, auth_header):
    asset_id = upload_published_asset(client, app, tmp_path, auth_header)
    applicant_header = register_and_login(client, 'scope_applicant')

    invalid = client.post('/api/license/apply', json={
        'asset_id': asset_id,
        'license_type': 'academic',
        'purpose': '课程教学',
        'usage_purpose_code': 'teaching_research',
        'allowed_formats': ['EXE'],
        'territory': '中国大陆',
        'valid_period': '3m',
        'contact': 'applicant@test.com',
    }, headers=applicant_header)
    assert invalid.status_code == 400
    assert '格式' in invalid.get_json()['message']

    response = client.post('/api/license/apply', json={
        'asset_id': asset_id,
        'license_type': 'academic',
        'purpose': '课程教学',
        'usage_purpose_code': 'teaching_research',
        'allowed_channels': ['online', 'print'],
        'allowed_formats': ['JPG'],
        'max_downloads': 5,
        'territory': '中国大陆',
        'valid_period': '3m',
        'contact': 'applicant@test.com',
    }, headers=applicant_header)
    assert response.status_code == 200, response.get_json()
    data = response.get_json()['data']
    assert data['usage_purpose_code'] == 'teaching_research'
    assert data['allowed_channels'] == ['online', 'print']
    assert data['allowed_formats'] == ['JPG']
    assert data['max_downloads'] == 5

    # 审批通过后范围字段复制到授权记录
    application_id = data['id']
    first = client.post(
        f'/api/license/approve/{application_id}',
        json={'action': 'approve', 'comment': '同意'},
        headers=_adm1(client, app),
    )
    assert first.status_code == 200, first.get_json()
    second = client.post(
        f'/api/license/approve/{application_id}',
        json={'action': 'approve', 'comment': '复核通过'},
        headers=_adm2(client, app),
    )
    assert second.status_code == 200, second.get_json()

    with app.app_context():
        applicant = User.query.filter_by(username='scope_applicant').one()
        license_row = License.query.filter_by(
            asset_id=asset_id, licensee_id=applicant.id
        ).one()
        assert license_row.usage_purpose_code == 'teaching_research'
        assert license_row.allowed_channels == ['online', 'print']
        assert license_row.allowed_formats == ['JPG']
        assert license_row.max_downloads == 5


def _adm1(client, app):
    with app.app_context():
        if not User.query.filter_by(username='scope_adm1').first():
            user = User(username='scope_adm1', email='scope_adm1@test.com', role='adm1')
            user.set_password('pass1234')
            db.session.add(user)
            db.session.commit()
    response = client.post('/api/login', json={
        'username': 'scope_adm1', 'password': 'pass1234'
    })
    return {'Authorization': f"Bearer {response.get_json()['data']['access_token']}"}


def _adm2(client, app):
    with app.app_context():
        if not User.query.filter_by(username='scope_adm2').first():
            user = User(username='scope_adm2', email='scope_adm2@test.com', role='adm2')
            user.set_password('pass1234')
            db.session.add(user)
            db.session.commit()
    response = client.post('/api/login', json={
        'username': 'scope_adm2', 'password': 'pass1234'
    })
    return {'Authorization': f"Bearer {response.get_json()['data']['access_token']}"}
