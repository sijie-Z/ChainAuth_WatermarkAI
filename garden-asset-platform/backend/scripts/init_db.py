"""
数据库初始化脚本
创建所有表并插入初始数据
"""
import sys
import os
import secrets

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.extensions import db
from app.models import (
    User, Garden, Asset, AssetTag, AssetVersion,
    License, LicenseApplication,
    Certificate, OperationLog
)

# 迁移基线：旧库没有 alembic_version 时先 stamp 到此版本，再执行后续迁移
BASELINE_REVISION = 'be3bcbd6313e'

# 本次初始化实际使用的管理员密码（仅用于一次性提示，历史密码不回显）
_ADMIN_PASSWORD = None
_ADMIN_PASSWORD_GENERATED = False
_TEST_USERS_CREATED = 0


def _write_initial_password(password):
    """把一次性初始密码写入仅当前用户可读的文件，避免明文进日志。"""
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    instance_dir = os.path.join(root, 'instance')
    os.makedirs(instance_dir, exist_ok=True)
    path = os.path.join(instance_dir, 'initial_admin_password.txt')
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, 'w', encoding='utf-8') as handle:
        handle.write(password + '\n')
    return path


def _is_production():
    env = os.environ.get('FLASK_CONFIG') or os.environ.get('FLASK_ENV') or ''
    return env.lower() == 'production'


def _app_config_name():
    return 'production' if _is_production() else 'development'


def create_tables():
    """通过 Alembic 创建/升级数据表

    - 空库：执行 baseline 及后续迁移；
    - 已有表但没有 alembic_version 的旧库：先 stamp 基线，再应用后续迁移。
    """
    from flask_migrate import stamp, upgrade
    from sqlalchemy import inspect

    print("Applying database migrations...")
    existing = set(inspect(db.engine).get_table_names())
    if existing and 'users' in existing and 'alembic_version' not in existing:
        stamp(revision=BASELINE_REVISION)
        print(f"Existing database stamped at baseline {BASELINE_REVISION}")
    upgrade()
    print("Database migrations applied.")


def create_admin_user():
    """创建管理员账号

    生产环境未提供 ADMIN_INITIAL_PASSWORD 时生成一次性随机密码，
    不再回落到演示密码 admin123。
    """
    global _ADMIN_PASSWORD, _ADMIN_PASSWORD_GENERATED

    print("Creating admin user...")

    if not User.query.filter_by(username='admin').first():
        configured = os.environ.get('ADMIN_INITIAL_PASSWORD')
        if configured:
            admin_password = configured
        elif _is_production():
            admin_password = secrets.token_urlsafe(18)
            _ADMIN_PASSWORD_GENERATED = True
        else:
            admin_password = 'admin123'

        admin = User(
            username='admin',
            email='admin@szgarden.cn',
            phone='13800000000',
            role='admin',
            status='active',
            user_number='ADMIN001'
        )
        admin.set_password(admin_password)

        db.session.add(admin)
        db.session.commit()
        _ADMIN_PASSWORD = admin_password
        if configured:
            print("Admin user created with ADMIN_INITIAL_PASSWORD.")
        elif _ADMIN_PASSWORD_GENERATED:
            _write_initial_password(admin_password)
            print("Admin user created with a generated random password.")
            print("  初始密码已写入 backend/instance/initial_admin_password.txt")
            print("  该文件权限为 600，请首次登录后立即修改密码并删除文件。")
        else:
            print("Admin user created (development demo password; see README/USER-GUIDE).")
    else:
        print("Admin user already exists.")


def create_gardens():
    """创建或刷新苏州园林档案数据"""
    print("Creating gardens data...")

    from app.seed_data import GARDENS as gardens_data

    created = 0
    for garden_data in gardens_data:
        garden = Garden.query.filter_by(code=garden_data['code']).first()
        if not garden:
            garden = Garden(**garden_data)
            db.session.add(garden)
            created += 1
        else:
            # 重复执行时刷新资料，保证本地库与种子数据一致
            for key, value in garden_data.items():
                setattr(garden, key, value)

    db.session.commit()
    print(f"Gardens ready: {len(gardens_data)} (created {created})")


