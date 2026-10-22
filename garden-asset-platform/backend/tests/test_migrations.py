"""迁移体系：空库必须能通过 Alembic 建出完整表结构"""
import os
import sqlite3
import subprocess
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]

EXPECTED_TABLES = {
    'users', 'assets', 'asset_versions', 'asset_tags', 'asset_comments',
    'asset_annotations', 'asset_shares', 'share_downloads',
    'collections', 'collection_assets',
    'favorites', 'download_records', 'licenses', 'license_applications',
    'license_contracts', 'certificates', 'blockchain_transactions',
    'operation_logs', 'system_configs', 'notification_reads',
    'notification_events', 'async_tasks', 'alembic_version',
}


def test_flask_db_upgrade_creates_full_schema(tmp_path):
    db_path = tmp_path / 'migration.db'
    env = os.environ.copy()
    env.update({
        'DATABASE_URL': f"sqlite:///{db_path.as_posix()}",
        'FLASK_APP': 'run.py',
        'AI_ENABLED': 'false',
        'RATELIMIT_ENABLED': 'false',
        'SCHEDULER_ENABLED': 'false',
    })

    result = subprocess.run(
        [sys.executable, '-m', 'flask', 'db', 'upgrade'],
        cwd=str(BACKEND_DIR),
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0, result.stderr[-2000:]

    connection = sqlite3.connect(db_path)
    try:
        tables = {
            row[0] for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
    finally:
        connection.close()

    missing = EXPECTED_TABLES - tables
    assert not missing, f'missing tables: {sorted(missing)}'

    connection = sqlite3.connect(db_path)
    try:
        certificate_columns = {
            row[1] for row in connection.execute('PRAGMA table_info(certificates)')
        }
        assert {'version_id', 'version_no'} <= certificate_columns
        for index in connection.execute('PRAGMA index_list(certificates)').fetchall():
            name, unique = index[1], index[2]
            if not unique:
                continue
            columns = [
                row[2] for row in connection.execute(
                    f'PRAGMA index_info("{name}")'
                )
            ]
            assert columns != ['asset_id'], (
                'certificates.asset_id 仍带唯一约束，无法按版本签发多份证书'
            )
    finally:
        connection.close()
