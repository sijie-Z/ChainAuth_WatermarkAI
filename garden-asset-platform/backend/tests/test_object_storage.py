"""对象存储兼容层测试（fake MinIO，不需要 Docker）"""
import hashlib
import io
import os
import zipfile
from types import SimpleNamespace

from app.extensions import db
from app.models import Asset, AssetVersion

import pytest

from app.services import object_storage


class FakeResponse:
    def __init__(self, data):
        self.data = data
        self.closed = False
        self.released = False

    def read(self, size=-1):
        if size is None or size < 0:
            size = len(self.data)
        result, self.data = self.data[:size], self.data[size:]
        return result

    def close(self):
        self.closed = True

    def release_conn(self):
        self.released = True


class FakeMinio:
    def __init__(self):
        self.objects = {}
        self.buckets = set()

    def bucket_exists(self, bucket):
        return bucket in self.buckets

    def make_bucket(self, bucket):
        self.buckets.add(bucket)

    def fput_object(self, bucket, key, path, content_type=None):
        with open(path, 'rb') as handle:
            self.objects[(bucket, key)] = handle.read()

    def stat_object(self, bucket, key):
        if (bucket, key) not in self.objects:
            raise FileNotFoundError(key)
        return SimpleNamespace(size=len(self.objects[(bucket, key)]))

    def get_object(self, bucket, key, offset=0, length=None):
        data = self.objects[(bucket, key)]
        if length is None:
            length = len(data) - offset
        return FakeResponse(data[offset:offset + length])

    def remove_object(self, bucket, key):
        self.objects.pop((bucket, key), None)


class RacingMinio(FakeMinio):
    def make_bucket(self, bucket):
        super().make_bucket(bucket)
        error = RuntimeError('bucket already exists')
        error.code = 'BucketAlreadyExists'
        raise error


@pytest.fixture
def fake_minio(app, monkeypatch, tmp_path):
    fake = FakeMinio()
    app.config['STORAGE_BACKEND'] = 'minio'
    app.config['MINIO_BUCKET'] = 'test-bucket'
    app.config['UPLOAD_FOLDER'] = str(tmp_path)
    monkeypatch.setattr(object_storage, '_client', fake)
    monkeypatch.setattr(object_storage, '_bucket_ready', set())
    return fake


def test_local_mode_keeps_existing_paths(app, tmp_path):
    app.config['STORAGE_BACKEND'] = 'local'
    source = tmp_path / 'source.jpg'
    source.write_bytes(b'local-content')
    with app.app_context():
        assert object_storage.store_original(
            str(source), '00000000-0000-0000-0000-000000000001', '.jpg'
        ) == str(source)
        assert object_storage.ref_exists(str(source))
        assert object_storage.ref_size(str(source)) == len(b'local-content')
        assert object_storage.hash_ref(str(source)) == hashlib.sha256(
            b'local-content'
        ).hexdigest()


def test_concurrent_bucket_creation_is_idempotent(app, monkeypatch, tmp_path):
    app.config['STORAGE_BACKEND'] = 'minio'
    app.config['MINIO_BUCKET'] = 'race-bucket'
    app.config['UPLOAD_FOLDER'] = str(tmp_path)
    monkeypatch.setattr(object_storage, '_client', RacingMinio())
    monkeypatch.setattr(object_storage, '_bucket_ready', set())
    with app.app_context():
        assert object_storage.ensure_bucket() == 'race-bucket'
        assert object_storage.ensure_bucket() == 'race-bucket'


def test_minio_upload_stream_hash_materialize_and_delete(
    app, fake_minio, tmp_path
):
    payload = bytes(range(256)) * 1024
    source = tmp_path / 'source.bin'
    source.write_bytes(payload)
    with app.app_context():
        ref = object_storage.store_original(
            str(source), '00000000-0000-0000-0000-000000000001', '.bin'
        )
        assert ref.startswith('minio://test-bucket/assets/')
        assert object_storage.ref_exists(ref)
        assert object_storage.ref_size(ref) == len(payload)
        assert object_storage.hash_ref(ref) == hashlib.sha256(payload).hexdigest()
        assert b''.join(object_storage.iter_ref(ref, 10, 20)) == payload[10:30]

        with object_storage.materialize_ref(ref, '.bin') as local_path:
            assert os.path.isfile(local_path)
            with open(local_path, 'rb') as handle:
                assert handle.read() == payload
        assert not os.path.exists(local_path)

        object_storage.delete_ref(ref)
        assert not object_storage.ref_exists(ref)