def create_test_users():
    """创建测试用户

    生产环境默认不创建演示账号（123456 弱口令），
    需要演示数据时显式设置 SEED_DEMO_USERS=true。
    """
    global _TEST_USERS_CREATED

    print("Creating test users...")

    if _is_production() and os.environ.get('SEED_DEMO_USERS', '').lower() != 'true':
        print("Skipped demo users in production (set SEED_DEMO_USERS=true to create them).")
        return

    test_users = [
        {'username': 'adm1', 'email': 'adm1@szgarden.cn', 'role': 'adm1', 'user_number': 'ADM1001'},
        {'username': 'adm2', 'email': 'adm2@szgarden.cn', 'role': 'adm2', 'user_number': 'ADM2001'},
        {'username': 'asset_mgr', 'email': 'asset@szgarden.cn', 'role': 'asset_admin', 'user_number': 'AST001'},
        {'username': 'license_mgr', 'email': 'license@szgarden.cn', 'role': 'license_admin', 'user_number': 'LIC001'},
        {'username': 'user1', 'email': 'user1@test.com', 'role': 'user'},
        {'username': 'user2', 'email': 'user2@test.com', 'role': 'user'},
    ]

    created = 0
    for user_data in test_users:
        if not User.query.filter_by(username=user_data['username']).first():
            user = User(
                username=user_data['username'],
                email=user_data['email'],
                role=user_data['role'],
                user_number=user_data.get('user_number'),
                status='active'
            )
            user.set_password('123456')
            db.session.add(user)
            created += 1

    db.session.commit()
    _TEST_USERS_CREATED = created
    print(f"Created {created} test users (demo password documented in README).")


def create_watermark_dir():
    """创建水印相关目录"""
    print("Creating directories...")

    dirs = [
        'uploads',
        'uploads/originals',
        'uploads/watermarked',
        'uploads/extracted',
        'data/watermark',
        'data/models'
    ]

    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for d in dirs:
        path = os.path.join(base_dir, d)
        os.makedirs(path, exist_ok=True)
        print(f"  Created: {path}")


def ensure_indexes():
    """为旧库补建唯一索引（create_all 不会修改已存在的表）"""
    from sqlalchemy import text
    try:
        db.session.execute(text(
            'CREATE UNIQUE INDEX IF NOT EXISTS uq_license_contract_application '
            'ON license_contracts(application_id)'
        ))
        db.session.commit()
        print("Indexes ready.")
    except Exception as exc:
        db.session.rollback()
        print(f"Index check skipped: {exc}")


def ensure_asset_versions():
    """为已有资产补建 v1 版本记录（已有版本不删除、不覆盖）"""
    print("Ensuring asset versions...")

    assets = Asset.query.filter(Asset.file_hash.isnot(None)).all()
    created = 0
    for asset in assets:
        if AssetVersion.query.filter_by(asset_id=asset.id).first():
            continue
        storage_path = asset.storage_path or ''
        db.session.add(AssetVersion(
            asset_id=asset.id,
            version_no=1,
            file_path=storage_path,
            file_name=os.path.basename(storage_path) if storage_path else None,
            file_format=asset.file_format,
            file_size=asset.file_size,
            file_hash=asset.file_hash,
            thumbnail_path=asset.thumbnail_path,
            change_note='初始版本',
            created_by=asset.uploader_id or asset.creator_id
        ))
        created += 1

    db.session.commit()
    print(f"Asset versions ready: {created} created")


def init_database():
    """初始化数据库"""
    app = create_app(_app_config_name())

    with app.app_context():
        # 创建目录
        create_watermark_dir()

        # 创建表
        create_tables()
        ensure_indexes()

        # 创建基础数据
        create_admin_user()
        create_gardens()
        create_test_users()
        ensure_asset_versions()

        print("\n" + "="*50)
        print("Database initialization completed!")
        print("="*50)
        print("\nAccounts:")
        if _ADMIN_PASSWORD:
            print("  Admin: admin")
            if _ADMIN_PASSWORD_GENERATED:
                print("  初始密码文件：backend/instance/initial_admin_password.txt")
            else:
                print("  密码见初始化提示或 ADMIN_INITIAL_PASSWORD")
        else:
            print("  Admin: admin（已存在，密码保持不变）")
        if _TEST_USERS_CREATED:
            print(f"  Test users: adm1, adm2, user1, user2 / 123456（本次创建 {_TEST_USERS_CREATED} 个）")
        elif _is_production():
            print("  Demo users: 未创建（生产环境默认关闭，SEED_DEMO_USERS=true 可开启）")


if __name__ == '__main__':
    init_database()
