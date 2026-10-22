"""站内待办提醒、通知偏好与实时推送

待办不单独存通知正文：按当前用户角色与业务状态实时汇总。
事件通知写入 notification_events 后，可通过 SSE 实时推送到已登录页面；
邮件投递由 notification_deliveries + 后台 worker 完成。
"""
import json
import threading
import time
from datetime import datetime, timedelta

from flask import current_app, request, Response, stream_with_context
from flask_jwt_extended import get_jwt_identity, jwt_required
from flask_restful import Resource

from app.extensions import db
from app.models import (
    Asset, AssetComment, InfringementReport, License, LicenseApplication,
    NotificationEvent, NotificationPreference, NotificationRead, User
)
from app.services.email_service import mail_configured, send_test_email
from app.utils.middleware import rate_limit
from sqlalchemy import or_

ADMIN_ROLES = ('admin', 'asset_admin', 'license_admin', 'adm1', 'adm2')
EMAIL_GROUPS = ('asset', 'license', 'task', 'infringement')
DEFAULT_EMAIL_GROUPS = ['asset', 'license', 'task', 'infringement']

_sse_connections = {}
_sse_lock = threading.Lock()


def _build_items(user):
    items = []
    now = datetime.utcnow()
    user_id = user.id

    # 事件型通知：审核结果、授权撤销/续期等，保留正文
    recent_events = NotificationEvent.query.filter_by(user_id=user_id).order_by(
        NotificationEvent.created_at.desc()
    ).limit(10).all()
    for event in recent_events:
        warning = any(token in event.event_type for token in ('rejected', 'revoked'))
        items.append({
            'id': f'event-{event.id}',
            'key': f'event-{event.id}',
            'type': 'warning' if warning else 'info',
            'title': event.title,
            'description': event.description or '',
            'link': event.link or '/home',
            'count': 1,
            'time': event.created_at.isoformat() if event.created_at else None
        })

    if user.role in ADMIN_ROLES:
        pending_licenses = LicenseApplication.query.filter(
            LicenseApplication.status.in_(['pending', 'adm1_approved'])
        ).count()
        if pending_licenses:
            items.append({
                'id': f'pending-licenses-{pending_licenses}',
                'key': f'pending-licenses-{pending_licenses}',
                'type': 'approval',
                'title': f'{pending_licenses} 条授权申请待审批',
                'description': '一级审批与二级复核会在这里汇总',
                'link': '/admin/license/pending',
                'count': pending_licenses,
                'time': None
            })

        pending_assets = Asset.query.filter_by(status='pending').count()
        if pending_assets:
            items.append({
                'id': f'pending-assets-{pending_assets}',
                'key': f'pending-assets-{pending_assets}',
                'type': 'asset',
                'title': f'{pending_assets} 件资产待发布审核',
                'description': '审核通过后资产才会进入公开档案',
                'link': '/admin/assets?status=pending',
                'count': pending_assets,
                'time': None
            })

        pending_reports = InfringementReport.query.filter(
            InfringementReport.status.in_(['pending', 'reviewing'])
        ).count()
        if pending_reports:
            items.append({
                'id': f'pending-infringements-{pending_reports}',
                'key': f'pending-infringements-{pending_reports}',
                'type': 'warning',
                'title': f'{pending_reports} 条侵权线索待处理',
                'description': '核实疑似盗用并确认或驳回',
                'link': '/admin/infringements',
                'count': pending_reports,
                'time': None
            })

    applications = LicenseApplication.query.filter(
        LicenseApplication.applicant_id == user_id,
        LicenseApplication.status.in_(['pending', 'adm1_approved', 'rejected'])
    ).order_by(
        LicenseApplication.updated_at.desc(), LicenseApplication.created_at.desc()
    ).limit(5).all()

    for application in applications:
        asset_title = application.asset.title if application.asset else '资产'
        if application.status == 'pending':
            title = '授权申请待一级审批'
            description = f'{asset_title} · 已提交，等待审批员处理'
            item_type = 'info'
        elif application.status == 'adm1_approved':
            title = '授权申请待二级复核'
            description = f'{asset_title} · 一级审批已通过'
            item_type = 'info'
        else:
            title = '授权申请未通过'
            description = (
                f'{asset_title} · '
                f'{application.adm2_review_comment or application.adm1_review_comment or "请查看申请详情"}'
            )
            item_type = 'warning'
        items.append({
            'id': f'application-{application.id}-{application.status}',
            'key': f'application-{application.id}-{application.status}',
            'type': item_type,
            'title': title,
            'description': description,
            'link': '/license/my?tab=pending' if application.status != 'rejected' else '/license/my?tab=rejected',
            'count': 1,
            'time': (application.updated_at or application.created_at).isoformat()
        })

    expiring = License.query.filter(
        License.licensee_id == user_id,
        License.status == 'active',
        License.end_time.isnot(None),
        License.end_time >= now,
        License.end_time <= now + timedelta(days=30)
    ).order_by(License.end_time.asc()).limit(5).all()

    for license in expiring:
        end_key = license.end_time.strftime('%Y%m%d') if license.end_time else 'unknown'
        items.append({
            'id': f'license-{license.id}-{end_key}',
            'key': f'license-{license.id}-{end_key}',
            'type': 'warning',
            'title': '授权即将到期',
            'description': (
                f'{license.asset.title if license.asset else "资产"} · '
                f'{license.end_time:%Y-%m-%d} 到期'
            ),
            'link': '/license/my',
            'count': 1,
            'time': license.end_time.isoformat()
        })

    # 自己拥有的资产收到新评论（排除自己发的评论）
    owned_asset_ids = db.session.query(Asset.id).filter(
        or_(
            Asset.owner_id == user_id,
            Asset.creator_id == user_id,
            Asset.uploader_id == user_id
        ),
        Asset.status != 'deleted'
    ).subquery()
    recent_comments = AssetComment.query.filter(
        AssetComment.asset_id.in_(db.session.query(owned_asset_ids.c.id)),
        AssetComment.user_id != user_id,
        AssetComment.is_deleted.is_(False)
    ).order_by(AssetComment.created_at.desc()).limit(5).all()

    for comment in recent_comments:
        asset = comment.asset
        author = comment.user
        author_name = (author.nickname or author.username) if author else '用户'
        snippet = (comment.content or '').strip().replace('\n', ' ')
        if len(snippet) > 60:
            snippet = snippet[:60] + '…'
        items.append({
            'id': f'comment-{comment.id}',
            'key': f'comment-{comment.id}',
            'type': 'info',
            'title': f'{author_name} 评论了你的资产',
            'description': f'{asset.title if asset else "资产"} · {snippet}',
            'link': f'/assets/{comment.asset_id}?tab=comments',
            'count': 1,
            'time': comment.created_at.isoformat() if comment.created_at else None
        })

    keys = [item['key'] for item in items]
    read_keys = set()
    if keys:
        read_keys = {
            row.notification_key
            for row in NotificationRead.query.filter(
                NotificationRead.user_id == user_id,
                NotificationRead.notification_key.in_(keys)
            ).all()
        }

    for item in items:
        item['read'] = item['key'] in read_keys

    return items


