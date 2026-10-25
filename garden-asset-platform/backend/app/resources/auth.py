"""
认证相关API资源
"""
import hashlib
import logging
from datetime import datetime
from urllib.parse import quote
from flask import current_app, request
from flask_restful import Resource
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    decode_token,
    jwt_required,
    get_jwt_identity,
    get_jwt
)
from itsdangerous import URLSafeTimedSerializer
from sqlalchemy import func
from app.extensions import db
from app.models.user import User, UserToken
from app.models.log import OperationLog
from app.services.email_service import mail_configured, send_email
from app.utils.middleware import rate_limit
from app.utils.tokens import invalidate_user_tokens
from app.utils.validators import has_html_tags


logger = logging.getLogger(__name__)


def _link_serializer(salt):
    return URLSafeTimedSerializer(
        current_app.config['SECRET_KEY'], salt=salt
    )


def _fingerprint(value):
    return hashlib.sha256((value or '').encode('utf-8')).hexdigest()[:16]


def _password_fingerprint(user):
    return _fingerprint(user.password_hash)


def _email_fingerprint(user):
    return _fingerprint((user.email or '').lower())


def _public_link(path, token):
    base = (current_app.config.get('PUBLIC_BASE_URL')
            or 'http://localhost:5173').rstrip('/')
    return f'{base}{path}?token={quote(token)}'


def _send_or_reveal(user, subject, body, link, link_key):
    """发送邮件；开发/测试环境在未发送时返回可点击链接。"""
    sent = False
    if mail_configured():
        try:
            send_email(user.email, subject, body)
            sent = True
        except Exception:
            logger.warning('认证邮件发送失败: %s', user.id, exc_info=True)
    data = {'sent': sent}
    if not sent and current_app.config.get('AUTH_LINK_RETURN_TOKEN'):
        data[link_key] = link
    return data



class RegisterResource(Resource):
    """用户注册"""

    @rate_limit(limit=3, window=3600)
    def post(self):
        data = request.get_json()

        # 参数校验
        username = data.get('username')
        password = data.get('password')
        email = (data.get('email') or '').strip() or None
        phone = (data.get('phone') or '').strip() or None

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
        except Exception as e:
            db.session.rollback()
            logger.error(f'注册失败: {e}', exc_info=True)
            return {'code': 500, 'message': '注册失败，请稍后重试'}, 500

        # 日志写入失败不应把已创建成功的用户判为注册失败
        try:
            OperationLog.log(
                user=user,
                action='register',
                module='auth',
                description=f'用户注册: {username}',
                request=request
            )
        except Exception:
            logger.warning('注册日志写入失败', exc_info=True)

        return {
            'code': 200,
            'message': '注册成功',
            'data': {'user_id': user.id, 'username': user.username}
        }, 200


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

        # 将当前 access token 的 jti 写入撤销表，登出后立即失效
        jwt_data = get_jwt()
        jti = jwt_data.get('jti')
        if jti:
            db.session.add(UserToken(
                user_id=user_id,
                token=jti,
                token_type='access',
                is_revoked=True,
                expires_at=datetime.utcfromtimestamp(jwt_data['exp'])
            ))

        # 前端会把 refresh token 一并提交；撤销后无法再换取新的 access token
        data = request.get_json(silent=True) or {}
        refresh_token = data.get('refresh_token')
        if refresh_token:
            try:
                refresh_payload = decode_token(refresh_token)
                if (
                    refresh_payload.get('type') == 'refresh'
                    and str(refresh_payload.get('sub')) == str(user_id)
                    and refresh_payload.get('jti')
                ):
                    db.session.add(UserToken(
                        user_id=user_id,
                        token=refresh_payload['jti'],
                        token_type='refresh',
                        is_revoked=True,
                        expires_at=datetime.utcfromtimestamp(refresh_payload['exp'])
                    ))
            except Exception:
                # refresh token 无效不影响登出本地会话
                logger.debug('登出时 refresh token 无效', exc_info=True)

        db.session.commit()

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
            user.nickname = (data.get('nickname') or '').strip()[:50] or None
        if 'email' in data:
            email = (data.get('email') or '').strip() or None
            # 检查邮箱是否已被其他用户使用
            existing = User.query.filter(User.email == email, User.id != user_id).first() if email else None
            if existing:
                return {'code': 400, 'message': '邮箱已被使用'}, 400
            if email != user.email:
                user.email_verified_at = None
            user.email = email
        if 'phone' in data:
            phone = (data.get('phone') or '').strip() or None
            existing = User.query.filter(User.phone == phone, User.id != user_id).first() if phone else None
            if existing:
                return {'code': 400, 'message': '手机号已被使用'}, 400
            user.phone = phone

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
        invalidate_user_tokens(user_id)
        db.session.commit()

        return {'code': 200, 'message': '密码修改成功，请重新登录'}


