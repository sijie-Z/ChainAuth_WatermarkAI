"""
应用配置模块
"""
import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()


class Config:
    """基础配置"""
    SECRET_KEY = os.environ.get('SECRET_KEY', '')
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', '')

    # 生产环境必须配置密钥
    @staticmethod
    def init_app(app):
        if not app.config.get('SECRET_KEY') or app.config['SECRET_KEY'] == '':
            if not app.config.get('TESTING'):
                import warnings
                warnings.warn('SECRET_KEY 未设置！使用随机密钥（重启后会话失效）')
                import secrets
                app.config['SECRET_KEY'] = secrets.token_hex(32)
        if not app.config.get('JWT_SECRET_KEY') or app.config['JWT_SECRET_KEY'] == '':
            if not app.config.get('TESTING'):
                import warnings
                warnings.warn('JWT_SECRET_KEY 未设置！使用随机密钥（重启后Token失效）')
                import secrets
                app.config['JWT_SECRET_KEY'] = secrets.token_hex(32)
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=24)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)

    # 数据库配置
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL',
        'sqlite:///garden_asset.db'  # 默认使用SQLite
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Redis配置
    REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')

    # MinIO配置
    MINIO_ENDPOINT = os.environ.get('MINIO_ENDPOINT', 'localhost:9000')
    MINIO_ACCESS_KEY = os.environ.get('MINIO_ACCESS_KEY', 'minioadmin')
    MINIO_SECRET_KEY = os.environ.get('MINIO_SECRET_KEY', 'minioadmin')
    MINIO_BUCKET = os.environ.get('MINIO_BUCKET', 'garden-assets')
    MINIO_SECURE = os.environ.get('MINIO_SECURE', 'false').lower() == 'true'

    # 区块链配置
    BLOCKCHAIN_ENABLED = os.environ.get('BLOCKCHAIN_ENABLED', 'false').lower() == 'true'
    BLOCKCHAIN_RPC_URL = os.environ.get('BLOCKCHAIN_RPC_URL', 'http://localhost:20200')
    CONTRACT_ADDRESS = os.environ.get('CONTRACT_ADDRESS', '')
    CHAIN_ID = int(os.environ.get('CHAIN_ID', '1'))
    PRIVATE_KEY = os.environ.get('PRIVATE_KEY', '')

    # AI配置
    AI_ENABLED = os.environ.get('AI_ENABLED', 'true').lower() == 'true'
    ZHIPU_API_KEY = os.environ.get('ZHIPU_API_KEY', '')
    MILVUS_DB_PATH = os.environ.get('MILVUS_DB_PATH', './data/milvus.db')

    # 百度OCR配置
    BAIDU_OCR_APP_ID = os.environ.get('BAIDU_OCR_APP_ID', '')
    BAIDU_OCR_API_KEY = os.environ.get('BAIDU_OCR_API_KEY', '')
    BAIDU_OCR_SECRET_KEY = os.environ.get('BAIDU_OCR_SECRET_KEY', '')

    # 文件存储路径
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER', './uploads')
    WATERMARK_FOLDER = os.environ.get('WATERMARK_FOLDER', './watermarks')
    EXTRACTED_FOLDER = os.environ.get('EXTRACTED_FOLDER', './extracted')

    # 文件上传大小限制 (500MB)
    MAX_CONTENT_LENGTH = int(os.environ.get('MAX_CONTENT_LENGTH', str(500 * 1024 * 1024)))

    # CORS 配置
    CORS_ORIGINS = os.environ.get('CORS_ORIGINS', '*')

    # 限流配置
    RATELIMIT_ENABLED = os.environ.get('RATELIMIT_ENABLED', 'true').lower() == 'true'
    RATELIMIT_LOGIN = int(os.environ.get('RATELIMIT_LOGIN', '5'))
    RATELIMIT_LOGIN_WINDOW = int(os.environ.get('RATELIMIT_LOGIN_WINDOW', '60'))
    RATELIMIT_REGISTER = int(os.environ.get('RATELIMIT_REGISTER', '3'))
    RATELIMIT_REGISTER_WINDOW = int(os.environ.get('RATELIMIT_REGISTER_WINDOW', '3600'))
    RATELIMIT_API = int(os.environ.get('RATELIMIT_API', '100'))
    RATELIMIT_API_WINDOW = int(os.environ.get('RATELIMIT_API_WINDOW', '60'))


class DevelopmentConfig(Config):
    """开发环境配置"""
    DEBUG = True


class ProductionConfig(Config):
    """生产环境配置"""
    DEBUG = False
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    PREFERRED_URL_SCHEME = 'https'


class TestingConfig(Config):
    """测试环境配置"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    # 测试使用固定密钥，保证 JWT 可签发；生产环境仍要求显式配置
    SECRET_KEY = 'testing-secret-key-not-for-production'
    JWT_SECRET_KEY = 'testing-jwt-secret-key-not-for-production'
    # 测试之间共享进程内存，限流会串扰；限流本身不在这里验证
    RATELIMIT_ENABLED = False


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
