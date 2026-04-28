"""
错误处理
"""
from flask import jsonify
from werkzeug.exceptions import HTTPException


def register_error_handlers(app):
    """注册错误处理器"""

    @app.errorhandler(400)
    def bad_request(error):
        return jsonify({
            'code': 400,
            'message': '请求参数错误',
            'error': str(error)
        }), 400

    @app.errorhandler(401)
    def unauthorized(error):
        return jsonify({
            'code': 401,
            'message': '未授权访问'
        }), 401

    @app.errorhandler(403)
    def forbidden(error):
        return jsonify({
            'code': 403,
            'message': '禁止访问'
        }), 403

    @app.errorhandler(404)
    def not_found(error):
        return jsonify({
            'code': 404,
            'message': '资源不存在'
        }), 404

    @app.errorhandler(500)
    def internal_error(error):
        return jsonify({
            'code': 500,
            'message': '服务器内部错误'
        }), 500

    @app.errorhandler(Exception)
    def handle_exception(error):
        if isinstance(error, HTTPException):
            return jsonify({
                'code': error.code,
                'message': error.description
            }), error.code

        app.logger.error(f'Unhandled exception: {error}', exc_info=True)
        return jsonify({
            'code': 500,
            'message': '服务器内部错误'
        }), 500