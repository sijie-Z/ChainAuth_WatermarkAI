"""
测试数据生成脚本
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.extensions import db
from app.models import User, Garden, Asset, AssetTag
from datetime import datetime
import uuid


def generate_asset_code(garden_code, asset_type):
    """生成资产编码"""
    type_map = {'image': 'IMG', 'model': 'MDL', 'vector': 'VEC', 'document': 'DOC', 'video': 'VID'}
    ts = datetime.now().strftime('%Y%m%d%H%M%S')
    return f"{garden_code}-{type_map.get(asset_type, 'OTH')}-{ts}-{uuid.uuid4().hex[:4].upper()}"


def create_test_assets():
    """创建测试资产数据"""
    app = create_app('development')

    with app.app_context():
        # 获取园林和管理员
        gardens = Garden.query.all()
        admin = User.query.filter_by(role='admin').first()

        if not gardens or not admin:
            print("请先运行 init_db.py 创建基础数据")
            return

        assets_data = [
            {'title': '拙政园远香堂全景', 'type': 'image', 'garden': 'ZZY', 'desc': '远香堂是拙政园的主体建筑，面阔三间，四面临水'},
            {'title': '拙政园荷风四面亭', 'type': 'image', 'garden': 'ZZY', 'desc': '荷风四面亭位于园林中部，四面环水'},
            {'title': '留园冠云峰', 'type': 'image', 'garden': 'LY', 'desc': '冠云峰是留园的标志性太湖石'},
            {'title': '狮子林假山群', 'type': 'image', 'garden': 'SZL', 'desc': '狮子林以假山著称，素有假山王国美誉'},
            {'title': '网师园殿春簃', 'type': 'image', 'garden': 'WSY', 'desc': '殿春簃是网师园内的书斋庭院'},
            {'title': '沧浪亭复廊', 'type': 'image', 'garden': 'CLT', 'desc': '沧浪亭复廊是苏州园林中著名的借景手法'},
            {'title': '拙政园平面图', 'type': 'vector', 'garden': 'ZZY', 'desc': '拙政园总体平面矢量图'},
            {'title': '留园建筑分布图', 'type': 'vector', 'garden': 'LY', 'desc': '留园建筑分布矢量数据'},
            {'title': '拙政园历史文献', 'type': 'document', 'garden': 'ZZY', 'desc': '拙政园相关历史文献资料'},
        ]

        for data in assets_data:
            garden = next((g for g in gardens if g.code == data['garden']), None)
            if not garden:
                continue

            asset = Asset(
                asset_code=generate_asset_code(data['garden'], data['type']),
                title=data['title'],
                description=data['desc'],
                asset_type=data['type'],
                garden_id=garden.id,
                creator_id=admin.id,
                uploader_id=admin.id,
                owner_id=admin.id,
                file_format='jpg' if data['type'] == 'image' else ('shp' if data['type'] == 'vector' else 'pdf'),
                file_size=1024*1024,
                status='published',
                watermark_status='none',
                chain_status='none'
            )
            db.session.add(asset)

        db.session.commit()
        print(f"创建了 {len(assets_data)} 个测试资产")


if __name__ == '__main__':
    create_test_assets()