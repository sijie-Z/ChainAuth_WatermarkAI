"""
数据库备份与恢复

SQLite 使用 sqlite3 的在线备份 API，而不是直接复制文件：
WAL 模式下直接 copy 可能丢掉尚未 checkpoint 的事务，正在写入时也可能
得到不一致的快照。备份完成后立即做 integrity_check，损坏的副本不会
被当作可用备份。

PostgreSQL 使用 pg_dump / psql；导出带 --clean --if-exists，恢复带
ON_ERROR_STOP 与单事务执行，失败时不会留下半套表结构。
"""
import os
import sqlite3
import subprocess
from contextlib import closing
from datetime import datetime

from flask import current_app


def _sqlite_db_path():
    from app.extensions import db

    db_path = db.engine.url.database
    if not db_path or db_path == ':memory:':
        raise ValueError('SQLite 内存数据库无法备份或恢复')
    if not os.path.isabs(db_path):
        db_path = os.path.join(current_app.instance_path, db_path)
    return db_path


def _sqlite_snapshot(source_path, target_path):
    """用 SQLite 在线备份 API 生成一致快照，并校验完整性。"""
    with closing(sqlite3.connect(f'file:{source_path}?mode=ro', uri=True)) as source:
        with closing(sqlite3.connect(target_path)) as target:
            source.backup(target)
            result = target.execute('PRAGMA integrity_check').fetchone()[0]
    if result != 'ok':
        raise RuntimeError(f'SQLite 完整性校验失败: {result}')


def _sqlite_integrity_ok(path):
    try:
        with closing(
            sqlite3.connect(f'file:{path}?mode=ro', uri=True)
        ) as conn:
            return conn.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
    except sqlite3.DatabaseError:
        return False


def _postgres_params(db_url):
    """解析 PostgreSQL 连接串；密码中的 @ / : 等字符交给 SQLAlchemy 处理。"""
    from sqlalchemy.engine import make_url

    url = make_url(db_url)
    return {
        'user': url.username or '',
        'password': url.password or '',
        'host': url.host or 'localhost',
        'port': str(url.port or 5432),
        'database': url.database or '',
    }


def backup_database(output_dir=None):
    """备份数据库；默认目录取 BACKUP_DIR 配置。"""
    output_dir = output_dir or current_app.config.get('BACKUP_DIR', './backups')
    os.makedirs(output_dir, exist_ok=True)

    # 微秒后缀避免同一秒内多次备份互相覆盖
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    db_url = current_app.config.get('SQLALCHEMY_DATABASE_URI', '')
    suffix = 'sql' if db_url.startswith('postgresql') else 'db'
    backup_file = os.path.join(output_dir, f'backup_{timestamp}.{suffix}')

    if db_url.startswith('postgresql'):
        params = _postgres_params(db_url)
        env = os.environ.copy()
        env['PGPASSWORD'] = params['password']
        cmd = [
            'pg_dump',
            '-h', params['host'],
            '-p', params['port'],
            '-U', params['user'],
            '-d', params['database'],
            '--clean', '--if-exists', '--no-owner',
            '-f', backup_file,
        ]
        subprocess.run(cmd, env=env, check=True)
        if not os.path.exists(backup_file) or os.path.getsize(backup_file) == 0:
            raise RuntimeError('pg_dump 未生成有效备份文件')

    elif db_url.startswith('sqlite'):
        db_path = _sqlite_db_path()
        try:
            _sqlite_snapshot(db_path, backup_file)
        except Exception:
            if os.path.exists(backup_file):
                os.remove(backup_file)
            raise

    else:
        raise ValueError(f'不支持的数据库类型: {db_url}')

    return backup_file


def restore_database(backup_file):
    """恢复数据库；SQLite 覆盖前自动保留一份当前库作为回滚副本。"""
    if not backup_file or not os.path.isfile(backup_file):
        raise ValueError('备份文件不存在')
    db_url = current_app.config.get('SQLALCHEMY_DATABASE_URI', '')

    if db_url.startswith('postgresql'):
        params = _postgres_params(db_url)
        env = os.environ.copy()
        env['PGPASSWORD'] = params['password']
        cmd = [
            'psql',
            '-h', params['host'],
            '-p', params['port'],
            '-U', params['user'],
            '-d', params['database'],
            '-v', 'ON_ERROR_STOP=1',
            '--single-transaction',
            '-f', backup_file,
        ]
        subprocess.run(cmd, env=env, check=True)

    elif db_url.startswith('sqlite'):
        from app.extensions import db

        db_path = _sqlite_db_path()
        if not _sqlite_integrity_ok(backup_file):
            raise ValueError('备份文件未通过完整性校验，已拒绝恢复')

        # 先释放当前进程持有的连接，再覆盖数据库文件
        db.session.remove()
        db.engine.dispose()

        backup_dir = current_app.config.get('BACKUP_DIR', './backups')
        os.makedirs(backup_dir, exist_ok=True)
        safety = os.path.join(
            backup_dir,
            f"pre_restore_{datetime.now():%Y%m%d_%H%M%S_%f}.db"
        )
        _sqlite_snapshot(db_path, safety)
        _sqlite_snapshot(backup_file, db_path)
        return safety

    else:
        raise ValueError('不支持的数据库类型')

    return None


def list_backups(backup_dir=None):
    """列出 SQLite .db 和 PostgreSQL .sql 备份，按时间倒序。"""
    backup_dir = backup_dir or current_app.config.get('BACKUP_DIR', './backups')
    if not os.path.exists(backup_dir):
        return []

    backups = []
    for filename in os.listdir(backup_dir):
        if not filename.startswith('backup_'):
            continue
        if not (filename.endswith('.sql') or filename.endswith('.db')):
            continue
        path = os.path.join(backup_dir, filename)
        if not os.path.isfile(path):
            continue
        stat = os.stat(path)
        backups.append({
            'filename': filename,
            'path': path,
            'size': stat.st_size,
            'created_at': datetime.fromtimestamp(stat.st_mtime).isoformat()
        })

    return sorted(backups, key=lambda item: item['created_at'], reverse=True)
