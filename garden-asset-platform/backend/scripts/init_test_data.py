"""
初始化测试数据
创建演示账号、园林、资产等数据
"""
import os
import sys
from datetime import datetime

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.extensions import db
from app.models.user import User, UserToken
from app.models.garden import Garden
from app.models.asset import Asset, AssetTag
from app.models.license import LicenseApplication
from app.models.blockchain import Certificate


def init_test_data():
    """初始化测试数据"""
    app = create_app('development')

    with app.app_context():
        # 创建数据库表
        db.create_all()
        print("Database tables created")

        # 创建测试用户
        users_data = [
            {'username': 'admin', 'password': 'admin123', 'role': 'admin', 'nickname': '超级管理员'},
            {'username': 'adm1', 'password': 'adm123', 'role': 'adm1', 'nickname': '资产管理员'},
            {'username': 'adm2', 'password': 'adm123', 'role': 'adm2', 'nickname': '授权管理员'},
            {'username': 'adm3', 'password': 'adm123', 'role': 'adm3', 'nickname': '审核员'},
            {'username': 'user1', 'password': 'user123', 'role': 'user', 'nickname': '测试用户'},
        ]

        for data in users_data:
            existing = User.query.filter_by(username=data['username']).first()
            if not existing:
                user = User(
                    username=data['username'],
                    role=data['role'],
                    nickname=data['nickname'],
                    email=f"{data['username']}@garden.test",
                    status='active'
                )
                user.set_password(data['password'])
                db.session.add(user)
                print(f"Created user: {data['username']}")
            else:
                print(f"User exists: {data['username']}")

        db.session.commit()

        # 创建园林数据
        gardens_data = [
            {'name': '拙政园', 'code': 'ZZY', 'description': '中国四大名园之首，世界文化遗产', 'location': '姑苏区东北街178号'},
            {'name': '留园', 'code': 'LY', 'description': '以园林建筑艺术著称，世界文化遗产', 'location': '姑苏区留园路338号'},
            {'name': '狮子林', 'code': 'SZL', 'description': '以假山迷宫闻名，世界文化遗产', 'location': '姑苏区园林路23号'},
            {'name': '沧浪亭', 'code': 'CLT', 'description': '苏州历史最悠久的园林', 'location': '姑苏区人民路三元坊口'},
            {'name': '网师园', 'code': 'WSY', 'description': '以小巧精致著称', 'location': '姑苏区阔街头巷11号'},
        ]

        for data in gardens_data:
            existing = Garden.query.filter_by(code=data['code']).first()
            if not existing:
                garden = Garden(**data)
                db.session.add(garden)
                print(f"Created garden: {data['name']}")
            else:
                print(f"Garden exists: {data['name']}")

        db.session.commit()

        # 创建测试资产
        gardens = Garden.query.all()
        user = User.query.filter_by(username='user1').first()

        assets_data = [
            {'title': '拙政园远香堂全景图', 'asset_type': 'image', 'description': '远香堂全景摄影作品', 'garden_id': 1},
            {'title': '留园建筑平面矢量数据', 'asset_type': 'vector', 'description': '留园主要建筑群平面图', 'garden_id': 2},
            {'title': '狮子林假山三维模型', 'asset_type': 'model', 'description': '狮子林核心假山群3D重建', 'garden_id': 3},
            {'title': '沧浪亭水景摄影', 'asset_type': 'image', 'description': '沧浪亭水景四季摄影', 'garden_id': 4},
            {'title': '拙政园历史文献', 'asset_type': 'document', 'description': '拙政园历史沿革文献汇编', 'garden_id': 1},
        ]

        for idx, data in enumerate(assets_data):
            garden_idx = data['garden_id'] - 1 if data['garden_id'] else 0
            garden_code = gardens[garden_idx].code if garden_idx < len(gardens) else 'GEN'
            type_prefix = data['asset_type'].upper()[:3]
            asset_code = f"{garden_code}-{type_prefix}-2026{idx+1:04d}"

            existing = Asset.query.filter_by(asset_code=asset_code).first()
            if not existing:
                asset = Asset(
                    asset_code=asset_code,
                    title=data['title'],
                    asset_type=data['asset_type'],
                    description=data['description'],
                    garden_id=data['garden_id'],
                    uploader_id=user.id if user else None,
                    creator_id=user.id if user else None,
                    status='published',
                    watermark_status='none',
                    chain_status='none'
                )
                db.session.add(asset)
                print(f"Created asset: {asset_code}")
            else:
                print(f"Asset exists: {asset_code}")

        db.session.commit()

        # 创建标签
        tags_data = ['摄影', '建筑', '园林', '历史', '三维', '矢量', '文献', '水景', '假山', '四季']

        for tag_name in tags_data:
            existing = AssetTag.query.filter_by(name=tag_name).first()
            if not existing:
                tag = AssetTag(name=tag_name)
                db.session.add(tag)

        db.session.commit()

        print("\n" + "=" * 50)
        print("Test data initialized successfully!")
        print("=" * 50)

        # 统计
        print(f"Users: {User.query.count()}")
        print(f"Gardens: {Garden.query.count()}")
        print(f"Assets: {Asset.query.count()}")
        print(f"Tags: {AssetTag.query.count()}")


if __name__ == '__main__':
    init_test_data()