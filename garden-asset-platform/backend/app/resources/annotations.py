"""图纸/影像区域标注 API

标注以归一化坐标绑定到资产（可选绑定到具体版本）：
- 默认只返回“当前版本”（version_no 最大）的标注；
- all=1 返回全部版本，version_id 可指定某一历史版本；
- 仅 image/vector 类型资产支持标注，其他类型返回空列表。
权限：作者或管理员可改内容；仅资产所有者或管理员可改状态。
"""
from datetime import datetime

from flask import request
from flask_jwt_extended import jwt_required
from flask_restful import Resource

from app.extensions import db
from app.models.annotation import (
    ANNOTATION_STATUSES, ANNOTATION_TYPES, AssetAnnotation
)
from app.models.asset import Asset, AssetVersion
from app.resources.comments import (
    can_view_asset, current_user, is_admin, is_asset_owner
)
from app.utils.middleware import rate_limit

ANNOTATABLE_TYPES = ('image', 'vector')
MIN_ANNOTATION_SIZE = 0.004
WIDTH_SUM_TOLERANCE = 1.001
MAX_TITLE_LENGTH = 100
MAX_CONTENT_LENGTH = 2000


def _author_name(user):
    if not user:
        return None
    return user.nickname or user.username


def _current_version(asset_id):
    """当前版本 = version_no 最大的版本；无版本时返回 None"""
    return AssetVersion.query.filter_by(asset_id=asset_id).order_by(
        AssetVersion.version_no.desc(), AssetVersion.id.desc()
    ).first()


def _annotation_payload(annotation, viewer, asset):
    author = annotation.user
    resolver = annotation.resolver
    is_author = bool(viewer and annotation.user_id == viewer.id)
    admin = is_admin(viewer)
    owner = bool(viewer and is_asset_owner(viewer.id, asset))
    return {
        'id': annotation.id,
        'asset_id': annotation.asset_id,
        'version_id': annotation.version_id,
        'version_no': annotation.version.version_no if annotation.version else None,
        'x': annotation.x,
        'y': annotation.y,
        'width': annotation.width,
        'height': annotation.height,
        'title': annotation.title,
        'content': annotation.content,
        'annotation_type': annotation.annotation_type,
        'status': annotation.status,
        'author_name': _author_name(author),
        'created_at': annotation.created_at.isoformat() if annotation.created_at else None,
        'resolved_at': annotation.resolved_at.isoformat() if annotation.resolved_at else None,
        'resolver_name': _author_name(resolver),
        'is_own': is_author,
        'can_edit': bool(is_author or admin),
        'can_resolve': bool(owner or admin),
        'can_delete': bool(is_author or owner or admin),
    }


def _get_visible_asset(asset_id, user):
    asset = db.session.get(Asset, asset_id)
    if not asset or not can_view_asset(user, user.id if user else None, asset):
        return None, ({'code': 404, 'message': '资产不存在'}, 404)
    return asset, None


def _parse_coordinates(data):
    """校验并返回归一化坐标；width/height 需大于 0.004"""
    values = {}
    for key in ('x', 'y', 'width', 'height'):
        if data.get(key) is None:
            return None, f'缺少 {key} 坐标'
        try:
            values[key] = float(data[key])
        except (TypeError, ValueError):
            return None, f'{key} 必须是数字'

    if not 0 <= values['x'] <= 1 or not 0 <= values['y'] <= 1:
        return None, 'x/y 坐标必须在 0 到 1 之间'
    if values['width'] <= MIN_ANNOTATION_SIZE or values['height'] <= MIN_ANNOTATION_SIZE:
        return None, f'标注宽高必须大于 {MIN_ANNOTATION_SIZE}'
    if values['x'] + values['width'] > WIDTH_SUM_TOLERANCE:
        return None, '标注区域超出图像右边界'
    if values['y'] + values['height'] > 1:
        return None, '标注区域超出图像下边界'
    return values, None


def _validated_title(value):
    title = value.strip() if isinstance(value, str) else ''
    if not title:
        return None, '标注标题不能为空'
    if len(title) > MAX_TITLE_LENGTH:
        return None, f'标注标题不能超过{MAX_TITLE_LENGTH}字'
    return title, None


