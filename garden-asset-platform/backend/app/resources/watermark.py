"""
水印相关API资源
"""
from flask import request, current_app
from flask_restful import Resource
from flask_jwt_extended import jwt_required, get_jwt_identity
from werkzeug.utils import secure_filename
from app.extensions import db
from app.models.user import User
from app.models.asset import Asset
from app.models.log import OperationLog
from app.services.watermark_service import WatermarkService


class WatermarkEmbedResource(Resource):
    """水印嵌入"""

    @jwt_required()
    def post(self):
        """嵌入水印"""
        user_id = get_jwt_identity()
        user = User.query.get(user_id)

        data = request.get_json()
        asset_id = data.get('asset_id')

        if not asset_id:
            return {'code': 400, 'message': '缺少资产ID'}, 400

        asset = Asset.query.get(asset_id)
        if not asset:
            return {'code': 404, 'message': '资产不存在'}, 404

        # 权限检查
        if asset.creator_id != user_id and user.role not in ['admin', 'adm1', 'adm2', 'adm3']:
            return {'code': 403, 'message': '无权限操作'}, 403

        # 调用服务嵌入水印
        result = WatermarkService.embed_watermark(asset, user)

        if result['success']:
            return {
                'code': 200,
                'message': result['message'],
                'data': {
                    'watermark_id': result.get('watermark_id'),
                    'watermarked_path': result.get('watermarked_path'),
                    'psnr': result.get('psnr')
                }
            }, 200
        else:
            status = 400 if '不支持' in result['message'] else 500
            return {'code': status, 'message': result['message']}, status


class WatermarkExtractResource(Resource):
    """水印提取"""

    @jwt_required()
    def post(self):
        """提取水印"""
        user_id = get_jwt_identity()
        user = User.query.get(user_id)

        data = request.get_json()
        asset_id = data.get('asset_id')

        if not asset_id:
            return {'code': 400, 'message': '缺少资产ID'}, 400

        asset = Asset.query.get(asset_id)
        if not asset:
            return {'code': 404, 'message': '资产不存在'}, 404

        # 调用服务提取水印
        result = WatermarkService.extract_watermark(asset, user)

        if result['success']:
            return {
                'code': 200,
                'message': result['message'],
                'data': {
                    'watermark_path': result.get('watermark_path'),
                    'nc_value': result.get('nc_value')
                }
            }, 200
        else:
            status = 400 if '不支持' in result['message'] else 500
            return {'code': status, 'message': result['message']}, status


class WatermarkVerifyResource(Resource):
    """水印验证"""

    def post(self):
        """验证水印ID"""
        data = request.get_json()
        watermark_id = data.get('watermark_id')

        if not watermark_id:
            return {'code': 400, 'message': '缺少水印ID'}, 400

        # 查找资产
        asset = Asset.query.filter_by(watermark_id=watermark_id).first()

        if not asset:
            return {
                'code': 404,
                'message': '未找到对应资产',
                'verified': False
            }, 404

        # 验证水印
        result = WatermarkService.verify_watermark(asset, watermark_id)

        return {
            'code': 200,
            'verified': result['verified'],
            'message': result['message'],
            'data': {
                'asset_id': asset.id,
                'asset_code': asset.asset_code,
                'title': asset.title,
                'watermark_id': asset.watermark_id,
                'chain_status': asset.chain_status
            }
        }, 200


class WatermarkTraceResource(Resource):
    """水印溯源"""

    def post(self):
        """通过上传文件溯源"""
        if 'file' not in request.files:
            return {'code': 400, 'message': '未上传文件'}, 400

        file = request.files['file']
        if file.filename == '':
            return {'code': 400, 'message': '未选择文件'}, 400

        import os
        import uuid
        from datetime import datetime

        # 保存临时文件
        filename = secure_filename(file.filename)
        temp_dir = current_app.config.get('UPLOAD_FOLDER', './uploads')
        temp_path = os.path.join(temp_dir, f"trace_{uuid.uuid4().hex[:8]}_{filename}")
        file.save(temp_path)

        try:
            # 调用服务提取水印
            result = WatermarkService.trace_from_file(temp_path)

            if result['success'] and result.get('watermark_id'):
                # 查找对应资产
                asset = Asset.query.filter_by(watermark_id=result['watermark_id']).first()

                if asset:
                    # 查找区块链存证记录
                    from app.models.blockchain import Certificate
                    certificate = Certificate.query.filter_by(asset_id=asset.id).first()

                    return {
                        'code': 200,
                        'verified': True,
                        'message': '溯源成功',
                        'data': {
                            'asset_id': asset.id,
                            'asset_code': asset.asset_code,
                            'title': asset.title,
                            'watermark_id': asset.watermark_id,
                            'created_at': asset.created_at.isoformat() if asset.created_at else None,
                            'nc_value': result.get('nc_value', 0),
                            'certificate_id': certificate.certificate_id if certificate else None,
                            'tx_hash': certificate.tx_hash if certificate else None,
                            'confirmed_at': certificate.created_at.isoformat() if certificate and certificate.created_at else None
                        }
                    }, 200
                else:
                    return {
                        'code': 200,
                        'verified': False,
                        'message': '未找到匹配的资产记录',
                        'data': {
                            'watermark_id': result.get('watermark_id'),
                            'nc_value': result.get('nc_value', 0)
                        }
                    }, 200
            else:
                return {
                    'code': 200,
                    'verified': False,
                    'message': result.get('message', '未能提取有效水印'),
                    'data': None
                }, 200
        finally:
            # 清理临时文件
            if os.path.exists(temp_path):
                os.remove(temp_path)


class WatermarkLogsResource(Resource):
    """水印操作记录"""

    @jwt_required()
    def get(self):
        """获取水印操作日志"""
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)

        if user.role not in ['admin', 'asset_admin', 'adm1', 'adm2']:
            return {'code': 403, 'message': '无权限'}, 403

        logs = OperationLog.query.filter_by(module='watermark').order_by(
            OperationLog.created_at.desc()
        ).limit(100).all()

        result = []
        for log in logs:
            asset = Asset.query.get(log.target_id) if log.target_id else None
            result.append({
                'id': log.id,
                'asset_code': asset.asset_code if asset else None,
                'asset_title': asset.title if asset else None,
                'operation': log.action.split('_')[1] if '_' in log.action else log.action,
                'watermark_id': asset.watermark_id if asset else None,
                'nc_value': None,  # 可以从日志详情中解析
                'operator': log.user.username if log.user else None,
                'created_at': log.created_at.isoformat() if log.created_at else None
            })

        return {'code': 200, 'data': result}, 200