class NotificationsResource(Resource):
    """当前用户的待办与状态提醒"""

    @jwt_required()
    def get(self):
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        if not user:
            return {'code': 404, 'message': '用户不存在'}, 404

        items = _build_items(user)
        unread_items = [item for item in items if not item['read']]
        return {
            'code': 200,
            'data': {
                'count': sum(item.get('count', 1) for item in items),
                'unread_count': sum(item.get('count', 1) for item in unread_items),
                'items': items
            }
        }, 200


class NotificationReadResource(Resource):
    """标记待办已读"""

    @jwt_required()
    def post(self):
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        if not user:
            return {'code': 404, 'message': '用户不存在'}, 404

        data = request.get_json(silent=True) or {}
        mark_all = bool(data.get('all'))
        keys = data.get('keys') or []

        if not mark_all:
            if not isinstance(keys, list):
                return {'code': 400, 'message': 'keys 必须是数组'}, 400
            keys = [str(key)[:120] for key in keys if key][:50]
            if not keys:
                return {'code': 400, 'message': '缺少待办 key'}, 400
        else:
            keys = [item['key'] for item in _build_items(user)]

        existing = {
            row.notification_key
            for row in NotificationRead.query.filter(
                NotificationRead.user_id == user_id,
                NotificationRead.notification_key.in_(keys)
            ).all()
        } if keys else set()

        for key in keys:
            if key not in existing:
                db.session.add(NotificationRead(
                    user_id=user_id,
                    notification_key=key
                ))
        db.session.commit()

        items = _build_items(user)
        unread_items = [item for item in items if not item['read']]
        return {
            'code': 200,
            'message': '已标记为已读',
            'data': {
                'unread_count': sum(item.get('count', 1) for item in unread_items)
            }
        }, 200


