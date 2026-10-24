"""
功能开关配置
控制各模块的启用状态
"""
import os

# 水印功能
WATERMARK_ENABLED = os.environ.get('WATERMARK_ENABLED', 'true').lower() == 'true'

# 区块链功能
BLOCKCHAIN_ENABLED = os.environ.get('BLOCKCHAIN_ENABLED', 'false').lower() == 'true'

# AI功能
AI_ENABLED = os.environ.get('AI_ENABLED', 'true').lower() == 'true'

# 向量检索
VECTOR_SEARCH_ENABLED = os.environ.get('VECTOR_SEARCH_ENABLED', 'true').lower() == 'true'

# 对象存储
OBJECT_STORAGE_ENABLED = os.environ.get('OBJECT_STORAGE_ENABLED', 'false').lower() == 'true'

# 异步任务
TASK_WORKER_ENABLED = os.environ.get('TASK_WORKER_ENABLED', 'false').lower() == 'true'

# 操作日志
OPERATION_LOG_ENABLED = os.environ.get('OPERATION_LOG_ENABLED', 'true').lower() == 'true'

# 文件去重
FILE_DEDUP_ENABLED = os.environ.get('FILE_DEDUP_ENABLED', 'true').lower() == 'true'

# 注册功能
REGISTER_ENABLED = os.environ.get('REGISTER_ENABLED', 'true').lower() == 'true'

# 功能配置字典
FEATURE_FLAGS = {
    'watermark': WATERMARK_ENABLED,
    'blockchain': BLOCKCHAIN_ENABLED,
    'ai': AI_ENABLED,
    'vector_search': VECTOR_SEARCH_ENABLED,
    'object_storage': OBJECT_STORAGE_ENABLED,
    'task_worker': TASK_WORKER_ENABLED,
    'operation_log': OPERATION_LOG_ENABLED,
    'file_dedup': FILE_DEDUP_ENABLED,
    'register': REGISTER_ENABLED
}


def is_enabled(feature_name):
    """检查功能是否启用"""
    return FEATURE_FLAGS.get(feature_name, False)


def get_enabled_features():
    """获取所有启用的功能"""
    return [k for k, v in FEATURE_FLAGS.items() if v]