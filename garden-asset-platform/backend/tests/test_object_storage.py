"""本地文件存储辅助测试"""
import hashlib
import os

from app.services import object_storage


def test_local_file_read_hash_and_stream(app, tmp_path):
    payload = bytes(range(256)) * 1024
    source = tmp_path / 'source.bin'
    source.write_bytes(payload)
    with app.app_context():
        assert object_storage.store_original(
            str(source), '00000000-0000-0000-0000-000000000001', '.bin'
        ) == str(source)
        assert object_storage.ref_exists(str(source))
        assert object_storage.ref_size(str(source)) == len(payload)
        assert object_storage.hash_ref(str(source)) == hashlib.sha256(
            payload
        ).hexdigest()
        assert b''.join(object_storage.iter_ref(str(source), 10, 20)) == payload[10:30]

        with object_storage.materialize_ref(str(source)) as local_path:
            assert os.path.isfile(local_path)
            with open(local_path, 'rb') as handle:
                assert handle.read() == payload


def test_relative_local_paths_and_range_preview(app, tmp_path, monkeypatch):
    upload_dir = tmp_path / 'uploads'
    upload_dir.mkdir()
    source = upload_dir / 'model.gltf'
    source.write_bytes(b'{"asset":{"version":"2.0"}}')
    monkeypatch.chdir(tmp_path)
    with app.app_context(), app.test_request_context('/preview'):
        response = object_storage.send_ref_range(
            './uploads/model.gltf', 'model.gltf', mimetype='model/gltf+json'
        )
        assert response.status_code == 200
        assert response.headers['Content-Type'].startswith('model/gltf+json')
        assert b''.join(response.iter_encoded()) == b'{"asset":{"version":"2.0"}}'
