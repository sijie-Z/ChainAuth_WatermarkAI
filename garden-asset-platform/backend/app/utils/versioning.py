"""
API版本控制
"""
from flask import request

API_VERSION = 'v1'
API_PREFIX = f'/api/{API_VERSION}'


def get_api_version():
    """获取当前API版本"""
    return API_VERSION


def versioned_url(path):
    """生成带版本的URL"""
    return f'{API_PREFIX}{path}'


# 版本兼容性映射
VERSION_COMPATIBILITY = {
    'v1': {
        'deprecated': False,
        'sunset_date': None,
        'migration_guide': None
    }
}


def check_version_compatibility(version):
    """检查版本兼容性"""
    info = VERSION_COMPATIBILITY.get(version)
    if not info:
        return False, '不支持的API版本'

    if info['deprecated']:
        return True, f'此API版本已弃用，将于{info["sunset_date"]}下线'

    return True, None