"""
AI相关API资源
"""
from flask import request
from flask_restful import Resource
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models.user import User
from app.models.asset import Asset
from app.services.ai_service import ai_service
from app.utils.middleware import rate_limit


def ai_unavailable():
    """AI 未配置时统一返回 503，避免把能力缺失误报成服务器错误"""
    if not getattr(ai_service, 'enabled', False):
        return {'code': 503, 'message': 'AI 服务未启用，请配置模型与 API Key'}, 503
    return None


class AIAnalyzeResource(Resource):
    """AI分析"""

    @rate_limit(limit=20, window=60)
    @jwt_required()
    def post(self):
        """分析资产"""
        unavailable = ai_unavailable()
        if unavailable:
            return unavailable

        user_id = get_jwt_identity()
        data = request.get_json()
        asset_id = data.get('asset_id')

        if not asset_id:
            return {'code': 400, 'message': '缺少资产ID'}, 400

        asset = Asset.query.get(asset_id)
        if not asset:
            return {'code': 404, 'message': '资产不存在'}, 404

        user = User.query.get(user_id)
        is_owner = user_id in (asset.creator_id, asset.owner_id, asset.uploader_id)
        is_admin = bool(user) and user.role in ('admin', 'asset_admin')
        if asset.status != 'published' and not (is_owner or is_admin):
            return {'code': 404, 'message': '资产不存在'}, 404

        result = ai_service.process_asset(asset)

        if result['success']:
            return {
                'code': 200,
                'message': '分析完成',
                'data': result['results']
            }, 200
        else:
            return {'code': 500, 'message': result['message']}, 500


class AISearchResource(Resource):
    """AI相似搜索"""

    @rate_limit(limit=10, window=60)
    @jwt_required()
    def post(self):
        """搜索相似图像"""
        unavailable = ai_unavailable()
        if unavailable:
            return unavailable

        if 'file' not in request.files:
            return {'code': 400, 'message': '未上传文件'}, 400

        file = request.files['file']
        if file.filename == '':
            return {'code': 400, 'message': '未选择文件'}, 400

        # 保存临时文件（先关闭句柄再处理，Windows 上才能删除）
        import os
        import tempfile
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg')
        tmp_path = tmp.name
        tmp.close()
        try:
            file.save(tmp_path)
            results = ai_service.search_similar(tmp_path, top_k=10)
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                # 临时文件可能已被系统清理，忽略即可
                pass

        return {
            'code': 200,
            'data': {
                'total': len(results),
                'results': results
            }
        }, 200


class AIInfringementResource(Resource):
    """AI侵权检测"""

    @rate_limit(limit=10, window=60)
    @jwt_required()
    def post(self):
        """检测侵权"""
        unavailable = ai_unavailable()
        if unavailable:
            return unavailable

        if 'file' not in request.files:
            return {'code': 400, 'message': '未上传文件'}, 400

        file = request.files['file']
        if file.filename == '':
            return {'code': 400, 'message': '未选择文件'}, 400

        # 保存临时文件（先关闭句柄再处理，Windows 上才能删除）
        import os
        import tempfile
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg')
        tmp_path = tmp.name
        tmp.close()
        try:
            file.save(tmp_path)
            result = ai_service.check_infringement(tmp_path)
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                # 临时文件可能已被系统清理，忽略即可
                pass

        return {
            'code': 200,
            'data': result
        }, 200


class AIChatResource(Resource):
    """AI智能对话"""

    @rate_limit(limit=20, window=60)
    @jwt_required()
    def post(self):
        """智能问答"""
        unavailable = ai_unavailable()
        if unavailable:
            return unavailable

        data = request.get_json()
        question = data.get('question')
        context = data.get('context', {})

        if not question:
            return {'code': 400, 'message': '缺少问题'}, 400

        # 构建系统提示
        system_prompt = """
        你是苏州园林数字资产保护平台智能助手，负责解答用户关于：
        - 平台使用方法
        - 版权保护知识
        - 授权流程说明
        - 溯源查询帮助
        等问题。请用专业、友好的语气回答。
        """

        full_prompt = f"{system_prompt}\n\n用户问题：{question}"

        answer = ai_service.analyze_with_glm(full_prompt, context)

        return {
            'code': 200,
            'data': {
                'question': question,
                'answer': answer
            }
        }, 200