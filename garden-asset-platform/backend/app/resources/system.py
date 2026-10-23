"""系统能力状态

把“哪些能力真实可用、哪些是演示/未启用”集中返回给后台，
避免界面把模拟存证或未部署 AI 当成真实能力展示。
"""
from flask import current_app, request
from flask_jwt_extended import get_jwt_identity, jwt_required
from flask_restful import Resource

from app.models import NotificationDelivery, User
from app.services.ai_service import ai_service
from app.services.blockchain_service import blockchain_service
from app.services.email_service import delivery_counts, mail_configured
from app.services.task_service import task_counts
from app.services.webhook_service import (
    config_for_api as webhook_config_for_api,
    get_webhook_config,
    save_webhook_config,
    send_test_webhook,
    webhook_delivery_counts,
)

ADMIN_ROLES = ('admin', 'asset_admin', 'license_admin', 'adm1', 'adm2')


class SystemStatusResource(Resource):
    """当前部署的能力状态（管理员）"""

    @jwt_required()
    def get(self):
        user = User.query.get(get_jwt_identity())
        if not user or user.role not in ADMIN_ROLES:
            return {'code': 403, 'message': '无权限查看系统状态'}, 403

        ai_enabled = bool(getattr(ai_service, 'enabled', False))
        chain_enabled = bool(getattr(blockchain_service, 'enabled', False))
        redis_client = current_app.extensions.get('redis')
        scheduler_enabled = bool(current_app.config.get('SCHEDULER_ENABLED', False))
        worker_enabled = bool(current_app.config.get('TASK_WORKER_ENABLED', False))
        counts = task_counts()
        mail_ready = mail_configured()
        deliveries = delivery_counts()
        webhook_config = webhook_config_for_api()
        webhook_deliveries = webhook_delivery_counts()

        return {
            'code': 200,
            'data': {
                'ai': {
                    'enabled': ai_enabled,
                    'label': '已启用' if ai_enabled else '未启用',
                    'description': (
                        '模型与 API Key 已加载'
                        if ai_enabled else
                        '需安装可选模型依赖并配置 ZHIPU_API_KEY'
                    )
                },
                'blockchain': {
                    'enabled': chain_enabled,
                    'simulated': not chain_enabled,
                    'label': 'FISCO BCOS 已连接' if chain_enabled else '本地模拟存证',
                    'description': (
                        '存证会写入真实联盟链节点'
                        if chain_enabled else
                        '交易哈希与区块为本地模拟数据，不能用于链上复核'
                    )
                },
                'redis': {
                    'enabled': bool(redis_client),
                    'label': 'Redis 已连接' if redis_client else '内存限流降级',
                    'description': (
                        '限流与缓存使用 Redis'
                        if redis_client else
                        'Redis 不可用，限流退化为单进程内存计数'
                    )
                },
                'scheduler': {
                    'enabled': scheduler_enabled,
                    'label': '调度器已启用' if scheduler_enabled else '调度器未启用',
                    'description': (
                        '备份、授权到期与清理任务会定时执行'
                        if scheduler_enabled else
                        '备份/过期检查需要手动执行或由外部 cron 触发'
                    )
                },
                'tasks': {
                    'enabled': worker_enabled,
                    'label': '异步 worker 运行中' if worker_enabled else '异步 worker 未启用',
                    'description': (
                        '水印与存证任务由后台 worker 领取执行'
                        if worker_enabled else
                        '任务会留在队列，需运行 flask tasks run 或开启 TASK_WORKER_ENABLED'
                    ),
                    'counts': counts
                },
                'notifications': {
                    'sse_enabled': bool(
                        current_app.config.get('SSE_ENABLED', True)
                    ),
                    'mail_configured': mail_ready,
                    'label': (
                        '邮件通知已配置' if mail_ready else '邮件通知未配置'
                    ),
                    'description': (
                        '事件通知可通过 SMTP 发送给开启邮件偏好的用户'
                        if mail_ready else
                        '站内 SSE 可用；配置 MAIL_ENABLED/MAIL_HOST 后可发送邮件'
                    ),
                    'deliveries': deliveries
                },
                'webhook': {
                    **webhook_config,
                    'label': (
                        'Webhook 已启用' if webhook_config['enabled']
                        else 'Webhook 未启用'
                    ),
                    'deliveries': webhook_deliveries
                }
            }
        }, 200


WEBHOOK_GROUP_OPTIONS = [
    {'key': 'asset', 'label': '资产审核结果'},
    {'key': 'license', 'label': '授权审批、撤销与续期'},
    {'key': 'task', 'label': '水印/存证任务结果'},
    {'key': 'infringement', 'label': '侵权线索与处理结果'},
]


class NotificationWebhookResource(Resource):
    """系统 Webhook 配置（仅超级管理员）"""

    @jwt_required()
    def get(self):
        user = User.query.get(get_jwt_identity())
        if not user or user.role != 'admin':
            return {'code': 403, 'message': '仅超级管理员可配置 Webhook'}, 403
        recent = NotificationDelivery.query.filter_by(
            channel='webhook'
        ).order_by(NotificationDelivery.id.desc()).limit(10).all()
        return {
            'code': 200,
            'data': {
                'config': webhook_config_for_api(),
                'groups': WEBHOOK_GROUP_OPTIONS,
                'deliveries': webhook_delivery_counts(),
                'recent': [
                    {
                        **row.to_dict(),
                        'event_title': (
                            row.event.title if row.event else None
                        ),
                    }
                    for row in recent
                ],
            }
        }, 200

    @jwt_required()
    def put(self):
        user = User.query.get(get_jwt_identity())
        if not user or user.role != 'admin':
            return {'code': 403, 'message': '仅超级管理员可配置 Webhook'}, 403
        data = request.get_json(silent=True) or {}
        error = save_webhook_config(data)
        if error:
            return {'code': 400, 'message': error}, 400
        return {
            'code': 200,
            'message': 'Webhook 配置已保存',
            'data': webhook_config_for_api(),
        }, 200


class NotificationWebhookTestResource(Resource):
    """发送测试 Webhook"""

    @jwt_required()
    def post(self):
        user = User.query.get(get_jwt_identity())
        if not user or user.role != 'admin':
            return {'code': 403, 'message': '仅超级管理员可测试 Webhook'}, 403
        config = get_webhook_config()
        if not config['enabled'] or not config['url']:
            return {'code': 400, 'message': '请先启用并保存 Webhook 地址'}, 400
        try:
            send_test_webhook(config)
        except ValueError as exc:
            return {'code': 400, 'message': str(exc)}, 400
        except Exception as exc:
            current_app.logger.warning('测试 Webhook 失败: %s', exc)
            return {'code': 502, 'message': f'Webhook 发送失败: {exc}'}, 502
        return {'code': 200, 'message': '测试 Webhook 已发送'}, 200
