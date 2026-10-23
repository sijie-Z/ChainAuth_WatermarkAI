"""异步任务查询与重试 API"""
from flask_jwt_extended import get_jwt_identity, jwt_required
from flask_restful import Resource
from flask import current_app, request

from app.extensions import db
from app.models.asset import Asset
from app.models.task import AsyncTask
from app.models.user import User
from app.services import task_service

ADMIN_ROLES = ('admin', 'asset_admin')


def _can_view_task(user, task):
    if not user:
        return False
    if user.role in ADMIN_ROLES or task.user_id == user.id:
        return True
    asset = Asset.query.get(task.asset_id) if task.asset_id else None
    return bool(asset and user.id in (
        asset.creator_id, asset.owner_id, asset.uploader_id
    ))


def _can_manage_asset(user, asset):
    if not user:
        return False
    return user.role in ADMIN_ROLES or user.id in (
        asset.creator_id, asset.owner_id, asset.uploader_id
    )


class TaskListResource(Resource):
    """我的任务 / 某件资产的任务"""

    @jwt_required()
    def get(self):
        user = User.query.get(get_jwt_identity())
        if not user:
            return {'code': 401, 'message': '用户不存在'}, 401

        asset_id = request.args.get('asset_id')
        status = request.args.get('status')

        query = AsyncTask.query
        if asset_id:
            asset = Asset.query.get(asset_id)
            if not asset:
                return {'code': 404, 'message': '资产不存在'}, 404
            if not _can_manage_asset(user, asset):
                return {'code': 403, 'message': '无权查看该资产的任务'}, 403
            query = query.filter(AsyncTask.asset_id == asset_id)
        elif user.role not in ADMIN_ROLES:
            query = query.filter(AsyncTask.user_id == user.id)

        if status:
            allowed = {'queued', 'running', 'succeeded', 'failed', 'cancelled'}
            if status not in allowed:
                return {'code': 400, 'message': '无效的任务状态'}, 400
            query = query.filter(AsyncTask.status == status)

        tasks = query.order_by(AsyncTask.created_at.desc()).limit(100).all()
        return {
            'code': 200,
            'data': {
                'items': [task.to_dict() for task in tasks],
                'total': len(tasks),
                'worker_enabled': bool(
                    current_app.config.get('TASK_WORKER_ENABLED', False)
                )
            }
        }, 200


class TaskHealthResource(Resource):
    """队列健康度、worker 心跳与积压告警（管理员）"""

    @jwt_required()
    def get(self):
        user = User.query.get(get_jwt_identity())
        if not user or user.role not in ADMIN_ROLES:
            return {'code': 403, 'message': '无权限查看队列健康度'}, 403
        health = task_service.queue_health()
        health['worker_enabled'] = bool(
            current_app.config.get('TASK_WORKER_ENABLED', False)
        )
        return {'code': 200, 'data': health}, 200


class TaskResource(Resource):
    """任务详情"""

    @jwt_required()
    def get(self, task_id):
        user = User.query.get(get_jwt_identity())
        task = AsyncTask.query.get(task_id)
        if not task:
            return {'code': 404, 'message': '任务不存在'}, 404
        if not _can_view_task(user, task):
            return {'code': 404, 'message': '任务不存在'}, 404
        return {'code': 200, 'data': task.to_dict(include_payload=True)}, 200


class TaskRetryResource(Resource):
    """手动重试失败任务"""

    @jwt_required()
    def post(self, task_id):
        user = User.query.get(get_jwt_identity())
        task = AsyncTask.query.get(task_id)
        if not task:
            return {'code': 404, 'message': '任务不存在'}, 404
        if not _can_view_task(user, task):
            return {'code': 404, 'message': '任务不存在'}, 404
        if task.status not in ('failed', 'cancelled'):
            return {'code': 400, 'message': '只有失败或已取消的任务可以重试'}, 400

        if not task_service.retry_task(task):
            return {'code': 400, 'message': '任务状态已变化，请刷新后重试'}, 400

        return {
            'code': 200,
            'message': '任务已重新排队',
            'data': task.to_dict()
        }, 200


class TaskCancelResource(Resource):
    """取消排队中的任务"""

    @jwt_required()
    def post(self, task_id):
        user = User.query.get(get_jwt_identity())
        task = AsyncTask.query.get(task_id)
        if not task:
            return {'code': 404, 'message': '任务不存在'}, 404
        if not _can_view_task(user, task):
            return {'code': 404, 'message': '任务不存在'}, 404
        if not task_service.cancel_task(task):
            return {'code': 400, 'message': '只有排队中的任务可以取消'}, 400
        return {'code': 200, 'message': '任务已取消', 'data': task.to_dict()}, 200
