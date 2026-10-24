"""数据库备份命令测试（子进程，避免测试进程共享 engine）"""
import os
import subprocess
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]


def _env(tmp_path):
    env = os.environ.copy()
    env.update({
        'DATABASE_URL': f"sqlite:///{(tmp_path / 'backup.db').as_posix()}",
        'BACKUP_DIR': str(tmp_path / 'backups'),
        'FLASK_APP': 'run.py',
        'FLASK_ENV': 'development',
        'AI_ENABLED': 'false',
        'RATELIMIT_ENABLED': 'false',
        'SCHEDULER_ENABLED': 'false',
        'TASK_WORKER_ENABLED': 'false',
    })
    return env


def test_backup_create_and_list(tmp_path):
    env = _env(tmp_path)
    migrated = subprocess.run(
        [sys.executable, '-m', 'flask', 'db', 'upgrade'],
        cwd=str(BACKEND_DIR), env=env, capture_output=True, text=True,
        timeout=120,
    )
    assert migrated.returncode == 0, migrated.stderr[-1000:]

    created = subprocess.run(
        [sys.executable, '-m', 'flask', 'backup', 'create'],
        cwd=str(BACKEND_DIR), env=env, capture_output=True, text=True,
        timeout=90,
    )
    assert created.returncode == 0, created.stderr[-1000:]
    backups = list((tmp_path / 'backups').glob('backup_*.db'))
    assert len(backups) == 1
    assert backups[0].stat().st_size > 0

    listed = subprocess.run(
        [sys.executable, '-m', 'flask', 'backup', 'list'],
        cwd=str(BACKEND_DIR), env=env, capture_output=True, text=True,
        timeout=90,
    )
    assert listed.returncode == 0, listed.stderr[-1000:]
    assert backups[0].name in listed.stdout


def _run(env, args, timeout=90):
    return subprocess.run(
        args, cwd=str(BACKEND_DIR), env=env, capture_output=True, text=True,
        timeout=timeout,
    )


def _user_exists(env, username):
    code = (
        'from run import app; from app.models import User; '
        'ctx = app.app_context(); ctx.push(); '
        f"print('exists', User.query.filter_by(username='{username}').count())"
    )
    result = _run(env, [sys.executable, '-c', code])
    assert result.returncode == 0, result.stderr[-1000:]
    return 'exists 1' in result.stdout


def test_backup_restore_roundtrip(tmp_path):
    """先备份、再删数据、恢复后数据回来，并保留回滚副本。"""
    env = _env(tmp_path)
    migrated = _run(
        env, [sys.executable, '-m', 'flask', 'db', 'upgrade'], timeout=120
    )
    assert migrated.returncode == 0, migrated.stderr[-1000:]

    created_user = _run(env, [
        sys.executable, '-m', 'flask', 'create-admin',
        '--username', 'backupuser', '--password', 'backup123',
    ])
    assert created_user.returncode == 0, created_user.stderr[-1000:]
    assert _user_exists(env, 'backupuser')

    created = _run(env, [sys.executable, '-m', 'flask', 'backup', 'create'])
    assert created.returncode == 0, created.stderr[-1000:]
    backups = sorted((tmp_path / 'backups').glob('backup_*.db'))
    assert len(backups) == 1

    code = (
        'from run import app; from app.extensions import db; '
        'from app.models import User; app.app_context().push(); '
        "u = User.query.filter_by(username='backupuser').first(); "
        'db.session.delete(u); db.session.commit()'
    )
    deleted = _run(env, [sys.executable, '-c', code])
    assert deleted.returncode == 0, deleted.stderr[-1000:]
    assert not _user_exists(env, 'backupuser')

    restored = _run(env, [
        sys.executable, '-m', 'flask', 'backup', 'restore', backups[0].name, '--yes'
    ])
    assert restored.returncode == 0, restored.stderr[-1000:]
    assert '恢复完成' in restored.stdout
    assert _user_exists(env, 'backupuser')

    safety_files = list((tmp_path / 'backups').glob('pre_restore_*.db'))
    assert len(safety_files) == 1
    assert safety_files[0].stat().st_size > 0

