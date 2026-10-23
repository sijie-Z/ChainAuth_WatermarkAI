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
