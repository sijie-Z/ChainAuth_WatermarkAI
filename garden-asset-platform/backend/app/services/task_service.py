"""异步任务服务

把耗时操作（水印、链上存证）从请求线程搬到持久化队列：

- 入队时记录资产与文件版本，执行前再次校验版本，避免旧任务覆盖新文件；
- 领取使用条件 UPDATE，多个 worker 同时轮询也只会有一个执行；
- 可重试错误按退避时间自动重试，业务性错误直接失败；
- 进程崩溃留下的 running 任务由 reconcile_stuck 重新排队或判失败。
"""
import logging
import os
import socket
import threading
import time
from datetime import datetime, timedelta

from flask import current_app
from sqlalchemy import or_, update

from app.extensions import db
from app.models.asset import Asset, AssetVersion
from app.models.task import AsyncTask
from app.models.user import User
from app.services.blockchain_service import blockchain_service
from app.services.notification_service import add_notification_event
from app.services.watermark_service import WatermarkService

logger = logging.getLogger(__name__)

TASK_TYPES = ('watermark_embed', 'blockchain_register')
ACTIVE_STATUSES = ('queued', 'running')

_worker_thread = None
_worker_stop = threading.Event()


class TaskFailure(Exception):
    """任务执行失败；retryable 决定是否进入自动重试。"""

    def __init__(self, message, retryable=False):
        super().__init__(message)
        self.message = message
        self.retryable = retryable


def current_version(asset):
    if not asset:
        return None
    return AssetVersion.query.filter_by(asset_id=asset.id).order_by(
        AssetVersion.version_no.desc()
    ).first()


def _worker_identity():
    return f'{socket.gethostname()}:{os.getpid()}:{threading.get_ident()}'


def _asset_uploader_id(asset):
    return asset.uploader_id or asset.owner_id or asset.creator_id


def _notify_task(task, asset, success):
    if not asset:
        return
    user_id = _asset_uploader_id(asset)
    if not user_id:
        return
    label = '水印嵌入' if task.task_type == 'watermark_embed' else '链上存证'
    if success:
        add_notification_event(
            user_id,
            'asset_task_succeeded',
            f'{label}完成：{asset.title}',
            '后台任务已完成，可刷新资产详情查看结果。',
            f'/assets/{asset.id}',
        )
    else:
        add_notification_event(
            user_id,
            'asset_task_failed',
            f'{label}失败：{asset.title}',
            (task.error_message or '请稍后重试')[:200],
            f'/assets/{asset.id}',
        )


def enqueue_task(task_type, asset, user=None, payload=None):
    """入队一个任务；同一资产同一版本的同类活跃任务会复用。"""
    if task_type not in TASK_TYPES:
        raise ValueError(f'不支持的任务类型: {task_type}')
    if not asset:
        raise ValueError('任务缺少资产')

    version = current_version(asset)
    version_id = version.id if version else None
    dedupe_key = f'{task_type}:{asset.id}:{version_id or asset.file_hash or "none"}'

    existing = AsyncTask.query.filter(
        AsyncTask.dedupe_key == dedupe_key,
        AsyncTask.status.in_(ACTIVE_STATUSES),
    ).order_by(AsyncTask.id.desc()).first()
    if existing:
        return existing, False

    max_attempts = int(current_app.config.get('TASK_MAX_ATTEMPTS', 3))
    task = AsyncTask(
        task_type=task_type,
        status='queued',
        asset_id=asset.id,
        user_id=user.id if user else None,
        version_id=version_id,
        payload=payload or {},
        attempts=0,
        max_attempts=max(1, max_attempts),
        dedupe_key=dedupe_key,
    )

    if task_type == 'watermark_embed':
        asset.watermark_status = 'pending'
    else:
        asset.chain_status = 'pending'

    db.session.add(task)
    db.session.commit()
    return task, True


def _run_watermark(task, asset, user):
    result = WatermarkService.embed_watermark(asset, user)
    if result.get('success'):
        return {
            'watermark_id': result.get('watermark_id'),
            'watermarked_path': result.get('watermarked_path'),
            'psnr': result.get('psnr'),
        }

    message = result.get('message') or '水印嵌入失败'
    if '已嵌入水印' in message:
        return {
            'watermark_id': asset.watermark_id,
            'watermarked_path': asset.watermarked_path,
            'already': True,
        }
    # 算法失败通常是确定性的（尺寸、格式、文件损坏），重试不会改变结果
    raise TaskFailure(message, retryable=False)


