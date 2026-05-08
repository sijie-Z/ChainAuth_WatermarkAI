"""
Flask 扩展初始化
"""
import logging
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager
from flask_cors import CORS

logger = logging.getLogger(__name__)

db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()
redis_client = None


def init_extensions(app):
    """初始化所有扩展"""
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)

    # CORS: 从配置读取允许的源
    origins = app.config.get('CORS_ORIGINS', '*')
    if isinstance(origins, str):
        origins = [o.strip() for o in origins.split(',')]
    CORS(app, origins=origins)

    # Redis: 初始化限流客户端
    _init_redis(app)


def _init_redis(app):
    """初始化Redis客户端（用于限流）"""
    global redis_client
    redis_url = app.config.get('REDIS_URL')
    if not redis_url:
        logger.warning('REDIS_URL 未配置，限流功能将使用内存降级方案')
        return

    try:
        import redis
        redis_client = redis.from_url(redis_url, decode_responses=True)
        redis_client.ping()
        app.extensions['redis'] = redis_client
        logger.info(f'Redis 连接成功: {redis_url}')
    except Exception as e:
        logger.warning(f'Redis 连接失败，限流使用内存降级: {e}')
        redis_client = None
