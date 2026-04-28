"""
响应工具函数
统一API响应格式
"""
from flask import jsonify


def success_response(data=None, message='操作成功', code=200):
    """成功响应"""
    response = {
        'code': code,
        'message': message,
        'data': data
    }
    return jsonify(response), code


def error_response(message='操作失败', code=400, data=None):
    """错误响应"""
    response = {
        'code': code,
        'message': message,
        'data': data
    }
    return jsonify(response), code


def paginated_response(items, total, page=1, per_page=20, message='获取成功'):
    """分页响应"""
    return jsonify({
        'code': 200,
        'message': message,
        'data': {
            'items': items,
            'total': total,
            'page': page,
            'per_page': per_page,
            'pages': (total + per_page - 1) // per_page if per_page > 0 else 0
        }
    }), 200
