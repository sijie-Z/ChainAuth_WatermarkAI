"""
测试环境配置
"""
import os

class TestingConfig:
    """测试环境配置"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = 'test-secret-key'
    JWT_SECRET_KEY = 'test-jwt-secret'

    # 禁用CSRF
    WTF_CSRF_ENABLED = False

    # 文件上传配置
    UPLOAD_FOLDER = './test_uploads'
    WATERMARK_FOLDER = './test_uploads/watermarked'
    EXTRACTED_FOLDER = './test_uploads/extracted'
    MAX_CONTENT_LENGTH = 10485760

    # 区块链配置 (测试环境禁用)
    BLOCKCHAIN_ENABLED = False

    # AI配置
    ZHIPU_API_KEY = 'test-api-key'

    # Celery配置
    CELERY_BROKER_URL = 'memory://'
    CELERY_RESULT_BACKEND = 'cache+memory://'