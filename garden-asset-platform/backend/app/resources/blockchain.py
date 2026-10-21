"""
区块链相关API资源
"""
from flask import request
from flask_restful import Resource
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.extensions import db
from app.models.user import User
from app.models.asset import Asset
from app.models.blockchain import Certificate, BlockchainTransaction
from app.services.blockchain_service import blockchain_service


class BlockchainRegisterResource(Resource):
    """资产上链存证"""

    @jwt_required()
    def post(self):
        """提交资产存证"""
        user_id = get_jwt_identity()
        user = User.query.get(user_id)

        data = request.get_json()
        asset_id = data.get('asset_id')

        if not asset_id:
            return {'code': 400, 'message': '缺少资产ID'}, 400

        asset = Asset.query.get(asset_id)
        if not asset:
            return {'code': 404, 'message': '资产不存在'}, 404

        # 权限检查：仅资产所有者或资产管理员可上链
        is_owner = user_id in (asset.creator_id, asset.owner_id, asset.uploader_id)
        if not is_owner and user.role not in ('admin', 'asset_admin'):
            return {'code': 403, 'message': '无权限操作'}, 403

        # 调用服务存证
        result = blockchain_service.register_asset(asset, user)

        if result['success']:
            return {
                'code': 200,
                'message': '存证成功',
                'data': {
                    'tx_hash': result['tx_hash'],
                    'certificate_id': result['certificate_id'],
                    'block_number': result['block_number'],
                    'simulated': result['simulated']
                }
            }, 200
        else:
            return {'code': 500, 'message': result['message']}, 500


class BlockchainVerifyResource(Resource):
    """存证验证"""

    def get(self, asset_id):
        """验证资产存证"""
        asset = Asset.query.get(asset_id)

        if not asset:
            return {'code': 404, 'message': '资产不存在'}, 404

        result = blockchain_service.verify_asset(asset)

        return {
            'code': 200,
            'verified': result['verified'],
            'message': result['message'],
            'data': result
        }, 200

    def post(self):
        """通过水印ID验证"""
        data = request.get_json()
        watermark_id = data.get('watermark_id')

        if not watermark_id:
            return {'code': 400, 'message': '缺少水印ID'}, 400

        asset = Asset.query.filter_by(watermark_id=watermark_id).first()

        if not asset:
            return {
                'code': 404,
                'verified': False,
                'message': '未找到对应资产'
            }, 404

        result = blockchain_service.verify_asset(asset)

        return {
            'code': 200,
            'verified': result['verified'],
            'message': result['message'],
            'data': {
                'asset_id': asset.id,
                'asset_code': asset.asset_code,
                'title': asset.title,
                **result
            }
        }, 200


class BlockchainCertificateResource(Resource):
    """存证证书"""

    def get(self, certificate_id):
        """获取证书详情"""
        certificate = Certificate.query.filter_by(certificate_id=certificate_id).first()

        if not certificate:
            return {'code': 404, 'message': '证书不存在'}, 404

        asset = Asset.query.get(certificate.asset_id)

        return {
            'code': 200,
            'data': {
                'certificate': certificate.to_dict(),
                'asset': {
                    'asset_code': asset.asset_code if asset else None,
                    'title': asset.title if asset else None,
                    'asset_type': asset.asset_type if asset else None,
                    'file_format': asset.file_format if asset else None,
                    'owner_name': (
                        (asset.owner.nickname or asset.owner.username)
                        if asset and asset.owner else None
                    ),
                    'watermark_id': asset.watermark_id if asset else None
                }
            }
        }, 200


class BlockchainHistoryResource(Resource):
    """存证历史"""

    @jwt_required()
    def get(self, asset_id=None):
        """获取存证历史"""
        if asset_id:
            asset = Asset.query.get(asset_id)
            if not asset:
                return {'code': 404, 'message': '资产不存在'}, 404

            history = blockchain_service.get_asset_history(asset)

            return {
                'code': 200,
                'data': {
                    'asset_id': asset_id,
                    'asset_code': asset.asset_code,
                    'history': history
                }
            }, 200
        else:
            # 获取所有存证记录
            from app.models.blockchain import Certificate
            certificates = Certificate.query.order_by(Certificate.created_at.desc()).limit(50).all()

            result = []
            for cert in certificates:
                asset = Asset.query.get(cert.asset_id)
                result.append({
                    'certificate_id': cert.certificate_id,
                    'asset_id': cert.asset_id,
                    'asset_code': asset.asset_code if asset else None,
                    'asset_title': asset.title if asset else None,
                    'tx_hash': cert.tx_hash,
                    'block_number': cert.block_number,
                    # 兼容旧字段名：证书创建即确认时间
                    'confirmed_at': cert.created_at.isoformat() if cert.created_at else None
                })

            return {'code': 200, 'data': result}, 200


class BlockchainStatusResource(Resource):
    """区块链状态"""

    def get(self):
        """获取区块链连接状态"""
        connected = blockchain_service.is_connected()

        from app.models.blockchain import Certificate
        total_certificates = Certificate.query.count()
        pending_assets = Asset.query.filter(
            Asset.status == 'published', Asset.chain_status == 'none'
        ).count()

        if connected:
            node_status = 'connected'
        elif blockchain_service.enabled:
            node_status = 'disconnected'
        else:
            node_status = 'simulated'

        return {
            'code': 200,
            'data': {
                'connected': connected,
                'rpc_url': blockchain_service.rpc_url,
                'simulated': not blockchain_service.enabled,
                'total_certificates': total_certificates,
                'pending_assets': pending_assets,
                'node_status': node_status
            }
        }, 200