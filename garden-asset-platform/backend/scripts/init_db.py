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
    """创建苏州园林数据"""
    print("Creating gardens data...")

    gardens_data = [
        {
            'name': '拙政园',
            'code': 'ZZY',
            'description': '拙政园位于江苏省苏州市姑苏区，是江南古典园林的代表作品。',
            'location': '苏州市姑苏区东北街178号',
            'build_year': 1509,
            'area_size': 5.2,
            'heritage_level': '世界文化遗产'
        },
        {
            'name': '留园',
            'code': 'LY',
            'description': '留园是中国大型古典私家园林，以园内建筑布置精巧、奇石众多而著称。',
            'location': '苏州市姑苏区留园路338号',
            'build_year': 1593,
            'area_size': 2.3,
            'heritage_level': '世界文化遗产'
        },
        {
            'name': '狮子林',
            'code': 'SZL',
            'description': '狮子林是苏州四大名园之一，以湖山奇石、洞壑深邃而享誉盛名。',
            'location': '苏州市姑苏区园林路23号',
            'build_year': 1342,
            'area_size': 1.1,
            'heritage_level': '世界文化遗产'
        },
        {
            'name': '网师园',
            'code': 'WSY',
            'description': '网师园是苏州园林中型古典山水宅园代表作品，以小巧精致著称。',
            'location': '苏州市姑苏区带城桥路阔家头巷11号',
            'build_year': 1174,
            'area_size': 0.6,
            'heritage_level': '世界文化遗产'
        },
        {
            'name': '沧浪亭',
            'code': 'CLT',
            'description': '沧浪亭是苏州最古老的园林，是苏州四大名园之一。',
            'location': '苏州市姑苏区人民路沧浪亭街3号',
            'build_year': 1044,
            'area_size': 1.1,
            'heritage_level': '世界文化遗产'
        },
        {
            'name': '耦园',
            'code': 'OY',
            'description': '耦园三面临水，一面临街，前后设有河埠。',
            'location': '苏州市姑苏区小新桥巷6号',
            'build_year': 1874,
            'area_size': 0.8,
            'heritage_level': '世界文化遗产'
        },
        {
            'name': '艺圃',
            'code': 'YP',
            'description': '艺圃是一座建于明代嘉靖年间的古典园林。',
            'location': '苏州市姑苏区文衙弄5号',
            'build_year': 1541,
            'area_size': 0.4,
            'heritage_level': '世界文化遗产'
        },
        {
            'name': '环秀山庄',
            'code': 'HXSZ',
            'description': '环秀山庄以假山堆叠奇巧著称，是研究中国园林假山艺术的典范。',
            'location': '苏州市姑苏区景德路272号',
            'build_year': 1847,
            'area_size': 0.2,
            'heritage_level': '世界文化遗产'
        },
        {
            'name': '怡园',
            'code': 'YY',
            'description': '怡园是苏州园林中建造较晚的一座，集苏州各园林之大成。',
            'location': '苏州市姑苏区人民路343号',
            'build_year': 1874,
            'area_size': 0.6,
            'heritage_level': '市级文保单位'
        },
        {
            'name': '可园',
            'code': 'KY',
            'description': '可园与沧浪亭隔水相望，是苏州现存唯一的书院园林。',
            'location': '苏州市姑苏区人民路708号',
            'build_year': 1723,
            'area_size': 0.5,
            'heritage_level': '市级文保单位'
        }
    ]

    for garden_data in gardens_data:
        if not Garden.query.filter_by(code=garden_data['code']).first():
            garden = Garden(**garden_data)
            db.session.add(garden)

    db.session.commit()
    print(f"Created {len(gardens_data)} gardens!")


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
