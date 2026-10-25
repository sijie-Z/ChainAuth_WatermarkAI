"""文件路径安全工具

用户上传只决定“允许的扩展名”，不直接进入磁盘路径；实际文件名使用
服务端生成的 UUID。扩展名通过白名单映射成常量，避免路径注入与
大小写/别名绕过后缀校验。
"""
import os
import uuid


IMAGE_EXT_ALIASES = {
    '.png': '.png',
    '.jpg': '.jpg',
    '.jpeg': '.jpg',
    '.bmp': '.bmp',
    '.tif': '.tiff',
    '.tiff': '.tiff',
    '.webp': '.webp',
    '.gif': '.gif',
}

REPORT_EXT_ALIASES = {
    **IMAGE_EXT_ALIASES,
    '.zip': '.zip',
}

VERSION_EXT_ALIASES = {
    **IMAGE_EXT_ALIASES,
    '.shp': '.shp',
    '.geojson': '.geojson',
    '.kml': '.kml',
    '.kmz': '.kmz',
    '.zip': '.zip',
    '.dwg': '.dwg',
    '.dxf': '.dxf',
    '.pdf': '.pdf',
    '.doc': '.doc',
    '.docx': '.docx',
    '.xls': '.xls',
    '.xlsx': '.xlsx',
    '.ppt': '.ppt',
    '.pptx': '.pptx',
    '.txt': '.txt',
    '.md': '.md',
    '.mp4': '.mp4',
    '.mov': '.mov',
    '.avi': '.avi',
    '.mkv': '.mkv',
    '.glb': '.glb',
    '.gltf': '.gltf',
    '.stl': '.stl',
    '.obj': '.obj',
    '.fbx': '.fbx',
}


def canonical_extension(filename, aliases):
    """返回白名单内的常量扩展名；不支持时返回 None。"""
    raw_ext = os.path.splitext(filename or '')[1].lower()
    return aliases.get(raw_ext)


def uuid_filename(extension=''):
    """生成不含任何用户路径成分的文件名。"""
    return f'{uuid.uuid4().hex}{extension}'


def path_inside(base, filename):
    """把文件名限制在 base 目录内，防止 .. / 绝对路径逃逸。"""
    base_real = os.path.realpath(base)
    candidate = os.path.realpath(os.path.join(base_real, filename))
    if os.path.commonpath([base_real, candidate]) != base_real:
        raise ValueError('path escapes base directory')
    return candidate
