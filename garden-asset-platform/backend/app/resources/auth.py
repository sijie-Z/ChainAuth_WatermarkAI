"""
认证相关API资源
"""
from datetime import datetime
from flask import request
from flask_restful import Resource
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    jwt_required,
    get_jwt_identity,
    get_jwt
)
from app.extensions import db
from app.models.user import User, UserToken
from app.models.log import OperationLog
from app.utils.middleware import rate_limit
from app.utils.validators import has_html_tags


class RegisterResource(Resource):
    """用户注册"""

    @rate_limit(limit=3, window=3600)
    def post(self):
        data = request.get_json()

        # 参数校验
        username = data.get('username')
        password = data.get('password')
        email = data.get('email')
        phone = data.get('phone')

        if not username or not password:
            return {'code': 400, 'message': '用户名和密码不能为空'}, 400

        # 防止XSS注入
        if has_html_tags(username) or has_html_tags(email) or has_html_tags(phone):
            return {'code': 400, 'message': '输入包含非法字符'}, 400

        # 检查用户是否已存在
        if User.query.filter_by(username=username).first():
            return {'code': 400, 'message': '用户名已存在'}, 400

        if email and User.query.filter_by(email=email).first():
            return {'code': 400, 'message': '邮箱已被注册'}, 400

        if phone and User.query.filter_by(phone=phone).first():
            return {'code': 400, 'message': '手机号已被注册'}, 400

        # 密码强度校验
        if len(password) < 6:
            return {'code': 400, 'message': '密码长度不能少于6位'}, 400

        # 创建用户（角色强制为 user，防止提权攻击）
        user = User(
            username=username,
            email=email,
            phone=phone,
            role='user'
        )
        user.set_password(password)

        try:
            db.session.add(user)
            db.session.commit()

            # 记录日志
            OperationLog.log(
                user=user,
                action='register',
                module='auth',
                description=f'用户注册: {username}',
                request=request
            )

            return {
                'code': 200,
                'message': '注册成功',
                'data': {'user_id': user.id, 'username': user.username}
            }, 200

        except Exception as e:
            db.session.rollback()
            import logging
            logging.getLogger(__name__).error(f'注册失败: {e}', exc_info=True)
            return {'code': 500, 'message': '注册失败，请稍后重试'}, 500


class LoginResource(Resource):
    """用户登录"""

    @rate_limit(limit=5, window=60)
    def post(self):
        data = request.get_json()

        username = data.get('username')
        password = data.get('password')

        if not username or not password:
            return {'code': 400, 'message': '用户名和密码不能为空'}, 400

        # 查找用户
        user = User.query.filter_by(username=username).first()

        if not user or not user.check_password(password):
            return {'code': 401, 'message': '用户名或密码错误'}, 401

        if user.status != 'active':
            return {'code': 403, 'message': '账户已被禁用'}, 403

        # 创建Token
        access_token = create_access_token(identity=user.id)
        refresh_token = create_refresh_token(identity=user.id)

        # 更新登录时间
        user.last_login_at = datetime.utcnow()
        db.session.commit()

        # 记录日志
        OperationLog.log(
            user=user,
            action='login',
            module='auth',
            description=f'用户登录: {username}',
            request=request
        )

        return {
            'code': 200,
            'message': '登录成功',
            'data': {
                'access_token': access_token,
                'refresh_token': refresh_token,
                'user': user.to_dict()
            }
        }, 200


class LogoutResource(Resource):
    """用户登出"""

    @jwt_required()
    def post(self):
        user_id = get_jwt_identity()

        # 记录日志
        user = User.query.get(user_id)
        OperationLog.log(
            user=user,
            action='logout',
            module='auth',
            request=request
        )

        return {'code': 200, 'message': '登出成功'}, 200


class RefreshTokenResource(Resource):
    """刷新Token"""

    @jwt_required(refresh=True)
    def post(self):
        user_id = get_jwt_identity()
        user = User.query.get(user_id)

        if not user or user.status != 'active':
            return {'code': 401, 'message': '用户不存在或已被禁用'}, 401

        access_token = create_access_token(identity=user_id)

        return {
            'code': 200,
            'message': '刷新成功',
            'data': {'access_token': access_token}
        }, 200


class CurrentUserResource(Resource):
    """获取当前用户信息"""

    @jwt_required()
    def get(self):
        user_id = get_jwt_identity()
        user = User.query.get(user_id)

        if not user:
            return {'code': 404, 'message': '用户不存在'}, 404

        return {
            'code': 200,
            'data': user.to_dict()
        }, 200

    @jwt_required()
    def put(self):
        """更新当前用户信息"""
        user_id = get_jwt_identity()
        user = User.query.get(user_id)

        if not user:
            return {'code': 404, 'message': '用户不存在'}, 404

        data = request.get_json()

        if 'nickname' in data:
            user.nickname = data['nickname']
        if 'email' in data:
            # 检查邮箱是否已被其他用户使用
            existing = User.query.filter(User.email == data['email'], User.id != user_id).first()
            if existing:
                return {'code': 400, 'message': '邮箱已被使用'}, 400
            user.email = data['email']
        if 'phone' in data:
            existing = User.query.filter(User.phone == data['phone'], User.id != user_id).first()
            if existing:
                return {'code': 400, 'message': '手机号已被使用'}, 400
            user.phone = data['phone']

        try:
            db.session.commit()
            return {'code': 200, 'message': '更新成功', 'data': user.to_dict()}
        except Exception as e:
            db.session.rollback()
            return {'code': 500, 'message': '更新失败'}, 500


class ChangePasswordResource(Resource):
    """修改密码"""

    @jwt_required()
    def post(self):
        user_id = get_jwt_identity()
        user = User.query.get(user_id)

        if not user:
            return {'code': 404, 'message': '用户不存在'}, 404

        data = request.get_json()
        old_password = data.get('old_password')
        new_password = data.get('new_password')

        if not old_password or not new_password:
            return {'code': 400, 'message': '请填写完整'}, 400

        if not user.check_password(old_password):
            return {'code': 400, 'message': '原密码错误'}, 400

        if len(new_password) < 6:
            return {'code': 400, 'message': '新密码长度不能少于6位'}, 400

        user.set_password(new_password)
        db.session.commit()

        return {'code': 200, 'message': '密码修改成功'}


class UserListResource(Resource):
    """用户列表"""

    @jwt_required()
    def get(self):
        current_user_id = get_jwt_identity()
        current_user = User.query.get(current_user_id)

        if current_user.role not in ['admin', 'super_admin']:
            return {'code': 403, 'message': '无权限'}, 403

        users = User.query.order_by(User.created_at.desc()).all()
        result = [u.to_dict() for u in users]

        return {'code': 200, 'data': result}


class UserResource(Resource):
    """用户管理"""

    @jwt_required()
    def put(self, user_id):
        """更新用户信息"""
        current_user_id = get_jwt_identity()
        current_user = User.query.get(current_user_id)

        if current_user.role not in ['admin', 'super_admin'] and current_user_id != user_id:
            return {'code': 403, 'message': '无权限'}, 403

        user = User.query.get(user_id)
        if not user:
            return {'code': 404, 'message': '用户不存在'}, 404

        data = request.get_json()

        # 更新字段
        if 'email' in data:
            user.email = data['email']
        if 'phone' in data:
            user.phone = data['phone']
        if 'role' in data and current_user.role in ['admin', 'super_admin']:
            user.role = data['role']
        if 'status' in data and current_user.role in ['admin', 'super_admin']:
            user.status = data['status']

        db.session.commit()

        return {'code': 200, 'message': '更新成功', 'data': user.to_dict()}