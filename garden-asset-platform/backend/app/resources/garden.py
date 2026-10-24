"""
园林相关API资源
"""
import re

from flask import request
from flask_restful import Resource
from flask_jwt_extended import jwt_required, get_jwt_identity

from app.extensions import db
from app.models.garden import Garden
from app.models.asset import Asset
from app.models.user import User
from app.models.log import OperationLog

GARDEN_ADMIN_ROLES = ('admin', 'asset_admin')
CODE_PATTERN = re.compile(r'^[A-Z0-9]{2,10}$')

TEXT_FIELDS = {
    'name': 100,
    'name_en': 100,
    'location': 200,
    'heritage_level': 50,
    'cover_image': 500,
    'intro_video': 500,
}


def _validate_payload(data, garden=None, creating=False):
    """校验园林字段，返回错误信息或 None"""
    if creating:
        if not str(data.get('name') or '').strip():
            return '园林名称不能为空'
        if not str(data.get('code') or '').strip():
            return '园林编码不能为空'

    code = str(data.get('code') or '').strip().upper()
    if code:
        if not CODE_PATTERN.match(code):
            return '园林编码需为 2-10 位大写字母或数字'
        existing = Garden.query.filter_by(code=code).first()
        if existing and (not garden or existing.id != garden.id):
            return '园林编码已存在'
        data['code'] = code

    for field, max_length in TEXT_FIELDS.items():
        if field in data and data[field] is not None:
            value = str(data[field]).strip()
            if len(value) > max_length:
                return f'{field} 长度不能超过 {max_length}'
            data[field] = value

    for field, label in (
        ('longitude', '经度'), ('latitude', '纬度'),
        ('area_size', '面积'), ('build_year', '建造年份'),
        ('heritage_year', '列入文保年份')
    ):
        if field not in data:
            continue
        if data[field] in (None, ''):
            data[field] = None
            continue
        try:
            data[field] = float(data[field])
        except (TypeError, ValueError):
            return f'{label}必须是数字'

    if data.get('longitude') is not None and not (-180 <= data['longitude'] <= 180):
        return '经度需在 -180 到 180 之间'
    if data.get('latitude') is not None and not (-90 <= data['latitude'] <= 90):
        return '纬度需在 -90 到 90 之间'
    if data.get('area_size') is not None and data['area_size'] < 0:
        return '面积不能为负数'
    for field, label in (('build_year', '建造年份'), ('heritage_year', '列入文保年份')):
        if data.get(field) is not None:
            data[field] = int(data[field])
            if not (0 <= data[field] <= 2100):
                return f'{label}需在 0-2100 之间'

    if 'status' in data and data['status'] not in ('active', 'archived'):
        return '状态只能是 active 或 archived'

    return None


def _require_admin():
    user = User.query.get(get_jwt_identity())
    if not user or user.role not in GARDEN_ADMIN_ROLES:
        return None, ({'code': 403, 'message': '需要园林管理权限'}, 403)
    return user, None


class GardenListResource(Resource):
    """园林列表 / 新建园林"""

    def get(self):
        """获取园林列表

        status=all 返回全部（含归档），用于后台档案维护；
        其他取值按状态过滤，默认只返回 active。
        """
        status = request.args.get('status', 'active')
        query = Garden.query
        if status != 'all':
            query = query.filter_by(status=status)

        gardens = query.order_by(Garden.id).all()
        return {
            'code': 200,
            'data': [garden.to_dict() for garden in gardens]
        }, 200

    @jwt_required()
    def post(self):
        user, error = _require_admin()
        if error:
            return error

        data = request.get_json(silent=True) or {}
        error_message = _validate_payload(data, creating=True)
        if error_message:
            return {'code': 400, 'message': error_message}, 400

        garden = Garden(
            code=data['code'],
            name=data['name'].strip(),
            status=data.get('status', 'active')
        )
        for field in (
            'name_en', 'description', 'history', 'location', 'longitude',
            'latitude', 'area_size', 'build_year', 'heritage_level',
            'heritage_year', 'cover_image', 'intro_video'
        ):
            if field in data:
                setattr(garden, field, data[field])

        db.session.add(garden)
        db.session.commit()

        OperationLog.log(
            user=user,
            action='garden_create',
            module='garden',
            description=f'新建园林档案: {garden.name}',
            target_type='garden',
            target_id=str(garden.id),
            request=request
        )

        return {'code': 200, 'message': '园林档案已创建', 'data': garden.to_dict()}, 200


class GardenResource(Resource):
    """单个园林：详情 / 更新 / 删除"""

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

    @jwt_required()
    def put(self, garden_id):
        user, error = _require_admin()
        if error:
            return error

        garden = Garden.query.get(garden_id)
        if not garden:
            return {'code': 404, 'message': '园林不存在'}, 404

        data = request.get_json(silent=True) or {}
        error_message = _validate_payload(data, garden=garden)
        if error_message:
            return {'code': 400, 'message': error_message}, 400

        for field in (
            'code', 'name', 'name_en', 'description', 'history', 'location',
            'longitude', 'latitude', 'area_size', 'build_year', 'heritage_level',
            'heritage_year', 'cover_image', 'intro_video', 'status'
        ):
            if field in data:
                setattr(garden, field, data[field])

        db.session.commit()

        OperationLog.log(
            user=user,
            action='garden_update',
            module='garden',
            description=f'更新园林档案: {garden.name}',
            target_type='garden',
            target_id=str(garden.id),
            request=request
        )

        return {'code': 200, 'message': '园林档案已更新', 'data': garden.to_dict()}, 200

    @jwt_required()
    def delete(self, garden_id):
        user, error = _require_admin()
        if error:
            return error

        garden = Garden.query.get(garden_id)
        if not garden:
            return {'code': 404, 'message': '园林不存在'}, 404

        asset_count = Asset.query.filter_by(garden_id=garden_id).count()
        if asset_count:
            return {
                'code': 400,
                'message': f'该园林下仍有 {asset_count} 件资产，请先迁移或删除资产'
            }, 400

        name = garden.name
        db.session.delete(garden)
        db.session.commit()

        OperationLog.log(
            user=user,
            action='garden_delete',
            module='garden',
            description=f'删除园林档案: {name}',
            target_type='garden',
            request=request
        )

        return {'code': 200, 'message': '园林档案已删除'}, 200


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