def _validated_content(value):
    """content 可为空；返回 (content, error)"""
    if value is None:
        return None, None
    if not isinstance(value, str):
        return None, '标注说明必须是文本'
    content = value.strip()
    if len(content) > MAX_CONTENT_LENGTH:
        return None, f'标注说明不能超过{MAX_CONTENT_LENGTH}字'
    return content or None, None


def _validated_annotation_type(value):
    annotation_type = value if isinstance(value, str) else ''
    if annotation_type not in ANNOTATION_TYPES:
        return None, '标注类型无效'
    return annotation_type, None


class AssetAnnotationListResource(Resource):
    """资产标注列表 / 新建标注"""

    @jwt_required()
    def get(self, asset_id):
        user = current_user()
        asset, error = _get_visible_asset(asset_id, user)
        if error:
            return error

        current_version = _current_version(asset.id)
        version_id = request.args.get('version_id', type=int)
        all_flag = (request.args.get('all') or '').strip().lower() in ('1', 'true', 'yes')

        if version_id is not None:
            version_filter = str(version_id)
        elif all_flag:
            version_filter = 'all'
        else:
            version_filter = 'current'

        empty_payload = {
            'items': [],
            'total': 0,
            'current_version_id': current_version.id if current_version else None,
            'current_version_no': current_version.version_no if current_version else None,
            'version_filter': version_filter,
        }

        # 非图纸/影像资产不支持标注，直接返回空列表
        if asset.asset_type not in ANNOTATABLE_TYPES:
            return {'code': 200, 'data': empty_payload}, 200

        query = AssetAnnotation.query.filter(AssetAnnotation.asset_id == asset.id)

        if version_id is not None:
            version = db.session.get(AssetVersion, version_id)
            if not version or version.asset_id != asset.id:
                return {'code': 404, 'message': '版本不存在'}, 404
            query = query.filter(AssetAnnotation.version_id == version.id)
        elif not all_flag:
            if current_version:
                query = query.filter(AssetAnnotation.version_id == current_version.id)
            else:
                query = query.filter(AssetAnnotation.version_id.is_(None))

        status = (request.args.get('status') or '').strip()
        if status:
            if status not in ANNOTATION_STATUSES:
                return {'code': 400, 'message': '无效的状态筛选'}, 400
            query = query.filter(AssetAnnotation.status == status)

        annotations = query.order_by(
            AssetAnnotation.created_at.asc(), AssetAnnotation.id.asc()
        ).all()

        return {
            'code': 200,
            'data': {
                'items': [
                    _annotation_payload(item, user, asset) for item in annotations
                ],
                'total': len(annotations),
                'current_version_id': current_version.id if current_version else None,
                'current_version_no': current_version.version_no if current_version else None,
                'version_filter': version_filter,
            }
        }, 200

    @jwt_required()
    @rate_limit(limit=30, window=60)
    def post(self, asset_id):
        user = current_user()
        asset, error = _get_visible_asset(asset_id, user)
        if error:
            return error

        if asset.asset_type not in ANNOTATABLE_TYPES:
            return {'code': 400, 'message': '该资产类型不支持标注'}, 400

        data = request.get_json(silent=True) or {}

        coordinates, error_message = _parse_coordinates(data)
        if error_message:
            return {'code': 400, 'message': error_message}, 400

        title, error_message = _validated_title(data.get('title'))
        if error_message:
            return {'code': 400, 'message': error_message}, 400

        content, error_message = _validated_content(data.get('content'))
        if error_message:
            return {'code': 400, 'message': error_message}, 400

        annotation_type = data.get('annotation_type') or 'note'
        annotation_type, error_message = _validated_annotation_type(annotation_type)
        if error_message:
            return {'code': 400, 'message': error_message}, 400

        # version_id 可选；缺省绑定当前版本（无版本时为未绑定）
        version_id = data.get('version_id')
        if version_id is not None:
            try:
                version_id = int(version_id)
            except (TypeError, ValueError):
                return {'code': 400, 'message': '版本无效'}, 400
            version = db.session.get(AssetVersion, version_id)
            if not version or version.asset_id != asset.id:
                return {'code': 400, 'message': '版本不属于该资产'}, 400
            version_id = version.id
        else:
            current_version = _current_version(asset.id)
            version_id = current_version.id if current_version else None

        annotation = AssetAnnotation(
            asset_id=asset.id,
            version_id=version_id,
            user_id=user.id,
            title=title,
            content=content,
            annotation_type=annotation_type,
            status='open',
            **coordinates
        )
        db.session.add(annotation)
        db.session.commit()

        return {
            'code': 200,
            'message': '标注已创建',
            'data': _annotation_payload(annotation, user, asset)
        }, 200


