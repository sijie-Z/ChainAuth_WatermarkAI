"""存储巡检测试

只读盘点：数据库已引用的文件不算孤儿，新写入的文件有保护期，
API 仅管理员可用。
"""
import os
import time

from app.extensions import db
from app.models.asset import Asset, AssetVersion
from app.services import storage_service


def make_asset(storage_path, watermarked_path=None, version_path=None):
    asset = Asset(
        asset_code='STO-IMG-001',
        title='存储巡检测试',
        asset_type='image',
        file_format='JPG',
        storage_path=str(storage_path),
        watermarked_path=str(watermarked_path) if watermarked_path else None,
        status='published',
    )
    db.session.add(asset)
    db.session.flush()
    if version_path:
        db.session.add(AssetVersion(
            asset_id=asset.id,
            version_no=1,
            file_path=str(version_path),
            file_hash='abc',
            file_size=10,
        ))
    db.session.commit()
    return asset


def age_file(path, hours=48):
    stamp = time.time() - hours * 3600
    os.utime(path, (stamp, stamp))


def test_storage_summary_and_orphans(app, tmp_path):
    uploads = tmp_path / 'uploads'
    watermarks = tmp_path / 'watermarks'
    extracted = tmp_path / 'extracted'
    for folder in (uploads, watermarks, extracted):
        folder.mkdir()

    referenced_original = uploads / 'origin.jpg'
    referenced_watermark = watermarks / 'mark.png'
    referenced_version = uploads / 'v1.jpg'
    orphan_old = uploads / 'orphan-old.jpg'
    orphan_new = uploads / 'orphan-new.jpg'
    orphan_mark = watermarks / 'orphan-mark.png'

    for path in (referenced_original, referenced_watermark, referenced_version,
                 orphan_old, orphan_new, orphan_mark):
        path.write_bytes(b'x' * 32)

    age_file(orphan_old)
    age_file(orphan_mark)

    app.config.update(
        UPLOAD_FOLDER=str(uploads),
        WATERMARK_FOLDER=str(watermarks),
        EXTRACTED_FOLDER=str(extracted),
    )

    with app.app_context():
        make_asset(referenced_original, referenced_watermark, referenced_version)

        summary = storage_service.storage_summary()
        assert summary['files'] == 6
        assert summary['bytes'] == 32 * 6
        roots = {item['key']: item for item in summary['roots']}
        assert roots['uploads']['files'] == 4
        assert roots['watermarks']['files'] == 2

        report = storage_service.find_orphans(min_age_hours=1, limit=10)
        assert report['count'] == 2
        assert report['total_bytes'] == 64
        names = {item['relative'] for item in report['items']}
        assert names == {'orphan-old.jpg', 'orphan-mark.png'}
        assert report['referenced_files'] == 3


def test_storage_api_requires_admin(client, admin_header, auth_header, app, tmp_path):
    app.config.update(
        UPLOAD_FOLDER=str(tmp_path / 'uploads'),
        WATERMARK_FOLDER=str(tmp_path / 'watermarks'),
        EXTRACTED_FOLDER=str(tmp_path / 'extracted'),
    )

    forbidden = client.get('/api/system/storage', headers=auth_header)
    assert forbidden.status_code == 403

    response = client.get(
        '/api/system/storage?min_age_hours=1', headers=admin_header
    )
    assert response.status_code == 200
    data = response.get_json()['data']
    assert 'summary' in data and 'orphans' in data
    assert data['orphans']['min_age_hours'] == 1


def test_storage_cli_reports_without_deleting(app, runner, tmp_path):
    uploads = tmp_path / 'uploads'
    uploads.mkdir()
    orphan = uploads / 'orphan.jpg'
    orphan.write_bytes(b'y' * 10)
    age_file(orphan)
    app.config.update(
        UPLOAD_FOLDER=str(uploads),
        WATERMARK_FOLDER=str(tmp_path / 'watermarks'),
        EXTRACTED_FOLDER=str(tmp_path / 'extracted'),
    )

    result = runner.invoke(args=['storage', 'report', '--min-age-hours', '1'])
    assert result.exit_code == 0, result.output
    assert '孤儿候选：1 个' in result.output
    assert 'orphan.jpg' in result.output
    assert '只报告，不删除' in result.output
    assert orphan.exists()
