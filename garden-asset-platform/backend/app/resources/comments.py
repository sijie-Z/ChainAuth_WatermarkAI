"""资产评论 API

可见性与资产详情保持一致：
- 已发布资产：所有登录用户可读可评；
- 草稿/待审/驳回：仅 creator/owner/uploader 与 admin/asset_admin 可见；
- 已删除：仅 admin/asset_admin 可见。
不可见统一返回 404，避免泄露资产状态。
"""
from flask import request
from flask_jwt_extended import get_jwt_identity, jwt_required
from flask_restful import Resource

from app.extensions import db
from app.models.asset import Asset
from app.models.comment import AssetComment
from app.models.user import User
from app.utils.middleware import rate_limit

COMMENT_ADMIN_ROLES = ('admin', 'asset_admin')
COMMENT_MAX_LENGTH = 2000
COMMENT_DEFAULT_PER_PAGE = 20
COMMENT_MAX_PER_PAGE = 100


def current_user():
    """当前登录用户；身份由 JWT 注入"""
    return db.session.get(User, get_jwt_identity())


def is_admin(user):
    return bool(user and user.role in COMMENT_ADMIN_ROLES)


def is_asset_owner(user_id, asset):
    return user_id in (asset.creator_id, asset.owner_id, asset.uploader_id)


def can_view_asset(user, user_id, asset):
    """与资产详情一致：已发布公开；未发布仅所有者/管理员；已删除仅管理员"""
    if not user:
        return False
    if asset.status == 'deleted':
        return is_admin(user)
    if asset.status == 'published':
        return True
    return is_admin(user) or is_asset_owner(user_id, asset)


def author_name(user):
    if not user:
        return None
    return user.nickname or user.username


def _reply_to_name(parent):
    """父评论被删除时不再暴露其作者名"""
    if not parent or parent.is_deleted:
        return None
    return author_name(parent.user)


def comment_payload(comment, viewer, reply_to_name_value=None):
    """评论序列化（resource 层统一输出结构）"""
    return {
        'id': comment.id,
        'asset_id': comment.asset_id,
        'user_id': comment.user_id,
        'parent_id': comment.parent_id,
        'content': comment.content,
        'author_name': author_name(comment.user),
        'author_role': comment.user.role if comment.user else None,
        'is_own': bool(viewer and comment.user_id == viewer.id),
        'can_delete': bool(
            viewer and (comment.user_id == viewer.id or is_admin(viewer))
        ),
        'created_at': comment.created_at.isoformat() if comment.created_at else None,
        'updated_at': comment.updated_at.isoformat() if comment.updated_at else None,
        'reply_to_name': reply_to_name_value,
    }


def _get_visible_asset(asset_id, user):
    """返回 (asset, error_response)；不可见与不存在同样按 404 处理"""
    asset = db.session.get(Asset, asset_id)
    if not asset or not can_view_asset(user, user.id if user else None, asset):
        return None, ({'code': 404, 'message': '资产不存在'}, 404)
    return asset, None


def _get_comment(asset_id, comment_id):
    comment = db.session.get(AssetComment, comment_id)
    if not comment or comment.asset_id != asset_id:
        return None
    return comment


def _validated_content(data):
    content = data.get('content')
    if not isinstance(content, str) or not content.strip():
        return None, '评论内容不能为空'
    content = content.strip()
    if len(content) > COMMENT_MAX_LENGTH:
        return None, f'评论内容不能超过{COMMENT_MAX_LENGTH}字'
    return content, None


class AssetCommentListResource(Resource):
    """资产评论列表 / 发表评论"""

    @jwt_required()
    def get(self, asset_id):
        user = current_user()
        asset, error = _get_visible_asset(asset_id, user)
        if error:
            return error

        page = max(request.args.get('page', 1, type=int), 1)
        per_page = min(
            max(request.args.get('per_page', COMMENT_DEFAULT_PER_PAGE, type=int), 1),
            COMMENT_MAX_PER_PAGE
        )

        query = AssetComment.query.filter_by(
            asset_id=asset.id, is_deleted=False
        ).order_by(
            AssetComment.created_at.asc(), AssetComment.id.asc()
        )
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)

        # 批量取父评论，避免逐条加载
        parent_ids = {item.parent_id for item in pagination.items if item.parent_id}
        parents = {}
        if parent_ids:
            parents = {
                parent.id: parent
                for parent in AssetComment.query.filter(
                    AssetComment.id.in_(parent_ids)
                ).all()
            }

        items = [
            comment_payload(
                item, user, _reply_to_name(parents.get(item.parent_id))
            )
            for item in pagination.items
        ]

        return {
            'code': 200,
            'data': {
                'items': items,
                'total': pagination.total,
                'page': page,
                'per_page': per_page,
                'pages': pagination.pages
            }
        }, 200

    @jwt_required()
    @rate_limit(limit=20, window=60)
    def post(self, asset_id):
        user = current_user()
        asset, error = _get_visible_asset(asset_id, user)
        if error:
            return error

        data = request.get_json(silent=True) or {}

        content, error_message = _validated_content(data)
        if error_message:
            return {'code': 400, 'message': error_message}, 400

        parent = None
        parent_id = data.get('parent_id')
        if parent_id is not None:
            try:
                parent_id = int(parent_id)
            except (TypeError, ValueError):
                return {'code': 400, 'message': '父评论无效'}, 400
            parent = db.session.get(AssetComment, parent_id)
            if not parent or parent.asset_id != asset.id or parent.is_deleted:
                return {'code': 400, 'message': '父评论不存在或已删除'}, 400

        comment = AssetComment(
            asset_id=asset.id,
            user_id=user.id,
            parent_id=parent.id if parent else None,
            content=content
        )
        db.session.add(comment)
        db.session.commit()

        return {
            'code': 200,
            'message': '评论已发布',
            'data': comment_payload(comment, user, _reply_to_name(parent))
        }, 200


class AssetCommentResource(Resource):
    """编辑 / 删除单条评论"""

    @jwt_required()
    def put(self, asset_id, comment_id):
        user = current_user()
        asset = db.session.get(Asset, asset_id)
        if not asset:
            return {'code': 404, 'message': '资产不存在'}, 404

        comment = _get_comment(asset.id, comment_id)
        if not comment or comment.is_deleted:
            return {'code': 404, 'message': '评论不存在'}, 404

        if not user or not (comment.user_id == user.id or is_admin(user)):
            return {'code': 403, 'message': '无权限修改评论'}, 403

        data = request.get_json(silent=True) or {}
        content, error_message = _validated_content(data)
        if error_message:
            return {'code': 400, 'message': error_message}, 400

        comment.content = content
        db.session.commit()

        parent = comment.parent
        return {
            'code': 200,
            'message': '评论已更新',
            'data': comment_payload(comment, user, _reply_to_name(parent))
        }, 200

    @jwt_required()
    def delete(self, asset_id, comment_id):
        user = current_user()
        asset = db.session.get(Asset, asset_id)
        if not asset:
            return {'code': 404, 'message': '资产不存在'}, 404

        comment = _get_comment(asset.id, comment_id)
        if not comment:
            return {'code': 404, 'message': '评论不存在'}, 404

        if not user or not (comment.user_id == user.id or is_admin(user)):
            return {'code': 403, 'message': '无权限删除评论'}, 403

        # 软删除，重复删除保持幂等
        if not comment.is_deleted:
            comment.is_deleted = True
            db.session.commit()

        return {'code': 200, 'message': '评论已删除'}, 200
