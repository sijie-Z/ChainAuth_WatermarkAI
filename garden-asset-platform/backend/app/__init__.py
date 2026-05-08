"""
Flask 应用工厂
"""
import os
import logging
from flask import Flask, jsonify
from werkzeug.exceptions import HTTPException

from app.config import config
from app.extensions import init_extensions


def create_app(config_name='default'):
    """
    创建Flask应用实例

    Args:
        config_name: 配置名称 (development/production/testing)

    Returns:
        Flask应用实例
    """
    app = Flask(__name__)
    app.config.from_object(config[config_name])

    # 初始化扩展
    init_extensions(app)

    # 配置日志
    setup_logging(app)

    # 注册错误处理
    register_error_handlers(app)

    # 注册请求钩子
    register_request_hooks(app)

    # 注册JWT回调
    register_jwt_callbacks(app)

    # 注册CLI命令
    register_commands(app)

    # 注册API资源
    register_api_resources(app)

    # 初始化业务服务
    init_services(app)

    # 创建必要的目录
    create_folders(app)

    # 健康检查端点
    @app.route('/health')
    def health_check():
        return jsonify({'status': 'healthy', 'service': 'garden-asset-platform'})

    return app


def setup_logging(app):
    """配置日志"""
    from app.utils.logger import setup_logging as _setup_logging
    _setup_logging(app)


def register_error_handlers(app):
    """注册错误处理器"""
    from app.utils.errors import register_error_handlers as _register
    _register(app)


def register_request_hooks(app):
    """注册请求钩子"""
    from app.utils.middleware import request_logger, security_headers
    request_logger(app)
    security_headers(app)


def register_jwt_callbacks(app):
    """注册JWT回调"""
    from app.utils.jwt_callbacks import init_jwt_callbacks
    init_jwt_callbacks(app)


def register_commands(app):
    """注册CLI命令"""
    from app.utils.commands import register_commands as _register
    _register(app)


def register_api_resources(app):
    """注册API资源"""
    from flask_restful import Api
    api = Api(app, prefix='/api')

    # 认证相关
    from app.resources.auth import (
        RegisterResource, LoginResource, LogoutResource,
        RefreshTokenResource, CurrentUserResource,
        UserListResource, UserResource, ChangePasswordResource
    )
    api.add_resource(RegisterResource, '/register')
    api.add_resource(LoginResource, '/login')
    api.add_resource(LogoutResource, '/logout')
    api.add_resource(RefreshTokenResource, '/refresh')
    api.add_resource(CurrentUserResource, '/user/current')
    api.add_resource(ChangePasswordResource, '/user/change-password')
    api.add_resource(UserListResource, '/users')
    api.add_resource(UserResource, '/users/<int:user_id>')

    # 资产相关
    from app.resources.asset import (
        AssetListResource, AssetResource, AssetUploadResource,
        AssetDownloadResource, AssetFavoriteResource, AssetStatsResource,
        MyAssetsResource, AssetTagsResource, AssetPublishResource, AssetApproveResource,
        PublicStatsResource
    )
    api.add_resource(PublicStatsResource, '/stats')
    api.add_resource(AssetListResource, '/assets')
    api.add_resource(AssetResource, '/assets/<string:asset_id>')
    api.add_resource(AssetUploadResource, '/assets/upload')
    api.add_resource(AssetDownloadResource, '/assets/<string:asset_id>/download')
    api.add_resource(AssetFavoriteResource, '/assets/<string:asset_id>/favorite')
    api.add_resource(AssetStatsResource, '/assets/stats')
    api.add_resource(MyAssetsResource, '/assets/my')
    api.add_resource(AssetTagsResource, '/assets/<string:asset_id>/tags')
    api.add_resource(AssetPublishResource, '/assets/<string:asset_id>/publish')
    api.add_resource(AssetApproveResource, '/assets/<string:asset_id>/approve')

    # 园林相关
    from app.resources.garden import GardenListResource, GardenResource, GardenStatsResource
    api.add_resource(GardenListResource, '/gardens')
    api.add_resource(GardenResource, '/gardens/<int:garden_id>')
    api.add_resource(GardenStatsResource, '/gardens/<int:garden_id>/stats')

    # 水印相关
    from app.resources.watermark import (
        WatermarkEmbedResource, WatermarkExtractResource,
        WatermarkVerifyResource, WatermarkTraceResource,
        WatermarkLogsResource
    )
    api.add_resource(WatermarkEmbedResource, '/watermark/embed')
    api.add_resource(WatermarkExtractResource, '/watermark/extract')
    api.add_resource(WatermarkVerifyResource, '/watermark/verify')
    api.add_resource(WatermarkTraceResource, '/watermark/trace')
    api.add_resource(WatermarkLogsResource, '/watermark/logs')

    # 区块链相关
    from app.resources.blockchain import (
        BlockchainRegisterResource, BlockchainVerifyResource,
        BlockchainCertificateResource, BlockchainHistoryResource,
        BlockchainStatusResource
    )
    api.add_resource(BlockchainRegisterResource, '/blockchain/register')
    api.add_resource(BlockchainVerifyResource, '/blockchain/verify', '/blockchain/verify/<string:asset_id>')
    api.add_resource(BlockchainCertificateResource, '/blockchain/certificate/<string:certificate_id>')
    api.add_resource(BlockchainHistoryResource, '/blockchain/history', '/blockchain/history/<string:asset_id>')
    api.add_resource(BlockchainStatusResource, '/blockchain/status')

    # AI相关
    from app.resources.ai import (
        AIAnalyzeResource, AISearchResource,
        AIInfringementResource, AIChatResource
    )
    api.add_resource(AIAnalyzeResource, '/ai/analyze')
    api.add_resource(AISearchResource, '/ai/search')
    api.add_resource(AIInfringementResource, '/ai/infringement')
    api.add_resource(AIChatResource, '/ai/chat')

    # 授权相关
    from app.resources.license import (
        LicenseApplyResource, LicensePendingResource,
        LicenseApproveResource, LicenseApprovedResource,
        MyLicenseResource
    )
    api.add_resource(LicenseApplyResource, '/license/apply')
    api.add_resource(LicensePendingResource, '/license/pending')
    api.add_resource(LicenseApproveResource, '/license/approve/<int:application_id>')
    api.add_resource(LicenseApprovedResource, '/license/approved')
    api.add_resource(MyLicenseResource, '/license/my')


def init_services(app):
    """初始化业务服务"""
    from app.services.ai_service import ai_service
    from app.services.blockchain_service import blockchain_service

    ai_service.init_app(app)
    blockchain_service.init_app(app)


def create_folders(app):
    """创建必要的文件夹"""
    folders = [
        app.config.get('UPLOAD_FOLDER', './uploads'),
        app.config.get('WATERMARK_FOLDER', './watermarks'),
        app.config.get('EXTRACTED_FOLDER', './extracted'),
        './logs',
        './data/watermark',
        './data/models',
    ]

    for folder in folders:
        if folder and not os.path.exists(folder):
            os.makedirs(folder, exist_ok=True)