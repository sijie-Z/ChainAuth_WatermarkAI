"""资产证据包导出测试"""
import hashlib
import io
import json
import zipfile

from app.extensions import db
from app.models.asset import Asset, AssetVersion
from app.models.blockchain import Certificate
from app.models.user import User


def _sha256(data):
    return hashlib.sha256(data).hexdigest()


def _prepare_asset(app, tmp_path, asset_id, username='testuser'):
    original = tmp_path / 'garden-photo.jpg'
    watermarked = tmp_path / 'garden-photo-watermarked.png'
    original.write_bytes(b'original-garden-photo-bytes')
    watermarked.write_bytes(b'watermarked-garden-photo-bytes')
    original_hash = _sha256(original.read_bytes())

    with app.app_context():
        owner = User.query.filter_by(username=username).first()
        asset = Asset.query.get(asset_id)
        asset.owner_id = owner.id
        asset.uploader_id = owner.id
        asset.creator_id = owner.id
        asset.storage_path = str(original)
        asset.watermarked_path = str(watermarked)
        asset.file_hash = original_hash
        asset.file_size = original.stat().st_size
        asset.watermark_status = 'embedded'
        asset.watermark_id = 'ZY-IMG-20260101000000-ABCD'
        asset.chain_status = 'confirmed'
        asset.chain_tx_hash = '0x' + 'a' * 64
        asset.certificate_id = 'CERT-20260101000000-ABCD'

        version = AssetVersion(
            asset_id=asset.id,
            version_no=1,
            file_path=str(original),
            file_name='garden-photo.jpg',
            file_format='JPG',
            file_size=original.stat().st_size,
            file_hash=original_hash,
            change_note='初始版本',
        )
        db.session.add(version)
        db.session.flush()

        certificate = Certificate(
            certificate_id=asset.certificate_id,
            asset_id=asset.id,
            version_id=version.id,
            version_no=1,
            tx_hash=asset.chain_tx_hash,
            block_number=123456,
            watermark_id=asset.watermark_id,
            file_hash=original_hash,
            creator_name=owner.username,
            ownership_type='original',
            status='valid',
        )
        db.session.add(certificate)
        db.session.commit()

    return {
        'asset_id': asset_id,
        'original_hash': original_hash,
        'original_size': original.stat().st_size,
    }


def test_owner_can_export_evidence_package(
    client, app, auth_header, sample_asset, tmp_path
):
    app.config['UPLOAD_FOLDER'] = str(tmp_path / 'uploads')
    fixture = _prepare_asset(app, tmp_path, sample_asset)

    response = client.get(
        f"/api/assets/{sample_asset}/evidence-package",
        headers=auth_header,
    )

    assert response.status_code == 200
    assert response.mimetype == 'application/zip'
    assert response.headers['X-Evidence-Package-Files'] == '2'
    assert response.headers['X-Evidence-Package-Omitted'] == '0'

    archive = zipfile.ZipFile(io.BytesIO(response.data))
    names = archive.namelist()
    assert 'manifest.json' in names
    assert 'evidence-chain.json' in names
    assert 'README.txt' in names
    assert 'SHA256SUMS' in names
    assert 'certificates/CERT-20260101000000-ABCD.json' in names
    assert any(name.startswith('files/') and name.endswith('.jpg') for name in names)
    assert any(name.startswith('files/') and 'watermarked' in name for name in names)

    manifest = json.loads(archive.read('manifest.json').decode('utf-8'))
    assert manifest['schema'] == 'chainauth-evidence-package/1'
    assert manifest['asset']['asset_code'] == 'ZY-IMG-20260101-001'
    assert manifest['watermark']['watermark_id'] == 'ZY-IMG-20260101000000-ABCD'
    assert manifest['chain']['simulated'] is True
    assert manifest['current_version']['version_no'] == 1
    assert manifest['certificates'][0]['is_current'] is True
    assert manifest['binary_policy']['included'] is True

    original_entry = next(
        item for item in manifest['files'] if item['role'] == 'original'
    )
    assert original_entry['sha256'] == fixture['original_hash']
    assert original_entry['hash_matches_record'] is True
    assert original_entry['size'] == fixture['original_size']

    sums = archive.read('SHA256SUMS').decode('utf-8')
    assert fixture['original_hash'] in sums
    assert 'manifest.json' in sums

    response.close()
    evidence_root = tmp_path / 'uploads' / 'evidence_tmp'
    assert not list(evidence_root.glob('evidence_*'))


def test_evidence_package_can_omit_binaries(
    client, app, auth_header, sample_asset, tmp_path
):
    app.config['UPLOAD_FOLDER'] = str(tmp_path / 'uploads')
    _prepare_asset(app, tmp_path, sample_asset)

    response = client.get(
        f"/api/assets/{sample_asset}/evidence-package",
        query_string={'include_files': '0'},
        headers=auth_header,
    )

    assert response.status_code == 200
    assert response.headers['X-Evidence-Package-Omitted'] == '1'
    archive = zipfile.ZipFile(io.BytesIO(response.data))
    assert not any(name.startswith('files/') for name in archive.namelist())
    manifest = json.loads(archive.read('manifest.json').decode('utf-8'))
    assert manifest['binary_policy']['include_files'] is False
    assert manifest['binary_policy']['included'] is False
    assert 'include_files=0' in manifest['binary_policy']['omitted_reason']
    response.close()


def test_evidence_package_requires_owner_or_asset_admin(
    client, app, auth_header, sample_asset, adm1_header, tmp_path
):
    app.config['UPLOAD_FOLDER'] = str(tmp_path / 'uploads')
    _prepare_asset(app, tmp_path, sample_asset)

    # adm1 是审批员，不是资产管理员，也不是资产所有者
    response = client.get(
        f"/api/assets/{sample_asset}/evidence-package",
        headers=adm1_header,
    )

    assert response.status_code == 403
    assert '所有者' in response.get_json()['message']


def test_evidence_package_missing_asset_returns_404(client, auth_header):
    response = client.get(
        '/api/assets/not-exists/evidence-package', headers=auth_header
    )

    assert response.status_code == 404
