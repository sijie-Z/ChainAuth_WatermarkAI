"""可选对象存储（MinIO/S3 兼容协议）

数据库中的 storage_path/file_path 同时兼容：
- 历史数据：本地绝对路径；
- 新数据：minio://bucket/key。

只有 STORAGE_BACKEND=minio 时新原件写入对象存储。缩略图、水印、
证据包和续传临时文件仍走本地目录，便于 PIL/矢量算法和 worker 共享。
"""
import hashlib
import os
import uuid
from contextlib import contextmanager
from urllib.parse import urlparse

from flask import Response, current_app, send_file, stream_with_context
from werkzeug.utils import secure_filename

from app.utils.paths import path_inside, uuid_filename

OBJECT_SCHEME = 'minio://'
DEFAULT_BUCKET = 'garden-assets'
_client = None
_bucket_ready = set()


def is_object_ref(value):
    return isinstance(value, str) and value.startswith(OBJECT_SCHEME)


def use_minio():
    return str(current_app.config.get('STORAGE_BACKEND', 'local')).lower() in (
        'minio', 's3', 'object'
    )


def _parse_ref(ref):
    parsed = urlparse(ref)
    if parsed.scheme != 'minio' or not parsed.netloc or not parsed.path.lstrip('/'):
        raise ValueError('invalid object reference')
    key = parsed.path.lstrip('/')
    parts = key.split('/')
    if any(part in ('', '.', '..') for part in parts):
        raise ValueError('invalid object key')
    return parsed.netloc, key


def _client_config():
    endpoint = str(current_app.config.get('MINIO_ENDPOINT', 'localhost:9000'))
    secure_value = current_app.config.get('MINIO_SECURE', False)
    secure = secure_value is True or str(secure_value).lower() in (
        '1', 'true', 'yes', 'on'
    )
    if endpoint.startswith('https://'):
        secure = True
    endpoint = endpoint.removeprefix('http://').removeprefix('https://')
    return endpoint.rstrip('/'), secure


def get_client():
    global _client
    if _client is None:
        try:
            from minio import Minio
        except ImportError as exc:
            raise RuntimeError(
                'STORAGE_BACKEND=minio 需要安装 minio Python SDK'
            ) from exc
        endpoint, secure = _client_config()
        _client = Minio(
            endpoint,
            access_key=current_app.config.get('MINIO_ACCESS_KEY', ''),
            secret_key=current_app.config.get('MINIO_SECRET_KEY', ''),
            secure=secure,
        )
    return _client


def ensure_bucket():
    bucket = current_app.config.get('MINIO_BUCKET', DEFAULT_BUCKET)
    if bucket in _bucket_ready:
        return bucket
    client = get_client()
    if not client.bucket_exists(bucket):
        try:
            client.make_bucket(bucket)
        except Exception as exc:
            # API 与 worker 首次启动可能同时建桶；已存在不是失败
            if getattr(exc, 'code', '') not in (
                'BucketAlreadyOwnedByYou', 'BucketAlreadyExists'
            ) and exc.__class__.__name__ not in (
                'BucketAlreadyOwnedByYou', 'BucketAlreadyExists'
            ):
                raise
            if not client.bucket_exists(bucket):
                raise
    _bucket_ready.add(bucket)
    return bucket


def init_object_storage(app):
    """启用对象存储时 fail fast，禁止静默退回本地。"""
    if str(app.config.get('STORAGE_BACKEND', 'local')).lower() not in (
        'minio', 's3', 'object'
    ):
        return
    with app.app_context():
        ensure_bucket()
    app.logger.info('对象存储已启用: %s', app.config.get('MINIO_BUCKET'))


def put_file(path, key, content_type=None):
    bucket = ensure_bucket()
    get_client().fput_object(
        bucket, key, path,
        content_type=content_type or 'application/octet-stream',
    )
    return f'{OBJECT_SCHEME}{bucket}/{key}'


def store_original(path, asset_id, extension='', kind='original'):
    """按后端配置保存原件；本地模式原样返回路径。"""
    if not use_minio():
        return path
    try:
        safe_asset_id = str(uuid.UUID(str(asset_id)))
    except (ValueError, TypeError, AttributeError) as exc:
        raise ValueError('invalid asset id for object storage') from exc
    ext = extension if str(extension).startswith('.') else f'.{extension}'
    if ext == '.':
        ext = ''
    # 扩展名来自已校验白名单，不能让用户文件名进入 object key
    key = f'assets/{safe_asset_id}/{kind}/{uuid_filename(ext)}'
    return put_file(path, key)


def _local_path(ref):
    return os.path.abspath(ref)


def _object_stat(ref):
    bucket, key = _parse_ref(ref)
    return get_client().stat_object(bucket, key)


def ref_exists(ref):
    if not ref:
        return False
    if not is_object_ref(ref):
        return os.path.isfile(_local_path(ref))
    try:
        _object_stat(ref)
        return True
    except Exception as exc:
        if isinstance(exc, FileNotFoundError) or getattr(exc, 'code', '') in (
            'NoSuchKey', 'NoSuchObject', 'NoSuchBucket'
        ):
            return False
        # 连接/权限故障不能伪装成“文件不存在”，让接口明确报错
        raise


