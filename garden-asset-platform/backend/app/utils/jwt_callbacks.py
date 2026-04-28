"""
JWT回调函数配置
"""
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    get_jwt_identity,
    get_jwt
)
from app.extensions import jwt
from app.models.user import User


@jwt.user_identity_loader
def user_identity_lookup(user):
    """用户身份加载器"""
    return user.id if hasattr(user, 'id') else user


@jwt.user_lookup_loader
def user_lookup_callback(_jwt_header, jwt_data):
    """用户查找回调"""
    identity = jwt_data["sub"]
    return User.query.get(identity)


@jwt.expired_token_loader
def expired_token_callback(jwt_header, jwt_payload):
    """Token过期回调"""
    return {
        'code': 401,
        'message': 'Token已过期，请重新登录'
    }, 401


@jwt.invalid_token_loader
def invalid_token_callback(error):
    """无效Token回调"""
    return {
        'code': 401,
        'message': '无效的Token'
    }, 401


@jwt.unauthorized_loader
def missing_token_callback(error):
    """缺少Token回调"""
    return {
        'code': 401,
        'message': '缺少认证Token'
    }, 401


@jwt.revoked_token_loader
def revoked_token_callback(jwt_header, jwt_payload):
    """已撤销Token回调"""
    return {
        'code': 401,
        'message': 'Token已被撤销'
    }, 401


def init_jwt_callbacks(app):
    """初始化JWT回调"""
    # 回调已在装饰器中定义，这里仅作入口
    pass