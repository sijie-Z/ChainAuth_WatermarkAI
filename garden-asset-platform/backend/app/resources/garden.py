"""
园林相关API资源
"""
from flask import request
from flask_restful import Resource
from flask_jwt_extended import jwt_required
from app.extensions import db
from app.models.garden import Garden
from app.models.asset import Asset


class GardenListResource(Resource):
    """园林列表"""

    def get(self):
        """获取园林列表"""
        status = request.args.get('status', 'active')

        gardens = Garden.query.filter_by(status=status).order_by(Garden.id).all()

        return {
            'code': 200,
            'data': [garden.to_dict() for garden in gardens]
        }, 200


class GardenResource(Resource):
    """单个园林"""

    def get(self, garden_id):
        """获取园林详情"""
        garden = Garden.query.get(garden_id)

        if not garden:
            return {'code': 404, 'message': '园林不存在'}, 404

        data = garden.to_dict()

        # 获取该园林的资产统计
        assets = Asset.query.filter_by(garden_id=garden_id, status='published').all()
        data['assets'] = {
            'total': len(assets),
            'by_type': {}
        }

        type_counts = {}
        for asset in assets:
            type_counts[asset.asset_type] = type_counts.get(asset.asset_type, 0) + 1
        data['assets']['by_type'] = type_counts

        return {
            'code': 200,
            'data': data
        }, 200


class GardenStatsResource(Resource):
    """园林统计"""

    @jwt_required()
    def get(self, garden_id):
        """获取园林统计数据"""
        garden = Garden.query.get(garden_id)

        if not garden:
            return {'code': 404, 'message': '园林不存在'}, 404

        # 资产统计
        total_assets = Asset.query.filter_by(garden_id=garden_id).count()
        published_assets = Asset.query.filter_by(garden_id=garden_id, status='published').count()
        watermarked_assets = Asset.query.filter_by(
            garden_id=garden_id,
            watermark_status='embedded'
        ).count()
        chained_assets = Asset.query.filter_by(
            garden_id=garden_id,
            chain_status='confirmed'
        ).count()

        return {
            'code': 200,
            'data': {
                'garden': garden.to_dict(),
                'stats': {
                    'total_assets': total_assets,
                    'published_assets': published_assets,
                    'watermarked_assets': watermarked_assets,
                    'chained_assets': chained_assets,
                    'watermark_rate': round(watermarked_assets / total_assets * 100, 2) if total_assets > 0 else 0,
                    'chain_rate': round(chained_assets / total_assets * 100, 2) if total_assets > 0 else 0
                }
            }
        }, 200