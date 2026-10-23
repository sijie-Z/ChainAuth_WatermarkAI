"""异步任务服务

把耗时操作（水印、链上存证）从请求线程搬到持久化队列：

- 入队时记录资产与文件版本，执行前再次校验版本，避免旧任务覆盖新文件；
- 领取使用条件 UPDATE，多个 worker 同时轮询也只会有一个执行；
- 可重试错误按退避时间自动重试，业务性错误直接失败；
- 进程崩溃留下的 running 任务由 reconcile_stuck 重新排队或判失败。
"""
import hashlib
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
from app.models.blockchain import Certificate
from app.models.report import InfringementReport
from app.models.task import AsyncTask, WorkerHeartbeat
from app.models.user import User
from app.services.blockchain_service import blockchain_service
from app.services.notification_service import add_notification_event
from app.services.watermark_service import WatermarkService

logger = logging.getLogger(__name__)

TASK_TYPES = ('watermark_embed', 'blockchain_register', 'infringement_patrol')
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


def enqueue_patrol_task(user, files):
    """批量巡检任务：文件已由接口保存到 reports/patrol 下。

    巡检不做自动重试（max_attempts=1），避免同一批文件重复生成线索。
    """
    task = AsyncTask(
        task_type='infringement_patrol',
        status='queued',
        user_id=user.id if user else None,
        payload={'files': files},
        attempts=0,
        max_attempts=1,
    )
    db.session.add(task)
    db.session.commit()
    return task


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


