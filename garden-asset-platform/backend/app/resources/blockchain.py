"""
区块链相关API资源
"""
from flask import current_app, request
from flask_restful import Resource
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models.user import User
from app.models.asset import Asset, AssetVersion
from app.models.blockchain import Certificate, BlockchainTransaction
from app.services.blockchain_service import blockchain_service


ADMIN_ROLES = ('admin', 'asset_admin', 'license_admin', 'adm1', 'adm2')


def _can_view_asset_for_user(user, user_id, asset):
    """公开证书允许匿名查看已发布资产；未发布/已删除沿用资产可见性。"""
    if not asset:
        return False
    if asset.status == 'published':
        return True
    from app.resources.comments import can_view_asset
    return can_view_asset(user, user_id, asset)


def _current_version(asset):
    return AssetVersion.query.filter_by(asset_id=asset.id).order_by(
        AssetVersion.version_no.desc()
    ).first()


def _current_certificate(asset):
    if asset.certificate_id:
        certificate = Certificate.query.filter_by(
            certificate_id=asset.certificate_id
        ).first()
        if certificate:
            return certificate
    return Certificate.query.filter_by(asset_id=asset.id).order_by(
        Certificate.id.desc()
    ).first()


class BlockchainRegisterResource(Resource):
    """资产上链存证"""

    @jwt_required()
    def post(self):
        """提交资产存证（支持 async=true 异步执行）"""
        user_id = get_jwt_identity()
        user = User.query.get(user_id)

        data = request.get_json() or {}
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

        # 影像/矢量需要水印；模型/文档/视频没有盲水印能力，直接按文件哈希与版本存证
        if (
            asset.asset_type in ('image', 'vector')
            and asset.watermark_status not in ('embedded', 'verified')
        ):
            return {'code': 400, 'message': '上链前需先完成水印嵌入'}, 400

        version = _current_version(asset)
        certificate = _current_certificate(asset)
        if certificate and (
            (version and certificate.version_id == version.id) or
            (not version and certificate.file_hash == asset.file_hash)
        ):
            return {'code': 400, 'message': '当前版本已存证'}, 400

        if data.get('async') or request.args.get('async') in ('1', 'true', 'yes'):
            from app.services import task_service
            task, created = task_service.enqueue_task(
                'blockchain_register', asset, user
            )
            return {
                'code': 202,
                'message': '存证任务已提交' if created else '已有相同存证任务在处理',
                'data': {
                    'task_id': task.id,
                    'created': created,
                    'worker_enabled': bool(
                        current_app.config.get('TASK_WORKER_ENABLED', False)
                    ),
                    'task': task.to_dict()
                }
            }, 202

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
                    'version_id': result.get('version_id'),
                    'version_no': result.get('version_no'),
                    'simulated': result['simulated']
                }
            }, 200
        else:
            return {'code': 500, 'message': result['message']}, 500


class BlockchainVerifyResource(Resource):
    """存证验证"""

    def get(self, asset_id=None):
        """验证资产存证（公开核验仅限已发布资产）"""
        if not asset_id:
            return {'code': 400, 'message': '缺少资产ID'}, 400

        asset = Asset.query.get(asset_id)

        if not asset or asset.status != 'published':
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

        if not asset or asset.status != 'published':
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
                'asset_type': asset.asset_type,
                'watermark_id': asset.watermark_id,
                'garden_name': asset.garden.name if asset.garden else None,
                'created_at': (
                    asset.created_at.isoformat() if asset.created_at else None
                ),
                **result
            }
        }, 200


class BlockchainCertificateResource(Resource):
    """存证证书"""

    @jwt_required(optional=True)
    def get(self, certificate_id):
        """获取证书详情（公开证书仅限已发布资产）"""
        identity = get_jwt_identity()
        user = User.query.get(identity) if identity else None
        certificate = Certificate.query.filter_by(certificate_id=certificate_id).first()

        if not certificate:
            return {'code': 404, 'message': '证书不存在'}, 404

        asset = Asset.query.get(certificate.asset_id)
        if not _can_view_asset_for_user(user, identity, asset):
            return {'code': 404, 'message': '证书不存在'}, 404
        version = certificate.version
        current_version = _current_version(asset) if asset else None
        has_newer = bool(
            asset and current_version and certificate.version_id and
            current_version.id != certificate.version_id
        )

        return {
            'code': 200,
            'data': {
                'certificate': certificate.to_dict(),
                'version': {
                    'id': version.id if version else certificate.version_id,
                    'version_no': (
                        version.version_no if version else certificate.version_no
                    ),
                    'file_name': version.file_name if version else None,
                    'file_format': version.file_format if version else None,
                    'file_size': version.file_size if version else None,
                    'file_hash': version.file_hash if version else certificate.file_hash,
                    'created_at': (
                        version.created_at.isoformat()
                        if version and version.created_at else None
                    )
                },
                'is_current_version': not has_newer,
                'has_newer_version': has_newer,
                'current_version_no': (
                    current_version.version_no if current_version else None
                ),
                'certificate_count': (
                    Certificate.query.filter_by(asset_id=asset.id).count()
                    if asset else 1
                ),
                'simulated': not blockchain_service.enabled,
                'chain_mode': (
                    'simulated' if not blockchain_service.enabled else 'fisco-bcos'
                ),
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
        identity = get_jwt_identity()
        user = User.query.get(identity)

        if asset_id:
            asset = Asset.query.get(asset_id)
            if not asset:
                return {'code': 404, 'message': '资产不存在'}, 404
            if not _can_view_asset_for_user(user, identity, asset):
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
            # 全平台证书列表只给管理员，避免普通用户枚举未发布资产
            if not user or user.role not in ADMIN_ROLES:
                return {'code': 403, 'message': '无权限查看全平台存证记录'}, 403

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
                    'version_id': cert.version_id,
                    'version_no': cert.version_no,
                    'tx_hash': cert.tx_hash,
                    'block_number': cert.block_number,
                    # 兼容旧字段名：证书创建即确认时间
                    'confirmed_at': cert.created_at.isoformat() if cert.created_at else None
                })

            return {'code': 200, 'data': result}, 200


class BlockchainStatusResource(Resource):
    """区块链状态"""

    @jwt_required(optional=True)
    def get(self):
        """获取区块链连接状态（RPC 地址只返回给管理员）"""
        identity = get_jwt_identity()
        user = User.query.get(identity) if identity else None
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

        data = {
            'connected': connected,
            'simulated': not blockchain_service.enabled,
            'rpc_configured': bool(blockchain_service.rpc_url),
            'total_certificates': total_certificates,
            'pending_assets': pending_assets,
            'node_status': node_status,
        }
        if user and user.role in ADMIN_ROLES:
            data['rpc_url'] = blockchain_service.rpc_url
        return {'code': 200, 'data': data}, 200