"""存储巡检

平台文件分散在上传目录（原文件、指纹副本、举报文件）与水印目录
（水印派生文件、提取结果）。本模块只做只读盘点：

- storage_summary：各目录的文件数与占用；
- find_orphans：数据库未引用且超过最小年龄的文件。

孤儿文件不会自动删除。删除属于不可逆操作，应由管理员核对清单后
通过部署流程处理。
"""
import os
import time
from datetime import datetime, timedelta

from flask import current_app

from app.models.asset import Asset, AssetVersion
from app.models.fingerprint import DownloadFingerprint
from app.models.report import InfringementReport

SKIP_DIRS = {'__pycache__', '.git', 'node_modules', 'lost+found'}


def _roots():
    return {
        'uploads': os.path.abspath(
            current_app.config.get('UPLOAD_FOLDER', './uploads')
        ),
        'watermarks': os.path.abspath(
            current_app.config.get('WATERMARK_FOLDER', './watermarks')
        ),
        'extracted': os.path.abspath(
            current_app.config.get('EXTRACTED_FOLDER', './extracted')
        ),
    }


def _norm(path):
    if not path:
        return None
    return os.path.normcase(os.path.abspath(path))


def _referenced_paths():
    referenced = set()

    for asset in Asset.query.with_entities(
        Asset.storage_path, Asset.watermarked_path
    ):
        referenced.add(_norm(asset.storage_path))
        referenced.add(_norm(asset.watermarked_path))

    for version in AssetVersion.query.with_entities(AssetVersion.file_path):
        referenced.add(_norm(version.file_path))

    for row in DownloadFingerprint.query.with_entities(
        DownloadFingerprint.file_path
    ):
        referenced.add(_norm(row.file_path))

    for report in InfringementReport.query.with_entities(
        InfringementReport.suspect_file_path
    ):
        referenced.add(_norm(report.suspect_file_path))

    referenced.discard(None)
    return referenced


def _walk(root):
    if not root or not os.path.isdir(root):
        return
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [name for name in dirnames if name not in SKIP_DIRS]
        for name in filenames:
            if name.startswith('.'):
                continue
            yield os.path.join(dirpath, name)


def storage_summary():
    summary = []
    for key, root in _roots().items():
        files = 0
        total_bytes = 0
        if os.path.isdir(root):
            for path in _walk(root):
                try:
                    stat = os.stat(path)
                except OSError:
                    continue
                files += 1
                total_bytes += stat.st_size
        summary.append({
            'key': key,
            'path': root,
            'exists': os.path.isdir(root),
            'files': files,
            'bytes': total_bytes,
        })
    return {
        'roots': summary,
        'files': sum(item['files'] for item in summary),
        'bytes': sum(item['bytes'] for item in summary),
    }


_summary_cache = {'at': 0.0, 'value': None}


def storage_summary_cached(ttl_seconds=120):
    """仪表盘等高频入口使用的短缓存，避免每次请求都遍历大目录。"""
    now = time.time()
    if _summary_cache['value'] is not None and now - _summary_cache['at'] < ttl_seconds:
        return _summary_cache['value']
    value = storage_summary()
    _summary_cache['at'] = now
    _summary_cache['value'] = value
    return value


def find_orphans(min_age_hours=24, limit=200):
    """返回数据库未引用、且修改时间早于阈值的文件清单（不删除）。"""
    min_age_hours = max(0, int(min_age_hours or 0))
    limit = min(max(1, int(limit or 200)), 1000)
    cutoff = datetime.now() - timedelta(hours=min_age_hours)
    referenced = _referenced_paths()

    items = []
    total_bytes = 0
    count = 0
    for root_key, root in _roots().items():
        for path in _walk(root):
            if _norm(path) in referenced:
                continue
            try:
                stat = os.stat(path)
            except OSError:
                continue
            modified = datetime.fromtimestamp(stat.st_mtime)
            if modified > cutoff:
                continue
            count += 1
            total_bytes += stat.st_size
            if len(items) < limit:
                items.append({
                    'path': path,
                    'relative': os.path.relpath(path, root),
                    'root': root_key,
                    'bytes': stat.st_size,
                    'modified_at': modified.isoformat(),
                })

    items.sort(key=lambda item: item['bytes'], reverse=True)
    return {
        'min_age_hours': min_age_hours,
        'count': count,
        'total_bytes': total_bytes,
        'items': items,
        'truncated': count > len(items),
        'referenced_files': len(referenced),
    }