def ref_size(ref):
    if not is_object_ref(ref):
        return os.path.getsize(_local_path(ref))
    return int(_object_stat(ref).size)


def open_object_stream(ref, offset=0, length=None):
    """立即打开对象流，供响应/台账提交前确认对象确实可读。"""
    bucket, key = _parse_ref(ref)
    kwargs = {}
    if offset:
        kwargs['offset'] = offset
    if length is not None:
        kwargs['length'] = length
    return get_client().get_object(bucket, key, **kwargs)


def _stream_open_response(response, chunk_size=1024 * 1024):
    try:
        while True:
            chunk = response.read(chunk_size)
            if not chunk:
                break
            yield chunk
    finally:
        response.close()
        response.release_conn()


def iter_ref(ref, offset=0, length=None, chunk_size=1024 * 1024):
    """逐块读取，调用方不需要了解本地/对象存储差异。"""
    if not is_object_ref(ref):
        with open(_local_path(ref), 'rb') as handle:
            if offset:
                handle.seek(offset)
            remaining = length
            while True:
                size = chunk_size if remaining is None else min(
                    chunk_size, remaining
                )
                if size <= 0:
                    break
                chunk = handle.read(size)
                if not chunk:
                    break
                yield chunk
                if remaining is not None:
                    remaining -= len(chunk)
                    if remaining <= 0:
                        break
        return

    response = open_object_stream(ref, offset, length)
    yield from _stream_open_response(response, chunk_size)


def hash_ref(ref):
    digest = hashlib.sha256()
    for chunk in iter_ref(ref):
        digest.update(chunk)
    return digest.hexdigest()


def delete_ref(ref):
    if not is_object_ref(ref):
        return False
    bucket, key = _parse_ref(ref)
    get_client().remove_object(bucket, key)
    return True


def delete_ref_quietly(ref):
    """清理新建对象失败时不覆盖原始数据库/上传异常。"""
    try:
        return delete_ref(ref)
    except Exception:
        current_app.logger.warning('对象存储清理失败: %s', ref, exc_info=True)
        return False


def _temp_dir():
    root = os.path.abspath(os.path.join(
        current_app.config.get('UPLOAD_FOLDER', './uploads'), 'object-cache'
    ))
    os.makedirs(root, exist_ok=True)
    return root


@contextmanager
def materialize_ref(ref, extension=''):
    """给 PIL/矢量算法提供本地文件；对象引用在退出时清理临时副本。"""
    if not is_object_ref(ref):
        yield _local_path(ref)
        return
    ext = extension if str(extension).startswith('.') else f'.{extension}'
    if ext == '.':
        ext = ''
    path = path_inside(_temp_dir(), uuid_filename(ext))
    try:
        with open(path, 'wb') as output:
            for chunk in iter_ref(ref):
                output.write(chunk)
        yield path
    finally:
        try:
            os.remove(path)
        except OSError:
            pass


def _download_headers(ref, download_name, as_attachment):
    disposition = 'attachment' if as_attachment else 'inline'
    name = secure_filename(download_name or 'download') or 'download'
    return {
        'Content-Disposition': f'{disposition}; filename="{name}"',
        'Content-Length': str(ref_size(ref)),
        'Accept-Ranges': 'bytes',
    }


def send_ref(ref, download_name, mimetype=None, as_attachment=True):
    """本地使用 send_file；对象存储在应用内鉴权后流式返回。"""
    if not is_object_ref(ref):
        return send_file(
            _local_path(ref),
            as_attachment=as_attachment,
            download_name=download_name,
            mimetype=mimetype,
            conditional=True,
        )
    object_response = open_object_stream(ref)
    response = Response(
        stream_with_context(_stream_open_response(object_response)),
        mimetype=mimetype or 'application/octet-stream',
        direct_passthrough=True,
        headers=_download_headers(ref, download_name, as_attachment),
    )
    return response


def send_ref_range(ref, download_name, mimetype=None):
    """对象预览的单段 Range 响应；本地仍由 send_file 处理。"""
    if not is_object_ref(ref):
        return send_file(
            _local_path(ref), download_name=download_name, mimetype=mimetype,
            conditional=True,
        )
    from flask import request
    size = ref_size(ref)
    start, end = 0, max(0, size - 1)
    status = 200
    range_header = request.headers.get('Range', '')
    if range_header.startswith('bytes='):
        value = range_header[6:].split(',', 1)[0]
        try:
            left, _, right = value.partition('-')
            if left:
                start = int(left)
                end = int(right) if right else size - 1
            else:
                suffix = int(right)
                start = max(0, size - suffix)
            if start < 0 or start >= size or end < start:
                raise ValueError
            end = min(end, size - 1)
            status = 206
        except (TypeError, ValueError):
            return Response(
                status=416,
                headers={'Content-Range': f'bytes */{size}'},
            )
    length = max(0, end - start + 1)
    headers = _download_headers(ref, download_name, False)
    headers['Content-Length'] = str(length)
    if status == 206:
        headers['Content-Range'] = f'bytes {start}-{end}/{size}'
    object_response = open_object_stream(ref, start, length)
    return Response(
        stream_with_context(_stream_open_response(object_response)),
        status=status,
        mimetype=mimetype or 'application/octet-stream',
        direct_passthrough=True,
        headers=headers,
    )
