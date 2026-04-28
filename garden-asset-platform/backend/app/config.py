"""
应用配置模块
"""
import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """基础配置"""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY') or 'dev-jwt-secret-change-in-production'
    JWT_ACCESS_TOKEN_EXPIRES = 24 * 60 * 60  # 24小时
    JWT_REFRESH_TOKEN_EXPIRES = 30 * 24 * 60 * 60  # 30天

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


class DevelopmentConfig(Config):
    """开发环境配置"""
    DEBUG = True


class ProductionConfig(Config):
    """生产环境配置"""
    DEBUG = False


class TestingConfig(Config):
    """测试环境配置"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