def test_minio_download_and_single_range(app, fake_minio, tmp_path):
    payload = b'0123456789abcdef'
    source = tmp_path / 'video.mp4'
    source.write_bytes(payload)
    with app.app_context():
        ref = object_storage.store_original(
            str(source), '00000000-0000-0000-0000-000000000001', '.mp4'
        )
        with app.test_request_context('/preview'):
            response = object_storage.send_ref(
                ref, 'asset.pdf', mimetype='application/pdf'
            )
            assert response.status_code == 200
            assert b''.join(response.iter_encoded()) == payload
            assert response.headers['Content-Type'].startswith('application/pdf')
            assert response.headers['Accept-Ranges'] == 'bytes'

        with app.test_request_context(
            '/preview', headers={'Range': 'bytes=2-5'}
        ):
            response = object_storage.send_ref_range(ref, 'asset.mp4')
            assert response.status_code == 206
            assert b''.join(response.iter_encoded()) == payload[2:6]
            assert response.headers['Content-Range'] == 'bytes 2-5/16'

        with app.test_request_context(
            '/preview', headers={'Range': 'bytes=-4'}
        ):
            response = object_storage.send_ref_range(ref, 'asset.mp4')
            assert response.status_code == 206
            assert b''.join(response.iter_encoded()) == payload[-4:]

        with app.test_request_context(
            '/preview', headers={'Range': 'bytes=99-100'}
        ):
            response = object_storage.send_ref_range(ref, 'asset.mp4')
            assert response.status_code == 416
            assert response.headers['Content-Range'] == 'bytes */16'


def test_relative_local_paths_are_normalized(app, tmp_path, monkeypatch):
    app.config['STORAGE_BACKEND'] = 'local'
    upload_dir = tmp_path / 'uploads'
    upload_dir.mkdir()
    source = upload_dir / 'model.gltf'
    source.write_bytes(b'{"asset":{"version":"2.0"}}')
    monkeypatch.chdir(tmp_path)
    with app.app_context(), app.test_request_context('/preview'):
        response = object_storage.send_ref_range(
            './uploads/model.gltf', 'model.gltf'
        )
        assert response.status_code == 200
        assert b''.join(response.iter_encoded()) == b'{"asset":{"version":"2.0"}}'


def test_minio_ref_rejects_traversal(app, fake_minio):
    with app.app_context():
        with pytest.raises(ValueError):
            object_storage.ref_size('minio://test-bucket/assets/../secret')


def _pdf_bytes(marker=b'1'):
    return (
        b'%PDF-1.4\n1 0 obj<</Type/Catalog>>endobj\n'
        + marker * 32
        + b'\ntrailer<</Root 1 0 R>>\n%%EOF\n'
    )


def test_minio_asset_upload_versions_download_preview_and_evidence(
    client, app, auth_header, fake_minio, tmp_path, monkeypatch
):
    first_pdf = _pdf_bytes(b'A')
    response = client.post(
        '/api/assets/upload',
        data={
            'file': (io.BytesIO(first_pdf), 'object-doc.pdf'),
            'title': '对象存储文档',
            'asset_type': 'document',
        },
        headers=auth_header,
        content_type='multipart/form-data',
    )
    assert response.status_code == 200, response.get_json()
    asset_id = response.get_json()['data']['asset_id']

    with app.app_context():
        asset = db.session.get(Asset, asset_id)
        assert asset.storage_path.startswith('minio://test-bucket/')
        version = AssetVersion.query.filter_by(asset_id=asset_id).one()
        assert version.file_path == asset.storage_path

    download = client.get(
        f'/api/assets/{asset_id}/download', headers=auth_header
    )
    assert download.status_code == 200
    assert b''.join(download.iter_encoded()) == first_pdf

    preview = client.get(
        f'/api/assets/{asset_id}/preview',
        headers={**auth_header, 'Range': 'bytes=0-7'},
    )
    assert preview.status_code == 206
    assert b''.join(preview.iter_encoded()) == first_pdf[:8]

    second_pdf = _pdf_bytes(b'B')
    version_response = client.post(
        f'/api/assets/{asset_id}/versions',
        data={'file': (io.BytesIO(second_pdf), 'object-v2.pdf')},
        headers=auth_header,
        content_type='multipart/form-data',
    )
    assert version_response.status_code == 200, version_response.get_json()
    with app.app_context():
        v1 = AssetVersion.query.filter_by(
            asset_id=asset_id, version_no=1
        ).one()
        v2 = AssetVersion.query.filter_by(
            asset_id=asset_id, version_no=2
        ).one()
        assert v1.file_path.startswith('minio://')
        assert v2.file_path.startswith('minio://')
        v1_id = v1.id

    restored = client.post(
        f'/api/assets/{asset_id}/versions/{v1_id}/restore',
        headers=auth_header,
    )
    assert restored.status_code == 200, restored.get_json()
    assert restored.get_json()['data']['asset']['current_version_no'] == 3

    evidence = client.get(
        f'/api/assets/{asset_id}/evidence-package', headers=auth_header
    )
    assert evidence.status_code == 200
    with zipfile.ZipFile(io.BytesIO(evidence.data)) as archive:
        names = archive.namelist()
        assert 'manifest.json' in names
        assert any(name.startswith('files/') for name in names)
        assert 'SHA256SUMS' in names

    # 只导出清单时不应物化对象，避免无意义的完整下载
    from app.services import evidence_package_service
    def fail_materialize(*args, **kwargs):
        raise AssertionError('include_files=0 不应下载对象')
    monkeypatch.setattr(
        evidence_package_service, '_materialize_candidates', fail_materialize
    )
    manifest_only = client.get(
        f'/api/assets/{asset_id}/evidence-package?include_files=0',
        headers=auth_header,
    )
    assert manifest_only.status_code == 200
