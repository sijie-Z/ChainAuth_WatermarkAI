"""本地文件存储辅助

项目固定使用本地磁盘保存原件、历史版本与派生文件。
保留统一的读取/流式响应接口，使上传、下载、预览、版本、证据包、
水印与授权链路共享同一套路径处理逻辑，不引入外部对象存储依赖。
"""
import hashlib
import os
from contextlib import contextmanager

from flask import send_file


def is_object_ref(value):
    """兼容旧调用方：当前版本只接受本地路径。"""
    return False


def store_original(path, asset_id, extension='', kind='original'):
    """原件保留在上传流程生成的本地路径中。"""
    return path


def _local_path(ref):
    return os.path.abspath(ref)


def ref_exists(ref):
    return bool(ref) and os.path.isfile(_local_path(ref))


def ref_size(ref):
    return os.path.getsize(_local_path(ref))


def iter_ref(ref, offset=0, length=None, chunk_size=1024 * 1024):
    """逐块读取本地文件，支持预览 Range 和流式下载。"""
    with open(_local_path(ref), 'rb') as handle:
        if offset:
            handle.seek(offset)
        remaining = length
        while True:
            size = chunk_size if remaining is None else min(chunk_size, remaining)
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


def hash_ref(ref):
    digest = hashlib.sha256()
    for chunk in iter_ref(ref):
        digest.update(chunk)
    return digest.hexdigest()


def delete_ref(ref):
    """业务文件删除由资产生命周期管理，存储辅助层不直接删文件。"""
    return False


def delete_ref_quietly(ref):
    return False


@contextmanager
def materialize_ref(ref, extension=''):
    """为 PIL/矢量算法提供规范化本地路径，不创建额外副本。"""
    yield _local_path(ref)


def send_ref(ref, download_name, mimetype=None, as_attachment=True):
    return send_file(
        _local_path(ref),
        as_attachment=as_attachment,
        download_name=download_name,
        mimetype=mimetype,
        conditional=True,
    )


def send_ref_range(ref, download_name, mimetype=None):
    return send_file(
        _local_path(ref),
        download_name=download_name,
        mimetype=mimetype,
        conditional=True,
    )
