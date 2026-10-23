"""
命令行工具
"""
import time

import click
from flask.cli import with_appcontext
from app.extensions import db
from app.models import User, Garden


@click.command('create-admin')
@click.option('--username', default='admin', help='管理员用户名')
@click.option('--password', default='admin123', help='管理员密码')
@click.option('--email', default='admin@szgarden.cn', help='管理员邮箱')
@with_appcontext
def create_admin(username, password, email):
    """创建管理员账号"""
    if User.query.filter_by(username=username).first():
        click.echo(f'用户 {username} 已存在')
        return

    admin = User(
        username=username,
        email=email,
        role='admin',
        status='active'
    )
    admin.set_password(password)

    db.session.add(admin)
    db.session.commit()

    click.echo(f'管理员创建成功: {username}')


@click.command('init-gardens')
@with_appcontext
def init_gardens():
    """初始化园林数据"""
    gardens = [
        {'name': '拙政园', 'code': 'ZZY'},
        {'name': '留园', 'code': 'LY'},
        {'name': '狮子林', 'code': 'SZL'},
        {'name': '网师园', 'code': 'WSY'},
        {'name': '沧浪亭', 'code': 'CLT'},
        {'name': '耦园', 'code': 'OY'},
        {'name': '艺圃', 'code': 'YP'},
        {'name': '环秀山庄', 'code': 'HXSZ'},
        {'name': '怡园', 'code': 'YY'},
        {'name': '可园', 'code': 'KY'}
    ]

    for g in gardens:
        if not Garden.query.filter_by(code=g['code']).first():
            db.session.add(Garden(**g))

    db.session.commit()
    click.echo(f'创建了 {len(gardens)} 个园林数据')


@click.command('reset-password')
@click.argument('username')
@click.argument('new_password')
@with_appcontext
def reset_password(username, new_password):
    """重置用户密码"""
    user = User.query.filter_by(username=username).first()
    if not user:
        click.echo(f'用户 {username} 不存在')
        return

    user.set_password(new_password)
    db.session.commit()
    click.echo(f'密码已重置')


@click.group('tasks')
def tasks_group():
    """异步任务队列（水印/链上存证）"""


@tasks_group.command('run')
@click.option('--once', is_flag=True, help='处理完当前到期任务后退出')
@click.option('--interval', default=2.0, type=float, help='无任务时的轮询间隔（秒）')
@click.option('--limit', default=50, type=int, help='单轮最多处理任务数')
@click.option('--no-email', is_flag=True, help='不派发邮件通知')
@with_appcontext
def tasks_run(once, interval, limit, no_email):
    """启动队列 worker（生产环境用它替代进程内线程）"""
    from app.services import task_service
    from app.services.email_service import dispatch_pending_emails
    from app.services.webhook_service import dispatch_pending_webhooks

    click.echo('任务 worker 已启动，按 Ctrl+C 停止')
    worker_id = task_service.cli_worker_identity()
    processed_total = 0
    last_email_dispatch = 0.0
    while True:
        processed = 0
        while processed < max(1, limit):
            task = task_service.process_next(worker_id=worker_id)
            if not task:
                break
            processed += 1
            processed_total += 1
            click.echo(
                f'[{task.status}] {task.task_type} {task.id} '
                f'资产={task.asset_id or "-"} '
                f'尝试={task.attempts}/{task.max_attempts}'
            )
            if task.error_message:
                click.echo(f'  错误: {task.error_message}')
        task_service.record_heartbeat(
            worker_id, kind='cli', processed=processed_total
        )

        now = time.time()
        if not no_email and now - last_email_dispatch >= 60:
            result = dispatch_pending_emails()
            last_email_dispatch = now
            if result.get('sent') or result.get('failed'):
                click.echo(
                    f"邮件通知: 发送 {result.get('sent', 0)}, "
                    f"失败 {result.get('failed', 0)}"
                )
            webhook_result = dispatch_pending_webhooks()
            if webhook_result.get('sent') or webhook_result.get('failed'):
                click.echo(
                    f"Webhook 通知: 发送 {webhook_result.get('sent', 0)}, "
                    f"失败 {webhook_result.get('failed', 0)}"
                )

        if once:
            click.echo(f'本次处理 {processed} 个任务')
            break
        if not processed:
            time.sleep(max(0.5, interval))


@tasks_group.command('reconcile')
@click.option('--timeout', default=None, type=int, help='running 超时分钟数')
@with_appcontext
def tasks_reconcile(timeout):
    """把超时/崩溃遗留的 running 任务重新排队或判失败"""
    from app.services import task_service

    result = task_service.reconcile_stuck(timeout_minutes=timeout)
    click.echo(f"重新排队 {result['requeued']} 个，判失败 {result['failed']} 个")


@tasks_group.command('list')
@click.option('--status', default=None, help='queued/running/succeeded/failed/cancelled')
@click.option('--limit', default=20, type=int)
@with_appcontext
def tasks_list(status, limit):
    """查看任务队列"""
    from app.models import AsyncTask

    query = AsyncTask.query
    if status:
        query = query.filter(AsyncTask.status == status)
    tasks = query.order_by(AsyncTask.created_at.desc()).limit(max(1, limit)).all()
    if not tasks:
        click.echo('暂无任务')
        return
    for task in tasks:
        click.echo(
            f'{task.id}  {task.status:<9} {task.task_type:<22} '
            f'asset={task.asset_id or "-"} '
            f'attempts={task.attempts}/{task.max_attempts}'
        )
        if task.error_message:
            click.echo(f'  {task.error_message}')


