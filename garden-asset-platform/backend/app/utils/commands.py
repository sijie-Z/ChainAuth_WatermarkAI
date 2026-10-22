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

    click.echo('任务 worker 已启动，按 Ctrl+C 停止')
    last_email_dispatch = 0.0
    while True:
        processed = 0
        while processed < max(1, limit):
            task = task_service.process_next(worker_id='cli')
            if not task:
                break
            processed += 1
            click.echo(
                f'[{task.status}] {task.task_type} {task.id} '
                f'资产={task.asset_id or "-"} '
                f'尝试={task.attempts}/{task.max_attempts}'
            )
            if task.error_message:
                click.echo(f'  错误: {task.error_message}')

        now = time.time()
        if not no_email and now - last_email_dispatch >= 60:
            result = dispatch_pending_emails()
            last_email_dispatch = now
            if result.get('sent') or result.get('failed'):
                click.echo(
                    f"邮件通知: 发送 {result.get('sent', 0)}, "
                    f"失败 {result.get('failed', 0)}"
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


@click.group('notifications')
def notifications_group():
    """通知渠道运维（邮件派发与测试）"""


@notifications_group.command('dispatch')
@click.option('--limit', default=20, type=int)
@with_appcontext
def notifications_dispatch(limit):
    """派发到期的邮件通知"""
    from app.services.email_service import dispatch_pending_emails

    result = dispatch_pending_emails(limit=limit)
    if not result.get('mail_configured'):
        click.echo('SMTP 未配置（MAIL_ENABLED/MAIL_HOST），未发送邮件')
        return
    click.echo(
        f"发送 {result['sent']}，跳过 {result['skipped']}，"
        f"失败 {result['failed']}，待重试 {result['retried']}"
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


def register_commands(app):
    """注册命令"""
    app.cli.add_command(create_admin)
    app.cli.add_command(init_gardens)
    app.cli.add_command(reset_password)
    app.cli.add_command(tasks_group)
    app.cli.add_command(notifications_group)