"""
项目配置汇总
包含所有可配置项及其说明
"""

# ===========================================
# 基础配置
# ===========================================

# 应用密钥 (必须修改)
SECRET_KEY = 'your-secret-key-here'
JWT_SECRET_KEY = 'your-jwt-secret-key-here'

# Token过期时间 (秒)
JWT_ACCESS_TOKEN_EXPIRES = 86400      # 24小时
JWT_REFRESH_TOKEN_EXPIRES = 2592000   # 30天

# ===========================================
# 数据库配置
# ===========================================

# PostgreSQL
DATABASE_URL = 'postgresql://user:password@localhost:5432/garden_asset'

# SQLite (开发用)
# DATABASE_URL = 'sqlite:///garden_asset.db'

# ===========================================
# Redis配置
# ===========================================

REDIS_URL = 'redis://localhost:6379/0'

# ===========================================
# 文件存储配置
# ===========================================

# 本地存储路径
UPLOAD_FOLDER = './uploads'
WATERMARK_FOLDER = './uploads/watermarked'
EXTRACTED_FOLDER = './uploads/extracted'

# 最大文件大小 (字节)
MAX_CONTENT_LENGTH = 104857600  # 100MB

# 允许的文件扩展名
ALLOWED_EXTENSIONS = {
    'image': ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff'],
    'vector': ['.shp', '.shx', '.dbf', '.prj', '.zip'],
    'document': ['.pdf', '.doc', '.docx'],
    'video': ['.mp4', '.avi', '.mov'],
    'model': ['.obj', '.fbx', '.gltf', '.glb']
}

# ===========================================
# 区块链配置 (FISCO BCOS)
# ===========================================

# 是否启用区块链
BLOCKCHAIN_ENABLED = False

# 节点RPC地址
BLOCKCHAIN_RPC_URL = 'http://127.0.0.1:20200'

# 链ID
CHAIN_ID = 1

# 合约地址
CONTRACT_ADDRESS = '0x...'

# 私钥 (重要：不要提交到版本控制)
PRIVATE_KEY = ''

# ===========================================
# AI配置
# ===========================================

# 是否启用AI功能
AI_ENABLED = True

# 智谱AI (GLM-4-Flash)
ZHIPU_API_KEY = 'your-zhipu-api-key'

# Milvus向量数据库
MILVUS_HOST = 'localhost'
MILVUS_PORT = 19530
MILVUS_COLLECTION = 'garden_assets'

# 模型路径
MODEL_PATH = './data/models'

# ===========================================
# MinIO对象存储配置
# ===========================================

STORAGE_BACKEND = 'local'
MINIO_ENDPOINT = 'localhost:9000'
MINIO_ACCESS_KEY = 'minioadmin'
MINIO_SECRET_KEY = 'minioadmin'
MINIO_BUCKET = 'garden-assets'
MINIO_SECURE = False

# ===========================================
# Celery配置
# ===========================================

CELERY_BROKER_URL = 'redis://localhost:6379/1'
CELERY_RESULT_BACKEND = 'redis://localhost:6379/1'

# ===========================================
# 邮件配置 (可选)
# ===========================================

MAIL_SERVER = 'smtp.example.com'
MAIL_PORT = 587
MAIL_USE_TLS = True
MAIL_USERNAME = ''
MAIL_PASSWORD = ''
MAIL_DEFAULT_SENDER = 'noreply@example.com'

# ===========================================
# 日志配置
# ===========================================

LOG_LEVEL = 'INFO'
LOG_FILE = './logs/app.log'
LOG_MAX_BYTES = 10485760  # 10MB
LOG_BACKUP_COUNT = 10

# ===========================================
# 功能开关
# ===========================================

# 注册功能
REGISTER_ENABLED = True

# 文件去重
FILE_DEDUP_ENABLED = True

# 操作日志
OPERATION_LOG_ENABLED = True

# ===========================================
# 园林数据
# ===========================================

GARDENS = [
    {'name': '拙政园', 'code': 'ZZY'},
    {'name': '留园', 'code': 'LY'},
    {'name': '狮子林', 'code': 'SZL'},
    {'name': '网师园', 'code': 'WSY'},
    {'name': '沧浪亭', 'code': 'CLT'},
    {'name': '耦园', 'code': 'OY'},
    {'name': '艺圃', 'code': 'YP'},
    {'name': '环秀山庄', 'code': 'HXSZ'},
    {'name': '怡园', 'code': 'YY'},
    {'name': '可园', 'code': 'KY'},
]