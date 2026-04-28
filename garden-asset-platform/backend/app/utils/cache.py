"""
缓存工具
"""
from functools import wraps
from flask import current_app
import json
import hashlib


def cache_key(*args, **kwargs):
    """生成缓存键"""
    key_data = json.dumps({'args': args, 'kwargs': kwargs}, sort_keys=True)
    return hashlib.md5(key_data.encode()).hexdigest()


def redis_cache(timeout=300):
    """Redis缓存装饰器"""
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            redis_client = current_app.extensions.get('redis')
            if not redis_client:
                return fn(*args, **kwargs)

            key = f"cache:{fn.__name__}:{cache_key(*args, **kwargs)}"

            # 尝试获取缓存
            cached = redis_client.get(key)
            if cached:
                return json.loads(cached)

            # 执行函数
            result = fn(*args, **kwargs)

            # 存储缓存
            if result is not None:
                redis_client.setex(key, timeout, json.dumps(result))

            return result
        return wrapper
    return decorator


def clear_cache(pattern):
    """清除匹配的缓存"""
    redis_client = current_app.extensions.get('redis')
    if redis_client:
        keys = redis_client.keys(f"cache:{pattern}*")
        if keys:
            redis_client.delete(*keys)