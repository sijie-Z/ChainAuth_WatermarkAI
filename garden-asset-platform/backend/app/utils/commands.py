"""
命令行工具
"""
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


def register_commands(app):
    """注册命令"""
    app.cli.add_command(create_admin)
    app.cli.add_command(init_gardens)
    app.cli.add_command(reset_password)