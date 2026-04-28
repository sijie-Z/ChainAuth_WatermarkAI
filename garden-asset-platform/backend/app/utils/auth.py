"""
JWT认证装饰器
"""
from functools import wraps
from flask import jsonify
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
from app.models.user import User


def admin_required():
    """管理员权限装饰器"""
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            verify_jwt_in_request()
            user_id = get_jwt_identity()
            user = User.query.get(user_id)

            if not user or user.role not in ['admin', 'super_admin']:
                return jsonify({
                    'code': 403,
                    'message': '需要管理员权限'
                }), 403

            return fn(*args, **kwargs)
        return wrapper
    return decorator


def role_required(*roles):
    """角色权限装饰器"""
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            verify_jwt_in_request()
            user_id = get_jwt_identity()
            user = User.query.get(user_id)

            if not user or user.role not in roles:
                return jsonify({
                    'code': 403,
                    'message': '权限不足'
                }), 403

            return fn(*args, **kwargs)
        return wrapper
    return decorator


def active_user_required():
    """活跃用户装饰器"""
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            verify_jwt_in_request()
            user_id = get_jwt_identity()
            user = User.query.get(user_id)

            if not user or user.status != 'active':
                return jsonify({
                    'code': 403,
                    'message': '账户已被禁用'
                }), 403

            return fn(*args, **kwargs)
        return wrapper
    return decorator