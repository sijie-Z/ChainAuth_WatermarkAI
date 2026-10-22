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

    # 生产环境必须配置密钥；未配置时生成一次并持久化到 instance 目录，
    # 保证多 worker / 重启后密钥一致（否则各 gunicorn worker 各自随机，Token 互不认）。
    @staticmethod
    def init_app(app):
        if app.config.get('TESTING'):
            return
        app.config['SECRET_KEY'] = Config._persistent_secret(app, 'SECRET_KEY', '.secret_key')
        app.config['JWT_SECRET_KEY'] = Config._persistent_secret(app, 'JWT_SECRET_KEY', '.jwt_secret_key')

    @staticmethod
    def _persistent_secret(app, key, filename):
        value = app.config.get(key) or ''
        if value:
            return value

        import secrets
        import time
        import warnings

        os.makedirs(app.instance_path, exist_ok=True)
        path = os.path.join(app.instance_path, filename)
        for _ in range(10):
            try:
                fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            except FileExistsError:
                try:
                    with open(path, 'r', encoding='utf-8') as handle:
                        saved = handle.read().strip()
                except OSError:
                    saved = ''
                if saved:
                    warnings.warn(f'{key} 未设置，复用 {path} 中已持久化的密钥')
                    return saved
                time.sleep(0.05)
                continue
            else:
                generated = secrets.token_hex(32)
                with os.fdopen(fd, 'w', encoding='utf-8') as handle:
                    handle.write(generated)
                warnings.warn(f'{key} 未设置，已生成并持久化到 {path}')
                return generated

        raise RuntimeError(f'{key} 未配置，且无法在 {path} 生成持久化密钥')
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=24)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)
    # Flask-JWT-Extended 4.7+ 默认按 RFC 7519 校验 sub 必须是字符串；
    # 本项目历史 Token 以整数 user.id 作为 identity，关闭该校验以保持兼容。
    JWT_VERIFY_SUB = False

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

    # 仅在确认后端不直接对外暴露（例如只经 nginx 反代）时开启，
    # 否则客户端可伪造 X-Forwarded-For 绕过限流。
    TRUST_PROXY_HEADERS = os.environ.get(
        'TRUST_PROXY_HEADERS', 'false'
    ).lower() == 'true'

    # 限流配置
    RATELIMIT_ENABLED = os.environ.get('RATELIMIT_ENABLED', 'true').lower() == 'true'
    RATELIMIT_LOGIN = int(os.environ.get('RATELIMIT_LOGIN', '5'))
    RATELIMIT_LOGIN_WINDOW = int(os.environ.get('RATELIMIT_LOGIN_WINDOW', '60'))
    RATELIMIT_REGISTER = int(os.environ.get('RATELIMIT_REGISTER', '3'))
    RATELIMIT_REGISTER_WINDOW = int(os.environ.get('RATELIMIT_REGISTER_WINDOW', '3600'))
    RATELIMIT_API = int(os.environ.get('RATELIMIT_API', '100'))
    RATELIMIT_API_WINDOW = int(os.environ.get('RATELIMIT_API_WINDOW', '60'))

    # 任务调度器：多 worker 部署（gunicorn 4 workers）会各自启动一份，默认关闭避免重复执行
    SCHEDULER_ENABLED = os.environ.get('SCHEDULER_ENABLED', 'false').lower() == 'true'

    # 异步任务队列：开发环境默认启动进程内 worker；
    # 生产环境建议保持关闭并用 `flask tasks run` 单独跑 worker，
    # 避免多个 gunicorn worker 各自轮询（任务领取有原子保护，但会浪费连接）。
    TASK_WORKER_ENABLED = os.environ.get(
        'TASK_WORKER_ENABLED', 'false'
    ).lower() == 'true'
    TASK_WORKER_POLL_INTERVAL = float(
        os.environ.get('TASK_WORKER_POLL_INTERVAL', '1.0')
    )
    TASK_MAX_ATTEMPTS = int(os.environ.get('TASK_MAX_ATTEMPTS', '3'))
    TASK_STUCK_TIMEOUT_MINUTES = int(
        os.environ.get('TASK_STUCK_TIMEOUT_MINUTES', '15')
    )

    # 站内实时通知（SSE）
    SSE_ENABLED = os.environ.get('SSE_ENABLED', 'true').lower() == 'true'
    SSE_MAX_SECONDS = int(os.environ.get('SSE_MAX_SECONDS', '300'))
    SSE_POLL_INTERVAL = float(os.environ.get('SSE_POLL_INTERVAL', '5'))
    SSE_MAX_CONNECTIONS_PER_USER = int(
        os.environ.get('SSE_MAX_CONNECTIONS_PER_USER', '3')
    )

    # 邮件通知（默认关闭；配置 SMTP 后可在账号设置中开启）
    MAIL_ENABLED = os.environ.get('MAIL_ENABLED', 'false').lower() == 'true'
    MAIL_HOST = os.environ.get('MAIL_HOST', '')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', '587'))
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME', '')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD', '')
    MAIL_FROM = os.environ.get('MAIL_FROM', '')
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() == 'true'
    MAIL_USE_SSL = os.environ.get('MAIL_USE_SSL', 'false').lower() == 'true'
    MAIL_TIMEOUT = int(os.environ.get('MAIL_TIMEOUT', '10'))
    PUBLIC_BASE_URL = os.environ.get('PUBLIC_BASE_URL', 'http://localhost:5173')


class DevelopmentConfig(Config):
    """开发环境配置"""
    DEBUG = True
    TASK_WORKER_ENABLED = os.environ.get(
        'TASK_WORKER_ENABLED', 'true'
    ).lower() == 'true'


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
    # AI 依赖（torch/CLIP/Milvus）因机器而异，测试固定关闭以保证确定性
    AI_ENABLED = False
    BLOCKCHAIN_ENABLED = False
    SCHEDULER_ENABLED = False
    TASK_WORKER_ENABLED = False
    SSE_MAX_SECONDS = 1
    SSE_POLL_INTERVAL = 0.2
    MAIL_ENABLED = False


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
