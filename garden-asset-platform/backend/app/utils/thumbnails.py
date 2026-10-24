"""资产缩略图生成

缩略图按资产 UUID 命名存放在 UPLOAD_FOLDER/thumbnails 下，
对外只通过 /api/assets/<id>/thumbnail 提供，避免暴露原始文件路径。
"""
import os

from flask import current_app
from PIL import Image, ImageOps

THUMBNAIL_DIRNAME = 'thumbnails'
DEFAULT_MAX_SIZE = (1600, 1600)
CARD_MAX_SIZE = (640, 640)


def thumbnail_dir():
    base = os.path.abspath(current_app.config.get('UPLOAD_FOLDER', './uploads'))
    path = os.path.join(base, THUMBNAIL_DIRNAME)
    os.makedirs(path, exist_ok=True)
    return path


def generate_thumbnail(source_path, asset_id, max_size=DEFAULT_MAX_SIZE, suffix=''):
    """从图片生成 JPEG 缩略图，返回相对 UPLOAD_FOLDER 的路径。

    失败时抛出异常，由调用方决定是否忽略。
    """
    if not source_path or not os.path.isfile(source_path):
        raise FileNotFoundError(source_path)

    out_path = os.path.join(thumbnail_dir(), f'{asset_id}{suffix}.jpg')
    with Image.open(source_path) as image:
        image = ImageOps.exif_transpose(image)
        image = image.convert('RGB')
        image.thumbnail(max_size, Image.Resampling.LANCZOS)
        image.save(out_path, 'JPEG', quality=84, optimize=True)

    return f'{THUMBNAIL_DIRNAME}/{asset_id}{suffix}.jpg'


def generate_thumbnail_set(source_path, asset_id):
    """同时生成详情用大图与列表用卡片图，返回 (大图路径, 卡片图路径)。"""
    detail = generate_thumbnail(source_path, asset_id)
    card = generate_thumbnail(source_path, asset_id, max_size=CARD_MAX_SIZE, suffix='-card')
    return detail, card

