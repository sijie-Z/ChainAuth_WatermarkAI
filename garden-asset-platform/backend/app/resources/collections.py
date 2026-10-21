"""用户资产合集

合集是用户自建的策展单位，与园林档案、收藏互为补充：
- 园林档案解决“资产属于哪座园”；
- 收藏解决“我关注哪些资产”；
- 合集解决“我为某个主题组织了一组资产”。
"""
from flask import request
from flask_jwt_extended import jwt_required, get_jwt_identity
from flask_restful import Resource
from sqlalchemy import or_

from app.extensions import db
from app.models import Asset, Collection, CollectionAsset, User
from app.models.log import OperationLog

ADMIN_ROLES = ('admin', 'asset_admin', 'license_admin', 'adm1', 'adm2')


def _current_user():
    return User.query.get(get_jwt_identity())


def _is_admin(user):
    return bool(user and user.role in ADMIN_ROLES)


def _can_view(collection, user):
    return bool(
        user and (
            collection.owner_id == user.id
            or collection.is_public
            or _is_admin(user)
        )
    )


def _can_edit(collection, user):
    return bool(user and (collection.owner_id == user.id or _is_admin(user)))


def _detail_payload(collection, user):
    data = collection.to_dict(viewer_id=user.id if user else None)
    assets = []
    for item in collection.items.order_by(CollectionAsset.id).all():
        asset = item.asset
        if not asset or asset.status == 'deleted':
            continue
        if not _is_admin(user) and asset.status != 'published' and collection.owner_id != user.id:
            continue
        assets.append(asset.to_dict())
    data['assets'] = assets
    return data


class CollectionListResource(Resource):
    """我的合集 / 新建合集"""

    @jwt_required()
    def get(self):
        user = _current_user()
        if not user:
            return {'code': 404, 'message': '用户不存在'}, 404

        query = Collection.query.filter(
            or_(Collection.owner_id == user.id, Collection.is_public.is_(True))
        ).order_by(
            Collection.updated_at.desc(), Collection.id.desc()
        ).limit(100)

        asset_id = (request.args.get('asset_id') or '').strip()
        items = []
        for collection in query.all():
            data = collection.to_dict(viewer_id=user.id)
            if asset_id:
                data['contains'] = collection.items.filter_by(asset_id=asset_id).first() is not None
            items.append(data)

        return {'code': 200, 'data': items}, 200

    @jwt_required()
    def post(self):
        user = _current_user()
        if not user:
            return {'code': 404, 'message': '用户不存在'}, 404

        data = request.get_json(silent=True) or {}
        name = str(data.get('name') or '').strip()
        if not name:
            return {'code': 400, 'message': '合集名称不能为空'}, 400
        if len(name) > 100:
            return {'code': 400, 'message': '合集名称不能超过 100 字'}, 400

        description = str(data.get('description') or '').strip()
        if len(description) > 500:
            return {'code': 400, 'message': '合集说明不能超过 500 字'}, 400

        collection = Collection(
            name=name,
            description=description or None,
            owner_id=user.id,
            is_public=bool(data.get('is_public', False))
        )
        db.session.add(collection)
        db.session.commit()

        OperationLog.log(
            user=user,
            action='collection_create',
            module='asset',
            description=f'新建合集: {collection.name}',
            target_type='collection',
            target_id=str(collection.id),
            request=request
        )
        return {
            'code': 200,
            'message': '合集已创建',
            'data': collection.to_dict(viewer_id=user.id)
        }, 200


