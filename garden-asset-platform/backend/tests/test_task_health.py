"""worker 心跳与队列健康度测试

覆盖：心跳写入/刷新、离线判定、无 worker 消费告警、积压阈值、
超时 running 任务告警、健康度接口权限与 CLI 状态输出。
"""
from datetime import datetime, timedelta

from app.extensions import db
from app.models.task import AsyncTask, WorkerHeartbeat
from app.services import task_service


def make_task(status='queued', **kwargs):
    task = AsyncTask(
        task_type='watermark_embed',
        status=status,
        payload={},
        **kwargs
    )
    db.session.add(task)
    db.session.commit()
    return task


def test_heartbeat_marks_online_then_stale(app):
    with app.app_context():
        task_service.record_heartbeat('worker-a', kind='cli', processed=7)
        status = task_service.worker_status()
        assert status['online_count'] == 1
        worker = status['workers'][0]
        assert worker['worker_id'] == 'worker-a'
        assert worker['processed'] == 7
        assert worker['online'] is True

        # 再次心跳刷新同一行，而不是新增
        task_service.record_heartbeat('worker-a', kind='cli', processed=9)
        assert WorkerHeartbeat.query.count() == 1
        assert WorkerHeartbeat.query.first().processed == 9

        row = WorkerHeartbeat.query.filter_by(worker_id='worker-a').first()
        row.last_seen_at = datetime.utcnow() - timedelta(minutes=5)
        db.session.commit()

        status = task_service.worker_status(stale_seconds=90)
        assert status['online_count'] == 0
        assert status['workers'][0]['online'] is False
        assert status['workers'][0]['last_seen_seconds'] >= 290


def test_queue_health_warns_when_queue_has_no_worker(app):
    with app.app_context():
        make_task()

        health = task_service.queue_health()
        assert health['status'] == 'warning'
        assert health['online_workers'] == 0
        assert any('没有在线 worker' in item for item in health['warnings'])
        assert health['oldest_queued_seconds'] >= 0

        task_service.record_heartbeat('worker-b')
        health = task_service.queue_health()
        assert health['status'] == 'ok'
        assert health['warnings'] == []
        assert health['online_workers'] == 1


def test_queue_health_warns_on_backlog_threshold(app):
    with app.app_context():
        app.config['TASK_BACKLOG_THRESHOLD'] = 2
        make_task()
        make_task()
        task_service.record_heartbeat('worker-c')

        health = task_service.queue_health()
        assert health['status'] == 'warning'
        assert health['counts']['queued'] == 2
        assert any('积压' in item for item in health['warnings'])


def test_queue_health_critical_for_stale_running_task(app):
    with app.app_context():
        task_service.record_heartbeat('worker-d')
        make_task(
            status='running',
            started_at=datetime.utcnow() - timedelta(hours=1),
            worker_id='worker-dead',
            attempts=1,
        )

        health = task_service.queue_health()
        assert health['status'] == 'critical'
        assert health['stale_running'] == 1
        assert any('超时' in item for item in health['warnings'])


def test_task_health_endpoint_permissions(client, admin_header, auth_header):
    response = client.get('/api/tasks/health')
    assert response.status_code == 401

    forbidden = client.get('/api/tasks/health', headers=auth_header)
    assert forbidden.status_code == 403

    response = client.get('/api/tasks/health', headers=admin_header)
    assert response.status_code == 200
    data = response.get_json()['data']
    for key in (
        'status', 'warnings', 'counts', 'workers', 'online_workers',
        'oldest_queued_seconds', 'stale_running', 'backlog_threshold',
        'worker_enabled',
    ):
        assert key in data


def test_tasks_status_cli_reports_worker_and_queue(app, runner):
    with app.app_context():
        make_task()
        task_service.record_heartbeat('cli:test-host:1', kind='cli', processed=3)

    result = runner.invoke(args=['tasks', 'status'])
    assert result.exit_code == 0, result.output
    assert '在线 worker 1' in result.output
    assert 'cli:test-host:1' in result.output
    assert '排队 1' in result.output


def test_tasks_status_check_exit_code(app, runner):
    with app.app_context():
        make_task()

    unhealthy = runner.invoke(args=['tasks', 'status', '--check'])
    assert unhealthy.exit_code == 1, unhealthy.output

    with app.app_context():
        task_service.record_heartbeat('cli:check:1', kind='cli')

    healthy = runner.invoke(args=['tasks', 'status', '--check'])
    assert healthy.exit_code == 0, healthy.output
    assert '在线 worker 1' in healthy.output