@tasks_group.command('status')
@click.option('--check', is_flag=True, help='无在线 worker 或健康度异常时以非零状态退出')
@with_appcontext
def tasks_status(check):
    """查看队列健康度与 worker 心跳"""
    from app.services import task_service

    health = task_service.queue_health()
    counts = health['counts']
    click.echo(
        f"队列：排队 {counts['queued']}，处理中 {counts['running']}，"
        f"失败 {counts['failed']}，已完成 {counts['succeeded']}"
    )
    click.echo(
        f"健康度：{health['status']}；在线 worker {health['online_workers']}；"
        f"最老排队任务 {health['oldest_queued_seconds']} 秒"
    )
    for warning in health['warnings']:
        click.echo(f'  警告: {warning}')
    if not health['workers']:
        click.echo('暂无 worker 心跳（未启动 worker，或心跳尚未写入）')
    for worker in health['workers']:
        state = '在线' if worker['online'] else '离线'
        click.echo(
            f"  [{state}] {worker['worker_id']} "
            f"{worker['kind_label']} 已处理 {worker['processed']} 个，"
            f"{worker['last_seen_seconds']} 秒前心跳"
        )
    if check and (
        health['status'] == 'critical' or health['online_workers'] == 0
    ):
        raise click.exceptions.Exit(1)


@click.group('notifications')
def notifications_group():
    """通知渠道运维（邮件派发与测试）"""


@notifications_group.command('dispatch')
@click.option('--limit', default=20, type=int)
@with_appcontext
def notifications_dispatch(limit):
    """派发到期的邮件与 Webhook 通知"""
    from app.services.email_service import dispatch_pending_emails
    from app.services.webhook_service import dispatch_pending_webhooks

    result = dispatch_pending_emails(limit=limit)
    webhook_result = dispatch_pending_webhooks(limit=limit)
    if not result.get('mail_configured'):
        click.echo('SMTP 未配置（MAIL_ENABLED/MAIL_HOST），未发送邮件')
    else:
        click.echo(
            f"邮件：发送 {result['sent']}，跳过 {result['skipped']}，"
            f"失败 {result['failed']}，待重试 {result['retried']}"
        )
    if not webhook_result.get('configured'):
        click.echo('Webhook 未启用，未发送 Webhook')
    else:
        click.echo(
            f"Webhook：发送 {webhook_result['sent']}，跳过 {webhook_result['skipped']}，"
            f"失败 {webhook_result['failed']}，待重试 {webhook_result['retried']}"
        )


@notifications_group.command('test')
@click.argument('username')
@with_appcontext
def notifications_test(username):
    """给指定用户发送测试邮件"""
    from app.models import User
    from app.services.email_service import send_test_email

    user = User.query.filter_by(username=username).first()
    if not user:
        click.echo(f'用户 {username} 不存在')
        return
    try:
        send_test_email(user)
    except Exception as exc:
        click.echo(f'发送失败: {exc}')
        return
    click.echo(f'测试邮件已发送至 {user.email}')


@notifications_group.command('deliveries')
@click.option('--status', default=None, help='pending/sent/skipped/failed')
@click.option('--limit', default=20, type=int)
@with_appcontext
def notifications_deliveries(status, limit):
    """查看邮件投递记录"""
    from app.models import NotificationDelivery

    query = NotificationDelivery.query
    if status:
        query = query.filter_by(status=status)
    rows = query.order_by(NotificationDelivery.id.desc()).limit(max(1, limit)).all()
    if not rows:
        click.echo('暂无投递记录')
        return
    for row in rows:
        click.echo(
            f'{row.id} event={row.event_id} {row.status:<8} '
            f'attempts={row.attempts} {row.error_message or ""}'
        )


@click.group('backup')
def backup_group():
    """数据库备份与恢复"""


@backup_group.command('create')
@click.option('--output-dir', default=None, help='备份目录（默认 BACKUP_DIR）')
@with_appcontext
def backup_create(output_dir):
    """创建数据库备份"""
    from app.utils.backup import backup_database

    path = backup_database(output_dir=output_dir)
    click.echo(f'备份完成: {path}')


@backup_group.command('list')
@with_appcontext
def backup_list():
    """列出可用备份"""
    from app.utils.backup import list_backups

    rows = list_backups()
    if not rows:
        click.echo('暂无备份')
        return
    for row in rows:
        click.echo(
            f"{row['filename']}  {row['size'] / 1024 / 1024:.2f}MB  "
            f"{row['created_at']}"
        )


@backup_group.command('restore')
@click.argument('filename')
@click.option('--yes', is_flag=True, help='跳过确认（危险操作）')
@with_appcontext
def backup_restore(filename, yes):
    """恢复数据库（会覆盖当前数据库）"""
    import os
    from flask import current_app
    from app.utils.backup import restore_database

    path = filename
    if not os.path.isabs(path):
        path = os.path.join(
            current_app.config.get('BACKUP_DIR', './backups'), filename
        )
    if not os.path.isfile(path):
        click.echo(f'备份文件不存在: {path}')
        return
    if not yes and not click.confirm(
        f'将用 {path} 覆盖当前数据库，是否继续？', default=False
    ):
        click.echo('已取消')
        return
    safety = restore_database(path)
    click.echo(f'恢复完成: {path}')
    if safety:
        click.echo(f'恢复前备份: {safety}')


def register_commands(app):
    """注册命令"""
    app.cli.add_command(create_admin)
    app.cli.add_command(init_gardens)
    app.cli.add_command(reset_password)
    app.cli.add_command(tasks_group)
    app.cli.add_command(notifications_group)
    app.cli.add_command(backup_group)