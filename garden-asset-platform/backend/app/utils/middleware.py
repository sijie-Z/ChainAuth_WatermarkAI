"""
中间件模块
"""
import time
import logging
from flask import request, g, current_app, jsonify
from functools import wraps

logger = logging.getLogger(__name__)


def request_logger(app):
    """请求日志中间件"""
    @app.before_request
    def before_request():
        g.start_time = time.time()
        g.request_id = request.headers.get('X-Request-ID', '')

        logger.info(
            f"Request: {request.method} {request.path} "
            f"IP: {request.remote_addr} "
            f"User-Agent: {request.user_agent}"
        )

    @app.after_request
    def after_request(response):
        if hasattr(g, 'start_time'):
            duration = time.time() - g.start_time
            response.headers['X-Response-Time'] = f"{duration:.3f}s"

            logger.info(
                f"Response: {response.status_code} "
                f"Duration: {duration:.3f}s"
            )

        return response


def rate_limit(limit=100, window=60):
    """请求频率限制装饰器（需配置Redis）"""
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            try:
                redis_client = current_app.extensions.get('redis')
                if redis_client:
                    key = f'rate_limit:{request.remote_addr}:{request.path}'
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


def cors_headers(app):
    """CORS头中间件"""
    @app.after_request
    def after_request(response):
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
        return response


def security_headers(app):
    """安全头中间件"""
    @app.after_request
    def after_request(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        return response