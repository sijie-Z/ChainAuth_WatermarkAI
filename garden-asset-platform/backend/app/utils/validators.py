"""
数据验证器
"""
import re
from datetime import datetime


def validate_username(username):
    """验证用户名"""
    if not username:
        return False, "用户名不能为空"
    if len(username) < 3:
        return False, "用户名至少3个字符"
    if len(username) > 50:
        return False, "用户名最多50个字符"
    if not re.match(r'^[a-zA-Z0-9_]+$', username):
        return False, "用户名只能包含字母、数字和下划线"
    return True, ""


def validate_password(password):
    """验证密码"""
    if not password:
        return False, "密码不能为空"
    if len(password) < 6:
        return False, "密码至少6个字符"
    if len(password) > 100:
        return False, "密码最多100个字符"
    return True, ""


def validate_email(email):
    """验证邮箱"""
    if not email:
        return True, ""  # 邮箱可选
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(pattern, email):
        return False, "邮箱格式不正确"
    return True, ""


def validate_phone(phone):
    """验证手机号"""
    if not phone:
        return True, ""  # 手机号可选
    pattern = r'^1[3-9]\d{9}$'
    if not re.match(pattern, phone):
        return False, "手机号格式不正确"
    return True, ""


def validate_asset_code(asset_code):
    """验证资产编码"""
    if not asset_code:
        return False, "资产编码不能为空"
    pattern = r'^[A-Z]{2,4}-(IMG|MDL|VEC|DOC|VID)-\d{14}-[A-F0-9]{4}$'
    if not re.match(pattern, asset_code):
        return False, "资产编码格式不正确"
    return True, ""


def validate_watermark_id(watermark_id):
    """验证水印ID"""
    if not watermark_id:
        return False, "水印ID不能为空"
    pattern = r'^ZY-[A-Z]{2,4}-(IMG|MDL|VEC|DOC|VID)-\d{14}-[A-F0-9]{4}$'
    if not re.match(pattern, watermark_id):
        return False, "水印ID格式不正确"
    return True, ""


def validate_license_type(license_type):
    """验证授权类型"""
    valid_types = ['personal', 'academic', 'commercial', 'display', 'derivative']
    if license_type not in valid_types:
        return False, f"授权类型必须是: {', '.join(valid_types)}"
    return True, ""


def validate_date_format(date_str, fmt='%Y-%m-%d'):
    """验证日期格式"""
    if not date_str:
        return True, ""
    try:
        datetime.strptime(date_str, fmt)
        return True, ""
    except ValueError:
        return False, f"日期格式不正确，应为: {fmt}"


def validate_file_extension(filename, allowed_extensions):
    """验证文件扩展名"""
    if not filename:
        return False, "文件名不能为空"
    ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
    if ext not in [e.lstrip('.') for e in allowed_extensions]:
        return False, f"不支持的文件类型，允许: {', '.join(allowed_extensions)}"
    return True, ""


def validate_file_size(size_bytes, max_mb=100):
    """验证文件大小"""
    max_bytes = max_mb * 1024 * 1024
    if size_bytes > max_bytes:
        return False, f"文件大小不能超过 {max_mb}MB"
    return True, ""


def sanitize_text(text):
    """
    清理文本中的HTML标签和脚本，防止XSS攻击

    Args:
        text: 原始文本

    Returns:
        清理后的文本
    """
    if not text:
        return text
    # 移除HTML标签
    import html
    text = html.escape(str(text))
    return text


def has_html_tags(text):
    """
    检查文本是否包含HTML标签

    Args:
        text: 待检查文本

    Returns:
        True如果包含HTML标签
    """
    if not text:
        return False
    value = str(text)
    if '<' not in value or '>' not in value:
        return False
    # 单次线性扫描，避免正则回溯；只判断是否存在成对尖括号。
    start = value.find('<')
    while start != -1:
        end = value.find('>', start + 1)
        if end > start + 1:
            return True
        start = value.find('<', start + 1)
    return False