class AssetAnnotationResource(Resource):
    """编辑 / 解决 / 删除单条标注"""

    @jwt_required()
    def put(self, asset_id, annotation_id):
        user = current_user()
        asset = db.session.get(Asset, asset_id)
        if not asset:
            return {'code': 404, 'message': '资产不存在'}, 404

        annotation = db.session.get(AssetAnnotation, annotation_id)
        if not annotation or annotation.asset_id != asset.id:
            return {'code': 404, 'message': '标注不存在'}, 404

        data = request.get_json(silent=True) or {}
        recognized = {'title', 'content', 'annotation_type', 'status'}
        if not recognized.intersection(data.keys()):
            return {'code': 400, 'message': '没有可更新的字段'}, 400

        is_author = bool(user and annotation.user_id == user.id)
        admin = is_admin(user)
        owner = bool(user and is_asset_owner(user.id, asset))

        # title/content/annotation_type 仅作者或管理员可改
        if {'title', 'content', 'annotation_type'}.intersection(data.keys()):
            if not (is_author or admin):
                return {'code': 403, 'message': '无权限修改标注内容'}, 403

        # status 仅资产所有者或管理员可改（值未变化时不视为修改）
        new_status = data.get('status')
        if 'status' in data:
            if new_status not in ANNOTATION_STATUSES:
                return {'code': 400, 'message': '无效的标注状态'}, 400
            if new_status != annotation.status and not (owner or admin):
                return {'code': 403, 'message': '无权限修改标注状态'}, 403

        if 'title' in data:
            title, error_message = _validated_title(data.get('title'))
            if error_message:
                return {'code': 400, 'message': error_message}, 400
            annotation.title = title

        if 'content' in data:
            content, error_message = _validated_content(data.get('content'))
            if error_message:
                return {'code': 400, 'message': error_message}, 400
            annotation.content = content

        if 'annotation_type' in data:
            annotation_type, error_message = _validated_annotation_type(
                data.get('annotation_type')
            )
            if error_message:
                return {'code': 400, 'message': error_message}, 400
            annotation.annotation_type = annotation_type

        if 'status' in data:
            if new_status == 'resolved' and annotation.status != 'resolved':
                annotation.status = 'resolved'
                annotation.resolved_by = user.id
                annotation.resolved_at = datetime.utcnow()
            elif new_status == 'open':
                annotation.status = 'open'
                annotation.resolved_by = None
                annotation.resolved_at = None

        db.session.commit()

        return {
            'code': 200,
            'message': '标注已更新',
            'data': _annotation_payload(annotation, user, asset)
        }, 200

    @jwt_required()
    def delete(self, asset_id, annotation_id):
        user = current_user()
        asset = db.session.get(Asset, asset_id)
        if not asset:
            return {'code': 404, 'message': '资产不存在'}, 404

        annotation = db.session.get(AssetAnnotation, annotation_id)
        if not annotation or annotation.asset_id != asset.id:
            return {'code': 404, 'message': '标注不存在'}, 404

        is_author = bool(user and annotation.user_id == user.id)
        if not (is_author or is_asset_owner(user.id if user else None, asset) or is_admin(user)):
            return {'code': 403, 'message': '无权限删除标注'}, 403

        db.session.delete(annotation)
        db.session.commit()

        return {'code': 200, 'message': '标注已删除'}, 200