def _patrol_hash(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def _run_patrol(task, asset, user):
    """逐文件提取水印，匹配已发布资产并自动生成侵权线索。"""
    files = (task.payload or {}).get('files') or []
    results = []
    matched = 0
    errors = 0

    for item in files:
        path = item.get('path') or ''
        name = item.get('name') or os.path.basename(path)
        if not path or not os.path.isfile(path):
            results.append({'file': name, 'matched': False, 'message': '文件不存在'})
            errors += 1
            continue

        try:
            trace = WatermarkService.trace_from_file(path)
        except Exception as exc:
            logger.warning('巡检文件提取失败 %s: %s', name, exc)
            results.append({'file': name, 'matched': False, 'message': str(exc)[:200]})
            errors += 1
            continue

        watermark_id = trace.get('watermark_id') if trace.get('success') else None
        matched_asset = None
        if watermark_id:
            matched_asset = Asset.query.filter_by(
                watermark_id=watermark_id, status='published'
            ).first()

        if not matched_asset:
            # 未匹配的文件没有保留价值，及时清理，避免巡检目录膨胀
            try:
                os.remove(path)
            except OSError:
                pass
            results.append({
                'file': name,
                'matched': False,
                'watermark_id': watermark_id,
                'message': '未匹配平台已发布资产',
            })
            continue

        certificate = (
            Certificate.query.filter_by(
                certificate_id=matched_asset.certificate_id
            ).first()
            if matched_asset.certificate_id else None
        )
        try:
            file_hash = _patrol_hash(path)
            file_size = os.path.getsize(path)
        except OSError as exc:
            results.append({'file': name, 'matched': False, 'message': str(exc)[:200]})
            errors += 1
            continue

        report = InfringementReport(
            asset_id=matched_asset.id,
            reporter_id=user.id if user else None,
            reporter_name='系统巡检',
            contact=user.email if user else None,
            source_url=item.get('source_url') or None,
            description='批量巡检自动匹配，请核实是否授权使用',
            suspect_filename=name[:255],
            suspect_file_path=path,
            suspect_file_hash=file_hash,
            suspect_file_size=file_size,
            watermark_id=watermark_id,
            certificate_id=(
                certificate.certificate_id if certificate
                else matched_asset.certificate_id
            ),
            trace_verified=True,
            status='pending',
        )
        db.session.add(report)
        db.session.flush()

        owner_id = (
            matched_asset.owner_id
            or matched_asset.creator_id
            or matched_asset.uploader_id
        )
        add_notification_event(
            owner_id,
            'infringement_reported',
            f'巡检发现疑似侵权：{matched_asset.title}',
            f'线索编号 {report.report_code}，管理员会跟进核实。',
            f'/assets/{matched_asset.id}?tab=evidence',
        )

        matched += 1
        results.append({
            'file': name,
            'matched': True,
            'asset_id': matched_asset.id,
            'asset_code': matched_asset.asset_code,
            'asset_title': matched_asset.title,
            'watermark_id': watermark_id,
            'report_code': report.report_code,
        })

    return {
        'total': len(files),
        'matched': matched,
        'errors': errors,
        'items': results,
    }


HANDLERS = {
    'watermark_embed': _run_watermark,
    'blockchain_register': _run_blockchain,
    'infringement_patrol': _run_patrol,
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
        # 巡检任务不绑定单个资产；水印/存证任务必须找到资产
        if task.task_type in ('watermark_embed', 'blockchain_register') and not asset:
            raise TaskFailure('资产不存在', retryable=False)
        if asset and asset.status == 'deleted':
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


def cli_worker_identity():
    """独立 `flask tasks run` 进程的稳定标识。"""
    return f'cli:{socket.gethostname()}:{os.getpid()}'


def _heartbeat_stale_seconds():
    return max(15, int(current_app.config.get('TASK_WORKER_STALE_SECONDS', 90)))


def record_heartbeat(worker_id, kind='thread', processed=0):
    """写入或刷新 worker 心跳；失败不打断任务执行。"""
    now = datetime.utcnow()
    try:
        row = WorkerHeartbeat.query.filter_by(worker_id=worker_id).first()
        if row is None:
            row = WorkerHeartbeat(
                worker_id=worker_id,
                kind=kind,
                hostname=socket.gethostname(),
                pid=os.getpid(),
                processed=max(0, processed),
                started_at=now,
                last_seen_at=now,
            )
            db.session.add(row)
        else:
            row.kind = kind
            row.processed = max(0, processed)
            row.last_seen_at = now
        db.session.commit()
        return row
    except Exception:
        logger.exception('worker 心跳写入失败')
        try:
            db.session.rollback()
        except Exception:
            pass
        return None


def worker_status(stale_seconds=None):
    """返回近期 worker 列表与在线数量。"""
    if stale_seconds is None:
        stale_seconds = _heartbeat_stale_seconds()
    now = datetime.utcnow()
    rows = WorkerHeartbeat.query.order_by(
        WorkerHeartbeat.last_seen_at.desc()
    ).limit(20).all()
    workers = [row.to_dict(stale_seconds=stale_seconds, now=now) for row in rows]
    online = [worker for worker in workers if worker['online']]
    return {
        'workers': workers,
        'online_count': len(online),
        'stale_after_seconds': stale_seconds,
    }


def queue_health():
    """队列积压、worker 在线情况与异常告警。"""
    now = datetime.utcnow()
    counts = task_counts()
    workers = worker_status()
    backlog_threshold = max(1, int(current_app.config.get('TASK_BACKLOG_THRESHOLD', 50)))
    stuck_minutes = max(1, int(current_app.config.get('TASK_STUCK_TIMEOUT_MINUTES', 15)))
    stale_cutoff = now - timedelta(minutes=stuck_minutes)

    oldest_queued = db.session.query(
        db.func.min(AsyncTask.created_at)
    ).filter(AsyncTask.status == 'queued').scalar()
    oldest_queued_seconds = (
        max(0, int((now - oldest_queued).total_seconds())) if oldest_queued else 0
    )
    stale_running = AsyncTask.query.filter(
        AsyncTask.status == 'running',
        AsyncTask.started_at.isnot(None),
        AsyncTask.started_at < stale_cutoff,
    ).count()

    warnings = []
    status = 'ok'
    if counts['queued'] >= backlog_threshold:
        warnings.append(
            f"队列积压 {counts['queued']} 个任务，超过阈值 {backlog_threshold}"
        )
        status = 'warning'
    if counts['queued'] and workers['online_count'] == 0:
        warnings.append(
            '队列有任务但没有在线 worker，请启动 worker 服务或运行 flask tasks run'
        )
        status = 'warning'
    if stale_running:
        warnings.append(
            f'{stale_running} 个任务处理超时，worker 进程可能已中断'
        )
        status = 'critical'
    if counts['running'] and workers['online_count'] == 0:
        warnings.append('有任务处于处理中但没有在线 worker，可能在等待超时回收')
        status = 'critical'

    return {
        'status': status,
        'warnings': warnings,
        'counts': counts,
        'workers': workers['workers'],
        'online_workers': workers['online_count'],
        'oldest_queued_seconds': oldest_queued_seconds,
        'stale_running': stale_running,
        'backlog_threshold': backlog_threshold,
        'stuck_timeout_minutes': stuck_minutes,
        'stale_after_seconds': workers['stale_after_seconds'],
        'checked_at': now.isoformat(),
    }


def _worker_loop(app):
    interval = float(app.config.get('TASK_WORKER_POLL_INTERVAL', 1.0))
    reconcile_every = 60
    heartbeat_every = 10
    ticks = 0
    processed_total = 0
    last_heartbeat = 0.0
    worker_id = _worker_identity()
    while not _worker_stop.is_set():
        try:
            with app.app_context():
                processed_total += process_pending(limit=5)
                ticks += 1
                if time.monotonic() - last_heartbeat >= heartbeat_every:
                    record_heartbeat(
                        worker_id, kind='thread', processed=processed_total
                    )
                    last_heartbeat = time.monotonic()
                if ticks >= reconcile_every:
                    ticks = 0
                    reconcile_stuck()
                    if not app.config.get('SCHEDULER_ENABLED', False):
                        try:
                            from app.services.email_service import dispatch_pending_emails
                            dispatch_pending_emails()
                        except Exception:
                            logger.exception('邮件通知派发失败')
                        try:
                            from app.services.webhook_service import dispatch_pending_webhooks
                            dispatch_pending_webhooks()
                        except Exception:
                            logger.exception('Webhook 通知派发失败')
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
