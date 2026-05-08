"""
Flask 扩展初始化
"""
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager
from flask_cors import CORS

db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()


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