class ForgotPasswordResource(Resource):
    """请求密码重置邮件（不泄露邮箱是否注册）"""

    @rate_limit(limit=5, window=3600)
    def post(self):
        data = request.get_json(silent=True) or {}
        email = (data.get('email') or '').strip()
        if not email:
            return {'code': 400, 'message': '请输入邮箱'}, 400

        user = User.query.filter(
            func.lower(User.email) == email.lower(),
            User.status == 'active',
        ).first()
        generic = {
            'code': 200,
            'message': '如果该邮箱已注册，重置链接已发送',
            'data': {'sent': False},
        }
        if not user:
            return generic

        token = _link_serializer('password-reset').dumps({
            'uid': user.id,
            'pwd': _password_fingerprint(user),
        })
        link = _public_link('/reset-password', token)
        body = (
            f'{user.nickname or user.username}，你好：\n\n'
            '请打开以下链接重置密码（30 分钟内有效）：\n'
            f'{link}\n\n'
            '如果不是你本人操作，请忽略这封邮件。\n\n'
            '—— 苏州园林数字资产平台'
        )
        result = _send_or_reveal(
            user,
            '[苏州园林数字资产平台] 重置密码',
            body,
            link,
            'dev_reset_url',
        )
        result['expires_in'] = current_app.config.get(
            'PASSWORD_RESET_MAX_AGE', 1800
        )
        return {
            'code': 200,
            'message': '如果该邮箱已注册，重置链接已发送',
            'data': result,
        }, 200


class ResetPasswordResource(Resource):
    """使用一次性链接重置密码"""

    @rate_limit(limit=10, window=3600)
    def post(self):
        data = request.get_json(silent=True) or {}
        token = (data.get('token') or '').strip()
        new_password = data.get('new_password') or ''
        if not token or not new_password:
            return {'code': 400, 'message': '请填写完整'}, 400
        if len(new_password) < 6:
            return {'code': 400, 'message': '新密码长度不能少于6位'}, 400

        try:
            payload = _link_serializer('password-reset').loads(
                token,
                max_age=current_app.config.get('PASSWORD_RESET_MAX_AGE', 1800),
            )
        except Exception:
            return {'code': 400, 'message': '重置链接已过期或无效'}, 400

        user = User.query.get(payload.get('uid')) if isinstance(payload, dict) else None
        if not user or user.status != 'active':
            return {'code': 400, 'message': '重置链接已过期或无效'}, 400
        if payload.get('pwd') != _password_fingerprint(user):
            return {'code': 400, 'message': '重置链接已过期或无效'}, 400

        user.set_password(new_password)
        invalidate_user_tokens(user.id)
        db.session.commit()
        OperationLog.log(
            user=user,
            action='password_reset',
            module='auth',
            description=f'通过邮件链接重置密码: {user.username}',
            request=request,
        )
        return {
            'code': 200,
            'message': '密码已重置，请使用新密码登录',
        }, 200


class SendEmailVerificationResource(Resource):
    """发送邮箱验证链接"""

    @rate_limit(limit=5, window=3600)
    @jwt_required()
    def post(self):
        user = User.query.get(get_jwt_identity())
        if not user:
            return {'code': 404, 'message': '用户不存在'}, 404
        if not user.email:
            return {'code': 400, 'message': '请先设置邮箱'}, 400
        if user.email_verified_at:
            return {'code': 200, 'message': '邮箱已验证'}, 200

        token = _link_serializer('email-verify').dumps({
            'uid': user.id,
            'email': _email_fingerprint(user),
        })
        link = _public_link('/verify-email', token)
        body = (
            f'{user.nickname or user.username}，你好：\n\n'
            '请打开以下链接验证邮箱：\n'
            f'{link}\n\n'
            '链接 24 小时内有效。\n\n'
            '—— 苏州园林数字资产平台'
        )
        result = _send_or_reveal(
            user,
            '[苏州园林数字资产平台] 验证邮箱',
            body,
            link,
            'dev_verify_url',
        )
        result['expires_in'] = current_app.config.get(
            'EMAIL_VERIFY_MAX_AGE', 86400
        )
        return {'code': 200, 'message': '验证邮件已处理', 'data': result}, 200


