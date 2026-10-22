"""版本级存证证书测试

覆盖：证书绑定当前版本、新版本重置资产存证状态、历史证书保留、
证书页返回版本信息、同一版本重复存证幂等，以及版本列表挂载证书。
"""
from io import BytesIO

from PIL import Image

from app.extensions import db
from app.models.asset import Asset, AssetVersion
from app.models.blockchain import Certificate
from app.models.task import AsyncTask
from app.services.blockchain_service import blockchain_service


def make_jpeg(color=(20, 60, 50), size=(64, 48)):
    buffer = BytesIO()
    Image.new('RGB', size, color).save(buffer, 'JPEG')
    buffer.seek(0)
    return buffer


def upload_asset(client, app, tmp_path, headers, color=(10, 30, 50)):
    app.config['UPLOAD_FOLDER'] = str(tmp_path)
    response = client.post(
        '/api/assets/upload',
        data={
            'file': (make_jpeg(color), '证书测试.jpg'),
            'title': '版本证书测试影像',
            'asset_type': 'image'
        },
        headers=headers,
        content_type='multipart/form-data'
    )
    assert response.status_code == 200, response.get_json()
    return response.get_json()['data']['asset_id']


def upload_version(client, headers, asset_id, color):
    return client.post(
        f'/api/assets/{asset_id}/versions',
        data={
            'file': (make_jpeg(color), '新版本.jpg'),
            'change_note': '替换为高清文件'
        },
        headers=headers,
        content_type='multipart/form-data'
    )


def set_watermark_ready(app, asset_id, watermark_id='WM-VERSION-TEST'):
    with app.app_context():
        asset = db.session.get(Asset, asset_id)
        asset.watermark_status = 'embedded'
        asset.watermark_id = watermark_id
        db.session.commit()


def certify(client, headers, asset_id):
    return client.post(
        '/api/blockchain/register',
        json={'asset_id': asset_id},
        headers=headers,
    )


def test_certificate_binds_current_version(client, app, tmp_path, auth_header):
    asset_id = upload_asset(client, app, tmp_path, auth_header)
    set_watermark_ready(app, asset_id)

    response = certify(client, auth_header, asset_id)
    assert response.status_code == 200, response.get_json()
    certificate_id = response.get_json()['data']['certificate_id']
    version_no = response.get_json()['data']['version_no']
    assert version_no == 1

    with app.app_context():
        version = AssetVersion.query.filter_by(
            asset_id=asset_id, version_no=1
        ).one()
        certificate = Certificate.query.filter_by(
            certificate_id=certificate_id
        ).one()
        assert certificate.asset_id == asset_id
        assert certificate.version_id == version.id
        assert certificate.version_no == 1
        assert certificate.file_hash == version.file_hash

        asset = db.session.get(Asset, asset_id)
        assert asset.certificate_id == certificate_id
        assert asset.chain_status == 'confirmed'


def test_new_version_resets_chain_and_keeps_history(client, app, tmp_path, auth_header):
    asset_id = upload_asset(client, app, tmp_path, auth_header)
    set_watermark_ready(app, asset_id)
    assert certify(client, auth_header, asset_id).status_code == 200

    with app.app_context():
        first_certificate = Certificate.query.filter_by(asset_id=asset_id).one()
        first_certificate_id = first_certificate.certificate_id

    response = upload_version(client, auth_header, asset_id, color=(180, 30, 30))
    assert response.status_code == 200, response.get_json()

    with app.app_context():
        asset = db.session.get(Asset, asset_id)
        # 当前文件未存证，主表不能继续声称已存证
        assert asset.chain_status == 'none'
        assert asset.chain_tx_hash is None
        assert asset.certificate_id is None
        # 历史证书仍在，并绑定 v1
        certificates = Certificate.query.filter_by(asset_id=asset_id).all()
        assert len(certificates) == 1
        assert certificates[0].certificate_id == first_certificate_id
        assert certificates[0].version_no == 1

    # 版本列表为每个版本挂载证书
    versions = client.get(
        f'/api/assets/{asset_id}/versions', headers=auth_header
    ).get_json()['data']['items']
    by_no = {item['version_no']: item for item in versions}
    assert by_no[1]['certificate']['certificate_id'] == first_certificate_id
    assert by_no[1]['certificate']['is_current'] is False
    assert by_no[2]['certificate'] is None


