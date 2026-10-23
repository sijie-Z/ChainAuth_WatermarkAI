"""
API权限配置
定义每个API端点需要的权限
"""

API_PERMISSIONS = {
    # 公开接口 (无需认证)
    'public': [
        '/api/register',
        '/api/login',
        '/api/gardens',
        '/api/gardens/<id>',
        '/api/watermark/verify',
        '/api/watermark/trace',
        '/api/blockchain/verify',
        '/api/blockchain/certificate/<id>',
        '/api/blockchain/status',
        '/api/infringements/report',
    ],

    # 用户接口 (需要登录)
    'user': [
        '/api/logout',
        '/api/user/current',
        '/api/assets',
        '/api/assets/<id>',
        '/api/assets/upload',
        '/api/watermark/embed',
        '/api/watermark/extract',
        '/api/license/apply',
        '/api/license/my',
        '/api/infringements/mine',
    ],

    # 审批员接口
    'approver': [
        '/api/license/pending',
        '/api/license/approve/<id>',
    ],

    # 管理员接口
    'admin': [
        '/api/users',
        '/api/users/<id>',
        '/api/watermark/logs',
        '/api/blockchain/history',
        '/api/license/usage-report',
        '/api/infringements',
        '/api/infringements/<id>',
        '/api/infringements/<id>/review',
        '/api/infringements/<id>/file',
        '/api/infringements/patrol',
    ],
}

# 角色权限映射
ROLE_PERMISSIONS = {
    'user': ['public', 'user'],
    'asset_admin': ['public', 'user', 'admin'],
    'license_admin': ['public', 'user', 'approver', 'admin'],
    'adm1': ['public', 'user', 'approver'],
    'adm2': ['public', 'user', 'approver'],
    'admin': ['public', 'user', 'approver', 'admin'],
}


def check_api_permission(path, role):
    """检查API权限"""
    # 公开接口无需检查
    for pattern in API_PERMISSIONS['public']:
        if match_path(pattern, path):
            return True

    # 检查角色权限
    allowed_groups = ROLE_PERMISSIONS.get(role, ['public'])

    for group in allowed_groups:
        for pattern in API_PERMISSIONS.get(group, []):
            if match_path(pattern, path):
                return True

    return False


def match_path(pattern, path):
    """匹配路径模式"""
    # 简化匹配，实际可用正则
    pattern_parts = pattern.split('/')
    path_parts = path.split('/')

    if len(pattern_parts) != len(path_parts):
        return False

    for p, a in zip(pattern_parts, path_parts):
        if p.startswith('<') and p.endswith('>'):
            continue  # 参数占位符
        if p != a:
            return False

    return True