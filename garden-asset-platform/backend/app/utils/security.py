"""
安全工具
"""
import secrets
import hashlib
import base64
import hmac
from datetime import datetime, timedelta
from functools import wraps

from flask import request, jsonify, current_app


def generate_random_string(length=32):
    """生成随机字符串"""
    return secrets.token_hex(length)


def generate_api_key():
    """生成API密钥"""
    return secrets.token_urlsafe(32)


def hash_password(password, salt=None):
    """哈希密码"""
    if salt is None:
        salt = secrets.token_hex(16)

    key = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt.encode('utf-8'),
        100000
    )
    return f'{salt}:{base64.b64encode(key).decode()}'


def verify_password(password, hashed):
    """验证密码"""
    try:
        salt, key = hashed.split(':')
        new_key = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt.encode('utf-8'),
            100000
        )
        return hmac.compare_digest(key, base64.b64encode(new_key).decode())
    except:
        return False


def sanitize_input(text):
    """清理输入"""
    if not text:
        return ''
    # 移除危险字符
    dangerous = ['<', '>', '"', "'", '&', '\x00']
    for char in dangerous:
        text = text.replace(char, '')
    return text.strip()


def generate_csrf_token():
    """生成CSRF Token"""
    return secrets.token_urlsafe(32)


def verify_csrf_token(token, stored_token):
    """验证CSRF Token"""
    if not token or not stored_token:
        return False
    return hmac.compare_digest(token, stored_token)


def rate_limit_by_ip(limit=100, window=3600):
    """IP限流装饰器（需配置Redis）"""
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            try:
                redis_client = current_app.extensions.get('redis')
                if redis_client:
                    key = f'rate_limit_ip:{request.remote_addr}'
                    count = redis_client.incr(key)
                    if count == 1:
                        redis_client.expire(key, window)
                    if count > limit:
                        return jsonify({'code': 429, 'message': '请求过于频繁'}), 429
            except Exception:
                pass
            return f(*args, **kwargs)
        return wrapped
    return decorator


def check_content_type(allowed_types):
    """检查Content-Type"""
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            content_type = request.content_type
            if content_type and not any(t in content_type for t in allowed_types):
                return jsonify({
                    'code': 415,
                    'message': '不支持的Content-Type'
                }), 415
            return f(*args, **kwargs)
        return wrapped
    return decorator


# SQL注入检测
SQL_INJECTION_PATTERNS = [
    "union select", "or 1=1", "and 1=1", "drop table",
    "insert into", "delete from", "--", "/*", "*/"
]


def detect_sql_injection(text):
    """检测SQL注入"""
    if not text:
        return False
    text_lower = text.lower()
    return any(pattern in text_lower for pattern in SQL_INJECTION_PATTERNS)


# XSS检测
XSS_PATTERNS = [
    "<script", "javascript:", "onerror=", "onload=",
    "eval(", "document.cookie", "alert("
]


def detect_xss(text):
    """检测XSS"""
    if not text:
        return False
    text_lower = text.lower()
    return any(pattern in text_lower for pattern in XSS_PATTERNS)