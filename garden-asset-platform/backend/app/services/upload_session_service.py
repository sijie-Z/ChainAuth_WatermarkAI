"""断点续传会话管理

浏览器关闭后，页面内的会话 ID 会丢失。服务端保留会话记录，用户重新
选择同一文件时可以按文件名/大小认领未完成会话继续上传。

本模块负责：
- 会话临时目录的安全定位与清理；
- 过期会话回收（默认 48 小时，可在配置中调整）；
- 同会话并发分块写入的跨线程/跨进程互斥。
"""
import hashlib
import os
import re
import shutil
import threading
import time
import uuid
from contextlib import contextmanager
from datetime import datetime, timedelta

from flask import current_app
from sqlalchemy import update
from sqlalchemy.exc import OperationalError

from app.extensions import db
from app.models.extra import UploadSession
from app.utils.paths import path_inside

_UPLOAD_ID_RE = re.compile(r'^[0-9a-f]{32}$')
_FINGERPRINT_RE = re.compile(r'^[0-9a-f]{64}$')
FINGERPRINT_SAMPLE_SIZE = 64 * 1024
UPLOAD_LEASE_SECONDS = 120

_session_locks = {}
_session_locks_guard = threading.Lock()


def normalize_fingerprint(value):
    value = str(value or '').strip().lower()
    return value if _FINGERPRINT_RE.fullmatch(value) else None


def calculate_upload_fingerprint(path, size):
    """计算完整 SHA-256，防止同名同大小文件被拼接成错误资产。"""
    digest = hashlib.sha256()
    actual_size = 0
    with open(path, 'rb') as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b''):
            actual_size += len(chunk)
            digest.update(chunk)
    if actual_size != size:
        raise ValueError('file size changed while calculating fingerprint')
    return digest.hexdigest()


def calculate_prefix_hash(path, size=FINGERPRINT_SAMPLE_SIZE):
    with open(path, 'rb') as handle:
        return hashlib.sha256(handle.read(size)).hexdigest()


def lease_is_valid(session):
    return bool(
        session.lease_token
        and session.lease_expires_at
        and session.lease_expires_at > datetime.utcnow()
    )


def claim_upload_session(session, fingerprint=None):
    """为当前上传者签发短期写入租约，返回 (token, error)。

    已有有效租约时，只有同一个 token 能续租；其他页面收到冲突提示，
    不再向同一临时文件并发写入。完成/取消后租约清空。
    """
    fingerprint = normalize_fingerprint(fingerprint)
    if session.file_fingerprint and fingerprint != session.file_fingerprint:
        return None, '所选文件内容与未完成上传不一致，请选择原文件'
    if session.lease_expires_at and not lease_is_valid(session):
        session.lease_token = None
        session.lease_expires_at = None
    if lease_is_valid(session):
        session.lease_expires_at = datetime.utcnow() + timedelta(
            seconds=UPLOAD_LEASE_SECONDS
        )
        return session.lease_token, None
    session.lease_token = uuid.uuid4().hex
    session.lease_expires_at = datetime.utcnow() + timedelta(
        seconds=UPLOAD_LEASE_SECONDS
    )
    if fingerprint and not session.file_fingerprint:
        session.file_fingerprint = fingerprint
    return session.lease_token, None


def clear_upload_lease(session):
    session.lease_token = None
    session.lease_expires_at = None


def resumable_root():
    return os.path.abspath(os.path.join(
        current_app.config.get('UPLOAD_FOLDER', './uploads'),
        'resumable',
    ))


def session_dir(upload_id):
    """返回会话临时目录；upload_id 只接受 32 位十六进制。"""
    if not _UPLOAD_ID_RE.match(upload_id or ''):
        return None
    try:
        return path_inside(resumable_root(), upload_id)
    except ValueError:
        return None


def remove_upload_session_dir(upload_id):
    directory = session_dir(upload_id)
    if directory and os.path.isdir(directory):
        shutil.rmtree(directory, ignore_errors=True)
        return True
    return False


def remove_session_files(session):
    """删除会话的临时目录；目录名只由已校验的会话 ID 推导。"""
    return remove_upload_session_dir(getattr(session, 'id', ''))


def purge_stale_upload_sessions(ttl_hours=None, user_id=None):
    """把超时未更新的会话标记为 expired，并清理其临时文件。

    删除前先拿到会话锁并重新读取状态，避免把刚写入分块的会话误判过期。
    """
    ttl = max(1, int(
        ttl_hours
        if ttl_hours is not None
        else current_app.config.get('UPLOAD_SESSION_TTL_HOURS', 48)
    ))
    cutoff = datetime.utcnow() - timedelta(hours=ttl)
    query = UploadSession.query.filter(
        UploadSession.status == 'uploading',
        UploadSession.updated_at.isnot(None),
        UploadSession.updated_at < cutoff,
    )
    if user_id is not None:
        query = query.filter(UploadSession.user_id == user_id)
    candidates = query.all()

    expired_ids = []
    for candidate in candidates:
        try:
            with upload_session_lock(candidate.id):
                # 候选对象已在 identity map 中，必须强制从数据库重新读取，
                # 否则等待锁期间刚写入的分块会被旧时间戳误判为过期。
                db.session.expire_all()
                session = db.session.get(UploadSession, candidate.id)
                if (
                    not session
                    or session.status != 'uploading'
                    or not session.updated_at
                    or session.updated_at >= cutoff
                ):
                    continue
                session.status = 'expired'
                clear_upload_lease(session)
                db.session.commit()
                expired_ids.append(session.id)
        except TimeoutError:
            # 会话正在被写入，下一轮再处理
            continue

    cleaned = 0
    for upload_id in expired_ids:
        session = db.session.get(UploadSession, upload_id)
        if session and remove_session_files(session):
            cleaned += 1
    return {
        'expired': len(expired_ids),
        'cleaned': cleaned,
        'ttl_hours': ttl,
    }


def _thread_lock(upload_id):
    with _session_locks_guard:
        lock = _session_locks.get(upload_id)
        if lock is None:
            lock = threading.Lock()
            _session_locks[upload_id] = lock
        return lock


@contextmanager
def upload_session_lock(upload_id, timeout=10.0):
    """同一会话的分块/完成操作串行执行。

    进程内用线程锁；跨进程通过更新会话行取得数据库行锁，事务结束前
    其他 worker 的 UPDATE 会阻塞。整个持锁期间只做本地文件写入与提交，
    不涉及用户输入拼接路径。
    """
    lock = _thread_lock(upload_id)
    if not lock.acquire(timeout=timeout):
        raise TimeoutError('上传会话正忙，请稍后重试')
    try:
        for attempt in range(3):
            try:
                db.session.execute(
                    update(UploadSession)
                    .where(UploadSession.id == upload_id)
                    .values(updated_at=UploadSession.updated_at)
                )
                break
            except OperationalError as exc:
                db.session.rollback()
                message = str(exc).lower()
                if not any(word in message for word in ('locked', 'busy', 'timeout')):
                    raise
                if attempt == 2:
                    raise TimeoutError('上传会话正忙，请稍后重试') from exc
                time.sleep(0.05 * (attempt + 1))
        yield
    finally:
        lock.release()
