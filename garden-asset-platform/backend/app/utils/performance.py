"""
性能监控中间件
"""
import time
import logging
from flask import g, request, current_app
from functools import wraps

logger = logging.getLogger(__name__)


def performance_monitor(app):
    """性能监控中间件"""
    @app.before_request
    def before_request():
        g.start_time = time.time()
        g.request_id = request.headers.get('X-Request-ID', '')

    @app.after_request
    def after_request(response):
        if hasattr(g, 'start_time'):
            duration = time.time() - g.start_time

            # 慢请求告警 (>1秒)
            if duration > 1:
                logger.warning(
                    f"Slow request: {request.method} {request.path} "
                    f"took {duration:.3f}s"
                )

            # 添加响应时间头
            response.headers['X-Response-Time'] = f"{duration:.3f}s"
            response.headers['X-Request-ID'] = g.request_id

        return response


def measure_time(func):
    """测量函数执行时间装饰器"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        duration = time.time() - start
        logger.debug(f"{func.__name__} took {duration:.3f}s")
        return result
    return wrapper


class PerformanceMetrics:
    """性能指标收集"""

    def __init__(self):
        self.metrics = {}

    def record(self, name, value):
        """记录指标"""
        if name not in self.metrics:
            self.metrics[name] = []
        self.metrics[name].append(value)

    def get_stats(self, name):
        """获取统计信息"""
        values = self.metrics.get(name, [])
        if not values:
            return None

        return {
            'count': len(values),
            'avg': sum(values) / len(values),
            'min': min(values),
            'max': max(values)
        }

    def clear(self):
        """清除指标"""
        self.metrics.clear()


# 全局指标实例
metrics = PerformanceMetrics()