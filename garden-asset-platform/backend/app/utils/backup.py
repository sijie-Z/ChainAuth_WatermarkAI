"""
数据库备份工具
"""
import os
import subprocess
from datetime import datetime
from flask import current_app


def backup_database(output_dir='./backups'):
    """备份数据库"""
    os.makedirs(output_dir, exist_ok=True)

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    db_url = current_app.config.get('SQLALCHEMY_DATABASE_URI', '')
    suffix = 'sql' if db_url.startswith('postgresql') else 'db'
    backup_file = os.path.join(output_dir, f'backup_{timestamp}.{suffix}')

    if db_url.startswith('postgresql'):
        # PostgreSQL备份
        # postgresql://user:password@host:port/database
        parts = db_url.replace('postgresql://', '').split('@')
        user_pass = parts[0].split(':')
        host_port_db = parts[1].split('/')

        user = user_pass[0]
        password = user_pass[1] if len(user_pass) > 1 else ''
        host_port = host_port_db[0].split(':')
        host = host_port[0]
        port = host_port[1] if len(host_port) > 1 else '5432'
        database = host_port_db[1]

        env = os.environ.copy()
        env['PGPASSWORD'] = password

        cmd = [
            'pg_dump',
            '-h', host,
            '-p', port,
            '-U', user,
            '-d', database,
            '-f', backup_file
        ]

        subprocess.run(cmd, env=env, check=True)

    elif db_url.startswith('sqlite'):
        # Flask-SQLAlchemy 会把相对 SQLite 路径解析到 instance 目录
        from app.extensions import db
        db_path = db.engine.url.database
        if not db_path or db_path == ':memory:':
            raise ValueError('SQLite 内存数据库无法备份')
        if not os.path.isabs(db_path):
            db_path = os.path.join(current_app.instance_path, db_path)
        import shutil
        shutil.copy(db_path, backup_file)

    else:
        raise ValueError(f'不支持的数据库类型: {db_url}')

    return backup_file


def restore_database(backup_file):
    """恢复数据库"""
    db_url = current_app.config.get('SQLALCHEMY_DATABASE_URI', '')

    if db_url.startswith('postgresql'):
        parts = db_url.replace('postgresql://', '').split('@')
        user_pass = parts[0].split(':')
        host_port_db = parts[1].split('/')

        user = user_pass[0]
        password = user_pass[1] if len(user_pass) > 1 else ''
        host_port = host_port_db[0].split(':')
        host = host_port[0]
        port = host_port[1] if len(host_port) > 1 else '5432'
        database = host_port_db[1]

        env = os.environ.copy()
        env['PGPASSWORD'] = password

        cmd = [
            'psql',
            '-h', host,
            '-p', port,
            '-U', user,
            '-d', database,
            '-f', backup_file
        ]

        subprocess.run(cmd, env=env, check=True)

    elif db_url.startswith('sqlite'):
        from app.extensions import db
        db_path = db.engine.url.database
        if not db_path or db_path == ':memory:':
            raise ValueError('SQLite 内存数据库无法恢复')
        if not os.path.isabs(db_path):
            db_path = os.path.join(current_app.instance_path, db_path)
        import shutil
        shutil.copy(backup_file, db_path)

    else:
        raise ValueError(f'不支持的数据库类型')


def list_backups(backup_dir='./backups'):
    """列出所有备份"""
    if not os.path.exists(backup_dir):
        return []

    backups = []
    for f in os.listdir(backup_dir):
        if f.startswith('backup_') and f.endswith('.sql'):
            path = os.path.join(backup_dir, f)
            stat = os.stat(path)
            backups.append({
                'filename': f,
                'path': path,
                'size': stat.st_size,
                'created_at': datetime.fromtimestamp(stat.st_mtime).isoformat()
            })

    return sorted(backups, key=lambda x: x['created_at'], reverse=True)