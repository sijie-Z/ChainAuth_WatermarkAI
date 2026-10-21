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
    User, Garden, Asset, AssetTag,
    License, LicenseApplication,
    Certificate, OperationLog
)


def create_tables():
    """创建所有数据表"""
    print("Creating database tables...")
    db.create_all()
    print("Tables created successfully!")


def create_admin_user():
    """创建管理员账号"""
    print("Creating admin user...")

    if not User.query.filter_by(username='admin').first():
        admin = User(
            username='admin',
            email='admin@szgarden.cn',
            phone='13800000000',
            role='admin',
            status='active',
            user_number='ADMIN001'
        )
        admin.set_password('admin123')

        db.session.add(admin)
        db.session.commit()
        print("Admin user created! Username: admin, Password: admin123")
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


def init_database():
    """初始化数据库"""
    app = create_app('development')

    with app.app_context():
        # 创建目录
        create_watermark_dir()

        # 创建表
        create_tables()

        # 创建基础数据
        create_admin_user()
        create_gardens()
        create_test_users()

        print("\n" + "="*50)
        print("Database initialization completed!")
        print("="*50)
        print("\nDefault accounts:")
        print("  Admin: admin / admin123")
        print("  Test users: adm1, adm2, user1, user2 / 123456")


if __name__ == '__main__':
    init_database()
