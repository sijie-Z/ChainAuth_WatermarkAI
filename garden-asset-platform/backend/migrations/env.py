"""
迁移环境配置
"""
import os
from flask_migrate import Migrate
from app import create_app
from app.extensions import db

app = create_app(os.environ.get('FLASK_ENV', 'development'))
migrate = Migrate(app, db)

# 导入所有模型以便迁移识别
from app.models import *