class VerifyEmailResource(Resource):
    """通过邮件链接验证邮箱"""

    @rate_limit(limit=20, window=3600)
    def post(self):
        data = request.get_json(silent=True) or {}
        token = (data.get('token') or '').strip()
        if not token:
            return {'code': 400, 'message': '缺少验证凭证'}, 400
        try:
            payload = _link_serializer('email-verify').loads(
                token,
                max_age=current_app.config.get('EMAIL_VERIFY_MAX_AGE', 86400),
            )
        except Exception:
            return {'code': 400, 'message': '验证链接已过期或无效'}, 400

        user = User.query.get(payload.get('uid')) if isinstance(payload, dict) else None
        if not user or user.status != 'active':
            return {'code': 400, 'message': '验证链接已过期或无效'}, 400
        if payload.get('email') != _email_fingerprint(user):
            return {'code': 400, 'message': '邮箱已变更，请重新发送验证邮件'}, 400
        if user.email_verified_at:
            return {'code': 200, 'message': '邮箱已验证'}, 200

        user.email_verified_at = datetime.utcnow()
        db.session.commit()
        OperationLog.log(
            user=user,
            action='email_verify',
            module='auth',
            description=f'验证邮箱: {user.email}',
            request=request,
        )
        return {'code': 200, 'message': '邮箱验证成功'}, 200


class UserListResource(Resource):
    """用户列表"""

    @jwt_required()
    def get(self):
        current_user_id = get_jwt_identity()
        current_user = User.query.get(current_user_id)

        if not current_user or current_user.role != 'admin':
            return {'code': 403, 'message': '无权限'}, 403

        users = User.query.order_by(User.created_at.desc()).all()
        result = [u.to_dict() for u in users]

        return {'code': 200, 'data': result}

    @jwt_required()
    def post(self):
        """管理员创建用户（可指定角色与状态）"""
        current_user_id = get_jwt_identity()
        current_user = User.query.get(current_user_id)

        if not current_user or current_user.role != 'admin':
            return {'code': 403, 'message': '无权限'}, 403

        data = request.get_json() or {}
        username = (data.get('username') or '').strip()
        password = data.get('password') or ''
        email = (data.get('email') or '').strip() or None
        role = data.get('role', 'user')
        status = data.get('status', 'active')

        if not username or not password:
            return {'code': 400, 'message': '用户名和密码不能为空'}, 400
        if len(password) < 6:
            return {'code': 400, 'message': '密码长度不能少于 6 位'}, 400
        if role not in ('user', 'asset_admin', 'license_admin', 'adm1', 'adm2', 'admin'):
            return {'code': 400, 'message': '无效的角色'}, 400
        if status not in ('active', 'inactive', 'banned'):
            return {'code': 400, 'message': '无效的状态'}, 400
        if User.query.filter_by(username=username).first():
            return {'code': 400, 'message': '用户名已存在'}, 400

        user = User(username=username, email=email, role=role, status=status)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        return {'code': 200, 'message': '创建成功', 'data': user.to_dict()}


class UserResource(Resource):
    """用户管理"""

    @jwt_required()
    def put(self, user_id):
        """更新用户信息"""
        current_user_id = get_jwt_identity()
        current_user = User.query.get(current_user_id)

        if current_user.role != 'admin' and current_user_id != user_id:
            return {'code': 403, 'message': '无权限'}, 403

        user = User.query.get(user_id)
        if not user:
            return {'code': 404, 'message': '用户不存在'}, 404

        data = request.get_json()

        # 更新字段
        if 'email' in data:
            email = (data.get('email') or '').strip() or None
            if email and User.query.filter(User.email == email, User.id != user.id).first():
                return {'code': 400, 'message': '邮箱已被使用'}, 400
            user.email = email
        if 'phone' in data:
            phone = (data.get('phone') or '').strip() or None
            if phone and User.query.filter(User.phone == phone, User.id != user.id).first():
                return {'code': 400, 'message': '手机号已被使用'}, 400
            user.phone = phone
        if data.get('nickname') is not None:
            user.nickname = (data.get('nickname') or '').strip()[:50]

        if data.get('password'):
            if current_user.role != 'admin':
                return {'code': 403, 'message': '只有管理员可以重置密码'}, 403
            if len(str(data['password'])) < 6:
                return {'code': 400, 'message': '密码至少 6 位'}, 400
            user.set_password(str(data['password']))
            invalidate_user_tokens(user.id)

        if 'role' in data and current_user.role == 'admin':
            if data['role'] not in ('user', 'asset_admin', 'license_admin', 'adm1', 'adm2', 'admin'):
                return {'code': 400, 'message': '无效的角色'}, 400
            if user.id == current_user_id and data['role'] != 'admin':
                return {'code': 400, 'message': '不能降低自己的管理员角色'}, 400
            user.role = data['role']
        if 'status' in data and current_user.role == 'admin':
            if data['status'] not in ('active', 'inactive', 'banned'):
                return {'code': 400, 'message': '无效的状态'}, 400
            if user.id == current_user_id and data['status'] != 'active':
                return {'code': 400, 'message': '不能停用自己的账号'}, 400
            user.status = data['status']

        db.session.commit()

        return {'code': 200, 'message': '更新成功', 'data': user.to_dict()}