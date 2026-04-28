"""
文件工具函数
"""
import os
import uuid
import hashlib
from datetime import datetime
from werkzeug.utils import secure_filename


def generate_unique_filename(original_filename):
    """生成唯一文件名"""
    ext = os.path.splitext(original_filename)[1]
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    unique_id = uuid.uuid4().hex[:8]
    return f"{timestamp}_{unique_id}{ext}"


def calculate_file_hash(file_path):
    """计算文件哈希值"""
    sha256 = hashlib.sha256()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b''):
            sha256.update(chunk)
    return sha256.hexdigest()


def get_file_extension(filename):
    """获取文件扩展名"""
    return os.path.splitext(filename)[1].lower()


def allowed_file(filename, allowed_extensions):
    """检查文件扩展名是否允许"""
    return '.' in filename and get_file_extension(filename) in allowed_extensions


def get_file_size(file_path):
    """获取文件大小（字节）"""
    return os.path.getsize(file_path)


def format_file_size(size_bytes):
    """格式化文件大小"""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.2f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.2f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"


# 允许的文件类型
ALLOWED_EXTENSIONS = {
    'image': {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.tif'},
    'vector': {'.shp', '.shx', '.dbf', '.prj', '.zip'},
    'document': {'.pdf', '.doc', '.docx'},
    'video': {'.mp4', '.avi', '.mov', '.mkv'},
    'model': {'.obj', '.fbx', '.gltf', '.glb'}
}


def get_asset_type(filename):
    """根据文件扩展名判断资产类型"""
    ext = get_file_extension(filename)
    for asset_type, extensions in ALLOWED_EXTENSIONS.items():
        if ext in extensions:
            return asset_type
    return 'other'
