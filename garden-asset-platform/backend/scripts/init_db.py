"""
数据库初始化脚本
创建所有表并插入初始数据
"""
import sys
import os

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
    """创建管理员账号"""
    print("Creating admin user...")

    if not User.query.filter_by(username='admin').first():
        admin_password = os.environ.get('ADMIN_INITIAL_PASSWORD', 'admin123')
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
        if os.environ.get('ADMIN_INITIAL_PASSWORD'):
            print("Admin user created with ADMIN_INITIAL_PASSWORD.")
        else:
            print("Admin user created! Username: admin, Password: admin123 (change it before deployment)")
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
    """创建测试用户"""
    print("Creating test users...")

    test_users = [
        {'username': 'adm1', 'email': 'adm1@szgarden.cn', 'role': 'adm1', 'user_number': 'ADM1001'},
        {'username': 'adm2', 'email': 'adm2@szgarden.cn', 'role': 'adm2', 'user_number': 'ADM2001'},
        {'username': 'asset_mgr', 'email': 'asset@szgarden.cn', 'role': 'asset_admin', 'user_number': 'AST001'},
        {'username': 'license_mgr', 'email': 'license@szgarden.cn', 'role': 'license_admin', 'user_number': 'LIC001'},
        {'username': 'user1', 'email': 'user1@test.com', 'role': 'user'},
        {'username': 'user2', 'email': 'user2@test.com', 'role': 'user'},
    ]

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

    db.session.commit()
    print(f"Created {len(test_users)} test users! Password: 123456")


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
    app = create_app('development')

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
        print("\nDefault accounts:")
        print("  Admin: admin / admin123")
        print("  Test users: adm1, adm2, user1, user2 / 123456")


if __name__ == '__main__':
    init_database()
