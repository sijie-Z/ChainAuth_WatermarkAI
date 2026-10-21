"""操作日志查询（管理员）"""
from datetime import datetime, timedelta

from flask import request
from flask_jwt_extended import get_jwt_identity, jwt_required
from flask_restful import Resource

from app.models import OperationLog, User

ADMIN_ROLES = ('admin', 'asset_admin', 'license_admin', 'adm1', 'adm2')
MODULES = ('asset', 'watermark', 'blockchain', 'license', 'auth', 'user', 'garden')


class LogListResource(Resource):
    """分页查询操作日志"""

    @jwt_required()
    def get(self):
        user = User.query.get(get_jwt_identity())
        if not user or user.role not in ADMIN_ROLES:
            return {'code': 403, 'message': '无权限查看操作日志'}, 403

        page = max(request.args.get('page', 1, type=int), 1)
        per_page = min(max(request.args.get('per_page', 20, type=int), 1), 100)
        module = (request.args.get('module') or '').strip()
        action = (request.args.get('action') or '').strip()
        status = (request.args.get('status') or '').strip()
        keyword = (request.args.get('keyword') or '').strip()
        date_from = (request.args.get('date_from') or '').strip()
        date_to = (request.args.get('date_to') or '').strip()

        query = OperationLog.query
        if module:
            if module not in MODULES:
                return {'code': 400, 'message': '无效的模块'}, 400
            query = query.filter_by(module=module)
        if action:
            query = query.filter(OperationLog.action == action)
        if status in ('success', 'failed'):
            query = query.filter_by(status=status)
        if keyword:
            query = query.filter(OperationLog.description.ilike(f'%{keyword}%'))
        if date_from:
            try:
                query = query.filter(OperationLog.created_at >= datetime.fromisoformat(date_from))
            except ValueError:
                return {'code': 400, 'message': '开始日期格式无效'}, 400
        if date_to:
            try:
                end = datetime.fromisoformat(date_to)
                # 只给日期时按“当天结束”处理，避免漏掉结束日当天的日志
                if len(date_to) == 10:
                    end += timedelta(days=1)
                    query = query.filter(OperationLog.created_at < end)
                else:
                    query = query.filter(OperationLog.created_at <= end)
            except ValueError:
                return {'code': 400, 'message': '结束日期格式无效'}, 400

        pagination = query.order_by(OperationLog.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )

        items = []
        for log in pagination.items:
            data = log.to_dict()
            # 普通管理员页面不展示完整 UA，只保留审计需要的字段
            data['user_role'] = log.user_role
            items.append(data)

        return {
            'code': 200,
            'data': {
                'items': items,
                'total': pagination.total,
                'page': page,
                'per_page': per_page,
                'pages': pagination.pages,
            }
        }, 200