class NotificationPreferenceResource(Resource):
    """当前用户的邮件通知偏好"""

    @jwt_required()
    def get(self):
        user = User.query.get(get_jwt_identity())
        if not user:
            return {'code': 404, 'message': '用户不存在'}, 404
        preference = NotificationPreference.query.filter_by(user_id=user.id).first()
        data = preference.to_dict() if preference else {
            'email_enabled': False,
            'email_groups': DEFAULT_EMAIL_GROUPS,
            'email': user.email,
            'updated_at': None,
        }
        data['email'] = user.email
        data['mail_configured'] = mail_configured()
        data['sse_enabled'] = bool(current_app.config.get('SSE_ENABLED', True))
        data['available_groups'] = [
            {'key': 'asset', 'label': '资产审核结果'},
            {'key': 'license', 'label': '授权审批、撤销与续期'},
            {'key': 'task', 'label': '水印/存证任务结果'},
            {'key': 'infringement', 'label': '侵权线索与处理结果'},
        ]
        return {'code': 200, 'data': data}, 200

    @jwt_required()
    def put(self):
        user = User.query.get(get_jwt_identity())
        if not user:
            return {'code': 404, 'message': '用户不存在'}, 404

        data = request.get_json(silent=True) or {}
        email_enabled = bool(data.get('email_enabled'))
        groups = data.get('email_groups', DEFAULT_EMAIL_GROUPS)
        if not isinstance(groups, list):
            return {'code': 400, 'message': 'email_groups 必须是数组'}, 400
        groups = [str(item) for item in groups if item]
        invalid = [item for item in groups if item not in EMAIL_GROUPS]
        if invalid:
            return {'code': 400, 'message': '存在无效的通知分组'}, 400
        if email_enabled and not user.email:
            return {'code': 400, 'message': '请先在个人信息中填写邮箱'}, 400

        preference = NotificationPreference.query.filter_by(user_id=user.id).first()
        if not preference:
            preference = NotificationPreference(user_id=user.id)
            db.session.add(preference)
        preference.email_enabled = email_enabled
        preference.email_groups = groups
        db.session.commit()

        return {
            'code': 200,
            'message': '通知偏好已保存',
            'data': preference.to_dict()
        }, 200


class NotificationTestEmailResource(Resource):
    """向当前用户邮箱发送测试邮件"""

    @rate_limit(limit=3, window=60)
    @jwt_required()
    def post(self):
        user = User.query.get(get_jwt_identity())
        if not user:
            return {'code': 404, 'message': '用户不存在'}, 404
        if not mail_configured():
            return {
                'code': 503,
                'message': 'SMTP 未配置，请先在服务端设置 MAIL_ENABLED 等环境变量'
            }, 503
        try:
            send_test_email(user)
        except ValueError as exc:
            return {'code': 400, 'message': str(exc)}, 400
        except Exception as exc:
            current_app.logger.warning('测试邮件发送失败: %s', exc)
            return {'code': 500, 'message': '测试邮件发送失败，请检查 SMTP 配置'}, 500
        return {'code': 200, 'message': f'测试邮件已发送至 {user.email}'}, 200


class NotificationStreamResource(Resource):
    """SSE 实时通知流

    使用 Authorization 头鉴权，前端通过 fetch + ReadableStream 消费。
    每 5 秒检查一次数据库中的新事件，心跳保活，连接最长保持配置的秒数。
    """

    @jwt_required()
    def get(self):
        if not current_app.config.get('SSE_ENABLED', True):
            return {'code': 503, 'message': '实时通知未启用'}, 503

        user_id = get_jwt_identity()
        app = current_app._get_current_object()
        max_seconds = int(app.config.get('SSE_MAX_SECONDS', 300))
        interval = max(0.2, float(app.config.get('SSE_POLL_INTERVAL', 5)))
        max_connections = int(
            app.config.get('SSE_MAX_CONNECTIONS_PER_USER', 3)
        )

        with _sse_lock:
            current = _sse_connections.get(user_id, 0)
            if current >= max_connections:
                return {
                    'code': 429,
                    'message': '实时通知连接数过多，请关闭多余页面后重试'
                }, 429
            _sse_connections[user_id] = current + 1

        since_arg = request.args.get('since_id', type=int)
        if since_arg is None:
            latest = NotificationEvent.query.filter_by(user_id=user_id).order_by(
                NotificationEvent.id.desc()
            ).first()
            since_id = latest.id if latest else 0
        else:
            since_id = max(0, since_arg)

        def generate():
            last_id = since_id
            started = time.time()
            try:
                yield 'retry: 5000\n\n'
                while time.time() - started < max_seconds:
                    payloads = []
                    try:
                        events = NotificationEvent.query.filter(
                            NotificationEvent.user_id == user_id,
                            NotificationEvent.id > last_id,
                        ).order_by(NotificationEvent.id.asc()).limit(50).all()
                        payloads = [event.to_dict() for event in events]
                        db.session.remove()
                    except Exception:
                        db.session.rollback()
                        db.session.remove()
                        app.logger.exception('SSE 读取通知事件失败')

                    for payload in payloads:
                        last_id = max(last_id, payload['id'])
                        yield (
                            f"id: {payload['id']}\n"
                            'event: notification\n'
                            f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
                        )
                    yield ': heartbeat\n\n'
                    time.sleep(interval)

                yield 'event: close\ndata: {}\n\n'
            finally:
                with _sse_lock:
                    remaining = _sse_connections.get(user_id, 1) - 1
                    if remaining > 0:
                        _sse_connections[user_id] = remaining
                    else:
                        _sse_connections.pop(user_id, None)

        return Response(
            stream_with_context(generate()),
            mimetype='text/event-stream',
            headers={
                'Cache-Control': 'no-cache',
                'X-Accel-Buffering': 'no',
                'Connection': 'keep-alive',
            },
        )