def _run_blockchain(task, asset, user):
    if asset.watermark_status not in ('embedded', 'verified'):
        raise TaskFailure('上链前需先完成水印嵌入', retryable=False)

    result = blockchain_service.register_asset(asset, user)
    if result.get('success'):
        return {
            'tx_hash': result.get('tx_hash'),
            'certificate_id': result.get('certificate_id'),
            'block_number': result.get('block_number'),
            'simulated': result.get('simulated'),
            'already': result.get('already', False),
        }
    raise TaskFailure(result.get('message') or '链上存证失败', retryable=True)


HANDLERS = {
    'watermark_embed': _run_watermark,
    'blockchain_register': _run_blockchain,
}


def _mark_asset_failed(task, asset):
    if not asset:
        return
    version = current_version(asset)
    if task.version_id and (not version or version.id != task.version_id):
        return
    if task.task_type == 'watermark_embed':
        asset.watermark_status = 'failed'
    elif task.task_type == 'blockchain_register':
        asset.chain_status = 'failed'


def _finish(task, asset, error=None, retryable=False):
    """写入任务终态或重试状态。"""
    now = datetime.utcnow()
    if error is None:
        task.status = 'succeeded'
        task.progress = 100
        task.error_message = None
        task.finished_at = now
        task.next_attempt_at = None
        _notify_task(task, asset, True)
    else:
        task.error_message = error[:2000] if error else '任务失败'
        if retryable and (task.attempts or 0) < (task.max_attempts or 1):
            delay = min(5 * (task.attempts or 1), 60)
            task.status = 'queued'
            task.next_attempt_at = now + timedelta(seconds=delay)
            task.finished_at = None
            task.worker_id = None
        else:
            task.status = 'failed'
            task.finished_at = now
            task.next_attempt_at = None
            _mark_asset_failed(task, asset)
            _notify_task(task, asset, False)

    db.session.commit()


def run_claimed_task(task):
    """执行一个已领取（status=running）的任务。"""
    asset = Asset.query.get(task.asset_id) if task.asset_id else None
    user = User.query.get(task.user_id) if task.user_id else None
    handler = HANDLERS.get(task.task_type)

    try:
        if not handler:
            raise TaskFailure(f'未知任务类型: {task.task_type}', retryable=False)
        if not asset:
            raise TaskFailure('资产不存在', retryable=False)
        if asset.status == 'deleted':
            raise TaskFailure('资产已删除，任务取消', retryable=False)

        version = current_version(asset)
        if task.version_id and (not version or version.id != task.version_id):
            raise TaskFailure('处理期间文件已更新，请对当前版本重新提交', retryable=False)

        task.progress = 30
        db.session.commit()

        result = handler(task, asset, user)
        task.result = result
        _finish(task, asset)
        logger.info('任务完成: %s %s', task.task_type, task.id)
        return task
    except TaskFailure as exc:
        db.session.rollback()
        task = db.session.get(AsyncTask, task.id)
        asset = Asset.query.get(task.asset_id) if task and task.asset_id else None
        if task:
            _finish(task, asset, exc.message, retryable=exc.retryable)
        logger.warning('任务失败: %s %s %s', task.id if task else '?', exc.message,
                       '将重试' if exc.retryable else '不再重试')
        return task
    except Exception as exc:  # 未预期异常按可重试处理
        logger.exception('任务执行异常: %s', task.id)
        db.session.rollback()
        task = db.session.get(AsyncTask, task.id)
        asset = Asset.query.get(task.asset_id) if task and task.asset_id else None
        if task:
            _finish(task, asset, f'任务执行异常: {exc}', retryable=True)
        return task


def process_next(worker_id=None):
    """领取并执行一个到期任务；没有可执行任务时返回 None。"""
    now = datetime.utcnow()
    task = AsyncTask.query.filter(
        AsyncTask.status == 'queued',
        or_(AsyncTask.next_attempt_at.is_(None), AsyncTask.next_attempt_at <= now),
    ).order_by(AsyncTask.created_at.asc(), AsyncTask.id.asc()).first()
    if not task:
        return None

    claimed = db.session.execute(
        update(AsyncTask)
        .where(AsyncTask.id == task.id, AsyncTask.status == 'queued')
        .values(
            status='running',
            started_at=now,
            updated_at=now,
            attempts=AsyncTask.attempts + 1,
            progress=10,
            worker_id=worker_id or _worker_identity(),
            next_attempt_at=None,
        )
    )
    db.session.commit()
    if claimed.rowcount != 1:
        return None

    task = db.session.get(AsyncTask, task.id)
    return run_claimed_task(task)