def test_recertify_new_version_and_public_verify(client, app, tmp_path, auth_header):
    asset_id = upload_asset(client, app, tmp_path, auth_header)
    set_watermark_ready(app, asset_id)
    first = certify(client, auth_header, asset_id).get_json()['data']

    upload_version(client, auth_header, asset_id, color=(30, 120, 30))

    with app.app_context():
        asset = db.session.get(Asset, asset_id)
        asset.status = 'published'
        db.session.commit()

    # 当前版本未存证：公开验证必须失败，而不是拿旧证书冒充
    verify = client.get(f'/api/blockchain/verify/{asset_id}')
    assert verify.status_code == 200
    body = verify.get_json()
    assert body['verified'] is False
    assert '历史版本' in body['message']

    # 新版本重新水印并签发新证书
    set_watermark_ready(app, asset_id, 'WM-VERSION-TEST-V2')
    second = certify(client, auth_header, asset_id)
    assert second.status_code == 200, second.get_json()
    second_data = second.get_json()['data']
    assert second_data['certificate_id'] != first['certificate_id']
    assert second_data['version_no'] == 2

    verify = client.get(f'/api/blockchain/verify/{asset_id}').get_json()
    assert verify['verified'] is True
    assert verify['data']['version_no'] == 2
    assert verify['data']['current_version_no'] == 2

    # 证书页明确标注旧证书对应历史版本
    old_cert = client.get(
        f"/api/blockchain/certificate/{first['certificate_id']}"
    ).get_json()['data']
    assert old_cert['certificate']['version_no'] == 1
    assert old_cert['is_current_version'] is False
    assert old_cert['has_newer_version'] is True
    assert old_cert['current_version_no'] == 2
    assert old_cert['certificate_count'] == 2

    new_cert = client.get(
        f"/api/blockchain/certificate/{second_data['certificate_id']}"
    ).get_json()['data']
    assert new_cert['is_current_version'] is True
    assert new_cert['version']['version_no'] == 2


def test_same_file_new_version_does_not_inherit_old_certificate(
    client, app, tmp_path, auth_header
):
    """新版本即使内容相同，也必须重新存证，不能沿用旧版本证书"""
    asset_id = upload_asset(client, app, tmp_path, auth_header, color=(10, 30, 50))
    set_watermark_ready(app, asset_id)
    first = certify(client, auth_header, asset_id).get_json()['data']

    # 用相同颜色生成同内容文件，哈希与 v1 一致
    upload_version(client, auth_header, asset_id, color=(10, 30, 50))

    versions = client.get(
        f'/api/assets/{asset_id}/versions', headers=auth_header
    ).get_json()['data']['items']
    by_no = {item['version_no']: item for item in versions}
    assert by_no[1]['certificate']['certificate_id'] == first['certificate_id']
    assert by_no[2]['certificate'] is None

    with app.app_context():
        asset = db.session.get(Asset, asset_id)
        assert asset.chain_status == 'none'
        assert asset.certificate_id is None


def test_version_upload_blocked_while_task_running(client, app, tmp_path, auth_header):
    asset_id = upload_asset(client, app, tmp_path, auth_header)
    with app.app_context():
        version = AssetVersion.query.filter_by(
            asset_id=asset_id, version_no=1
        ).one()
        db.session.add(AsyncTask(
            task_type='watermark_embed',
            status='running',
            asset_id=asset_id,
            version_id=version.id,
            attempts=1,
            max_attempts=3,
        ))
        db.session.commit()

    response = upload_version(client, auth_header, asset_id, color=(90, 20, 20))
    assert response.status_code == 409
    assert '任务' in response.get_json()['message']


def test_version_upload_cancels_queued_tasks(client, app, tmp_path, auth_header):
    asset_id = upload_asset(client, app, tmp_path, auth_header)
    with app.app_context():
        version = AssetVersion.query.filter_by(
            asset_id=asset_id, version_no=1
        ).one()
        task = AsyncTask(
            task_type='watermark_embed',
            status='queued',
            asset_id=asset_id,
            version_id=version.id,
            attempts=0,
            max_attempts=3,
        )
        db.session.add(task)
        db.session.commit()
        task_id = task.id

    response = upload_version(client, auth_header, asset_id, color=(60, 140, 60))
    assert response.status_code == 200, response.get_json()

    with app.app_context():
        task = db.session.get(AsyncTask, task_id)
        assert task.status == 'cancelled'
        assert '文件已更新' in task.error_message


def test_duplicate_certification_is_idempotent(client, app, tmp_path, auth_header):
    asset_id = upload_asset(client, app, tmp_path, auth_header)
    set_watermark_ready(app, asset_id)
    first = certify(client, auth_header, asset_id)
    assert first.status_code == 200
    certificate_id = first.get_json()['data']['certificate_id']

    again = certify(client, auth_header, asset_id)
    assert again.status_code == 400
    assert '已存证' in again.get_json()['message']

    with app.app_context():
        assert Certificate.query.filter_by(asset_id=asset_id).count() == 1
        asset = db.session.get(Asset, asset_id)
        result = blockchain_service.register_asset(asset)
        assert result['success'] is True
        assert result['already'] is True
        assert result['certificate_id'] == certificate_id