class CollectionResource(Resource):
    """合集详情 / 编辑 / 删除"""

    @jwt_required()
    def get(self, collection_id):
        user = _current_user()
        collection = Collection.query.get(collection_id)
        if not collection:
            return {'code': 404, 'message': '合集不存在'}, 404
        if not _can_view(collection, user):
            return {'code': 403, 'message': '无权查看该合集'}, 403

        return {'code': 200, 'data': _detail_payload(collection, user)}, 200

    @jwt_required()
    def put(self, collection_id):
        user = _current_user()
        collection = Collection.query.get(collection_id)
        if not collection:
            return {'code': 404, 'message': '合集不存在'}, 404
        if not _can_edit(collection, user):
            return {'code': 403, 'message': '无权编辑该合集'}, 403

        data = request.get_json(silent=True) or {}
        if 'name' in data:
            name = str(data.get('name') or '').strip()
            if not name:
                return {'code': 400, 'message': '合集名称不能为空'}, 400
            if len(name) > 100:
                return {'code': 400, 'message': '合集名称不能超过 100 字'}, 400
            collection.name = name
        if 'description' in data:
            description = str(data.get('description') or '').strip()
            if len(description) > 500:
                return {'code': 400, 'message': '合集说明不能超过 500 字'}, 400
            collection.description = description or None
        if 'is_public' in data:
            collection.is_public = bool(data['is_public'])

        db.session.commit()
        return {
            'code': 200,
            'message': '合集已更新',
            'data': collection.to_dict(viewer_id=user.id)
        }, 200

    @jwt_required()
    def delete(self, collection_id):
        user = _current_user()
        collection = Collection.query.get(collection_id)
        if not collection:
            return {'code': 404, 'message': '合集不存在'}, 404
        if not _can_edit(collection, user):
            return {'code': 403, 'message': '无权删除该合集'}, 403

        name = collection.name
        db.session.delete(collection)
        db.session.commit()

        OperationLog.log(
            user=user,
            action='collection_delete',
            module='asset',
            description=f'删除合集: {name}',
            target_type='collection',
            request=request
        )
        return {'code': 200, 'message': '合集已删除'}, 200


class CollectionAssetsResource(Resource):
    """向合集添加资产（批量）"""

    @jwt_required()
    def post(self, collection_id):
        user = _current_user()
        collection = Collection.query.get(collection_id)
        if not collection:
            return {'code': 404, 'message': '合集不存在'}, 404
        if not _can_edit(collection, user):
            return {'code': 403, 'message': '无权编辑该合集'}, 403

        data = request.get_json(silent=True) or {}
        asset_ids = data.get('asset_ids')
        if not isinstance(asset_ids, list) or not asset_ids:
            return {'code': 400, 'message': '请选择要加入的资产'}, 400
        asset_ids = [str(asset_id) for asset_id in asset_ids][:100]

        assets = Asset.query.filter(Asset.id.in_(asset_ids)).all()
        allowed = []
        for asset in assets:
            if asset.status == 'deleted':
                continue
            is_owner = user.id in (asset.creator_id, asset.owner_id, asset.uploader_id)
            if asset.status == 'published' or is_owner or _is_admin(user):
                allowed.append(asset)

        existing = {
            item.asset_id for item in collection.items.filter(
                CollectionAsset.asset_id.in_([asset.id for asset in allowed])
            ).all()
        }
        added = 0
        for asset in allowed:
            if asset.id in existing:
                continue
            db.session.add(CollectionAsset(
                collection_id=collection.id,
                asset_id=asset.id
            ))
            added += 1
        db.session.commit()

        return {
            'code': 200,
            'message': f'已加入 {added} 件资产',
            'data': {
                'added': added,
                'skipped': len(asset_ids) - added,
                'asset_count': collection.items.count()
            }
        }, 200


class CollectionAssetResource(Resource):
    """从合集移除单件资产"""

    @jwt_required()
    def delete(self, collection_id, asset_id):
        user = _current_user()
        collection = Collection.query.get(collection_id)
        if not collection:
            return {'code': 404, 'message': '合集不存在'}, 404
        if not _can_edit(collection, user):
            return {'code': 403, 'message': '无权编辑该合集'}, 403

        item = collection.items.filter_by(asset_id=asset_id).first()
        if not item:
            return {'code': 404, 'message': '该资产不在合集中'}, 404

        db.session.delete(item)
        db.session.commit()
        return {
            'code': 200,
            'message': '已从合集移除',
            'data': {'asset_count': collection.items.count()}
        }, 200