def process_pending(limit=20):
    """连续处理到期任务，返回实际处理条数。"""
    processed = 0
    for _ in range(max(0, limit)):
        task = process_next()
        if not task:
            break
        processed += 1
    return processed


def retry_task(task, reset_attempts=True):
    if not task or task.status not in ('failed', 'cancelled'):
        return False
    if task.asset_id:
        asset = Asset.query.get(task.asset_id)
        if asset:
            if task.task_type == 'watermark_embed':
                asset.watermark_status = 'pending'
            else:
                asset.chain_status = 'pending'
    task.status = 'queued'
    task.error_message = None
    task.next_attempt_at = None
    task.finished_at = None
    task.worker_id = None
    if reset_attempts:
        task.attempts = 0
    db.session.commit()
    return True


def cancel_task(task):
    if not task or task.status != 'queued':
        return False
    task.status = 'cancelled'
    task.finished_at = datetime.utcnow()
    if task.asset_id:
        asset = Asset.query.get(task.asset_id)
        if asset:
            if task.task_type == 'watermark_embed':
                asset.watermark_status = 'none'
            else:
                asset.chain_status = 'none'
    db.session.commit()
    return True


def reconcile_stuck(timeout_minutes=None):
    """处理进程崩溃或超时遗留的 running 任务。"""
    if timeout_minutes is None:
        timeout_minutes = int(current_app.config.get('TASK_STUCK_TIMEOUT_MINUTES', 15))
    cutoff = datetime.utcnow() - timedelta(minutes=max(1, timeout_minutes))

    stuck = AsyncTask.query.filter(
        AsyncTask.status == 'running',
        AsyncTask.started_at.isnot(None),
        AsyncTask.started_at < cutoff,
    ).all()

    requeued = failed = 0
    for task in stuck:
        asset = Asset.query.get(task.asset_id) if task.asset_id else None
        if (task.attempts or 0) < (task.max_attempts or 1):
            task.status = 'queued'
            task.error_message = '任务执行超时，已重新排队'
            task.next_attempt_at = None
            task.worker_id = None
            requeued += 1
        else:
            task.status = 'failed'
            task.error_message = '任务执行超时且已超过最大重试次数'
            task.finished_at = datetime.utcnow()
            _mark_asset_failed(task, asset)
            failed += 1
    if stuck:
        db.session.commit()
        logger.info('任务对账: 重新排队 %s，判失败 %s', requeued, failed)
    return {'requeued': requeued, 'failed': failed}


def task_counts():
    rows = db.session.query(
        AsyncTask.status, db.func.count(AsyncTask.id)
    ).group_by(AsyncTask.status).all()
    counts = {status: count for status, count in rows}
    return {
        'queued': counts.get('queued', 0),
        'running': counts.get('running', 0),
        'succeeded': counts.get('succeeded', 0),
        'failed': counts.get('failed', 0),
        'cancelled': counts.get('cancelled', 0),
        'total': sum(counts.values()),
    }


def _worker_loop(app):
    interval = float(app.config.get('TASK_WORKER_POLL_INTERVAL', 1.0))
    reconcile_every = 60
    ticks = 0
    while not _worker_stop.is_set():
        try:
            with app.app_context():
                process_pending(limit=5)
                ticks += 1
                if ticks >= reconcile_every:
                    ticks = 0
                    reconcile_stuck()
                db.session.remove()
        except Exception:
            logger.exception('异步任务 worker 轮询异常')
            try:
                db.session.rollback()
                db.session.remove()
            except Exception:
                pass
        _worker_stop.wait(interval)


def start_worker(app):
    """启动进程内 worker；测试与显式关闭时跳过。

    任务领取使用条件 UPDATE，因此即使 debug reloader 或多 gunicorn worker
    同时启动多个轮询线程，也不会重复执行同一个任务。生产环境建议关闭
    进程内 worker，由独立的 `flask tasks run` 服务执行。
    """
    global _worker_thread
    if app.config.get('TESTING') or not app.config.get('TASK_WORKER_ENABLED', False):
        return None
    if _worker_thread and _worker_thread.is_alive():
        return _worker_thread

    _worker_stop.clear()
    _worker_thread = threading.Thread(
        target=_worker_loop,
        args=(app,),
        daemon=True,
        name='async-task-worker',
    )
    _worker_thread.start()
    app.logger.info('异步任务 worker 已启动')
    return _worker_thread


def stop_worker():
    _worker_stop.set()
    thread = _worker_thread
    if thread and thread.is_alive():
        thread.join(timeout=5)
