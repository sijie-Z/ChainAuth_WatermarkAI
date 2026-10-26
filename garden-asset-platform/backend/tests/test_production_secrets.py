"""生产密钥校验测试

生产配置必须拒绝示例占位密钥与短密钥，避免 Token 可被伪造。
"""
import pytest
from flask import Flask

from app.config import validate_production_config


def make_app(secret, jwt_secret):
    app = Flask(__name__)
    app.config.update(
        SECRET_KEY=secret,
        JWT_SECRET_KEY=jwt_secret,
        TESTING=False,
    )
    return app


def test_rejects_placeholder_secrets():
    app = make_app(
        'change-me-to-a-random-secret',
        'change-me-to-another-random-secret',
    )
    with pytest.raises(RuntimeError) as exc:
        validate_production_config(app)
    assert 'SECRET_KEY' in str(exc.value)
    assert '示例占位文本' in str(exc.value)


def test_rejects_short_secrets():
    app = make_app('short-secret', 'also-short')
    with pytest.raises(RuntimeError) as exc:
        validate_production_config(app)
    assert '长度不足 32 位' in str(exc.value)


def test_rejects_default_minio_credentials_when_enabled():
    app = make_app('a' * 64, 'b' * 64)
    app.config.update(
        STORAGE_BACKEND='minio',
        MINIO_ACCESS_KEY='minioadmin',
        MINIO_SECRET_KEY='minioadmin',
    )
    with pytest.raises(RuntimeError) as exc:
        validate_production_config(app)
    assert 'MINIO_ACCESS_KEY' in str(exc.value)


def test_accepts_generated_length_secrets():
    app = make_app('a' * 64, 'b' * 64)
    validate_production_config(app)


def test_generate_secrets_script_outputs_strong_keys():
    import subprocess
    import sys
    from pathlib import Path

    script = Path(__file__).resolve().parents[1] / 'scripts' / 'generate_secrets.py'
    result = subprocess.run(
        [sys.executable, str(script)],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    lines = dict(
        line.split('=', 1) for line in result.stdout.strip().splitlines() if '=' in line
    )
    assert len(lines['SECRET_KEY']) == 64
    assert len(lines['JWT_SECRET_KEY']) == 64
    assert lines['SECRET_KEY'] != lines['JWT_SECRET_KEY']


def test_init_db_selects_production_config(monkeypatch):
    import importlib.util
    from pathlib import Path

    path = Path(__file__).resolve().parents[1] / 'scripts' / 'init_db.py'
    spec = importlib.util.spec_from_file_location('init_db_script', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    monkeypatch.setenv('FLASK_ENV', 'production')
    monkeypatch.delenv('FLASK_CONFIG', raising=False)
    assert module._is_production() is True
    assert module._app_config_name() == 'production'

    monkeypatch.setenv('FLASK_ENV', 'development')
    assert module._is_production() is False
    assert module._app_config_name() == 'development'


def test_create_admin_generates_random_password_when_not_debug(app, runner):
    from app.models import User

    result = runner.invoke(args=['create-admin', '--username', 'opsadmin'])
    assert result.exit_code == 0, result.output
    assert '随机初始密码' in result.output

    password = result.output.split('随机初始密码: ', 1)[1].split('（', 1)[0].strip()
    assert len(password) >= 20

    with app.app_context():
        admin = User.query.filter_by(username='opsadmin').first()
        assert admin is not None
        assert admin.check_password(password)

