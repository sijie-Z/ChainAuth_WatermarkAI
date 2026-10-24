"""下载指纹生成

在授权下载的影像副本底部叠加可见页脚（资产编码、授权编号、账号、指纹码），
原盲水印仍保留。每个授权+资产只生成一次，重复下载复用同一副本。
"""
import hashlib
import logging
import os

from flask import current_app
from PIL import Image, ImageDraw, ImageFont

from app.extensions import db
from app.models import DownloadFingerprint
from app.models.fingerprint import generate_fingerprint_code

logger = logging.getLogger(__name__)

MAX_FINGERPRINT_PIXELS = 40_000_000


def _load_font(size):
    for name in ('arial.ttf', 'DejaVuSans.ttf'):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _ascii(value, fallback):
    text = str(value or '')
    return text if text.isascii() else fallback


def _draw_footer(image, lines):
    width, height = image.size
    padding = max(6, width // 200)
    font_size = max(10, min(28, width // 70))

    while font_size >= 8:
        font = _load_font(font_size)
        widths = [
            ImageDraw.Draw(image).textbbox((0, 0), line, font=font)[2]
            for line in lines
        ]
        if max(widths) <= width - padding * 2:
            break
        font_size -= 2

    font = _load_font(font_size)
    metric = ImageDraw.Draw(image).textbbox((0, 0), 'Ag', font=font)
    line_height = metric[3] - metric[1] + max(2, font_size // 3)
    footer_height = line_height * len(lines) + padding * 2
    footer_height = max(24, footer_height)

    canvas = Image.new('RGB', (width, height + footer_height), (0, 0, 0))
    canvas.paste(image.convert('RGB'), (0, 0))
    overlay = Image.new('RGBA', canvas.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    draw.rectangle([0, height, width, height + footer_height], fill=(0, 0, 0, 200))
    y = height + padding
    for line in lines:
        draw.text((padding, y), line, font=font, fill=(255, 255, 255, 235))
        y += line_height
    return Image.alpha_composite(canvas.convert('RGBA'), overlay).convert('RGB')


def get_or_create_fingerprint(asset, license_row, user):
    """返回 (DownloadFingerprint, created)；不支持/失败时返回 (None, False)。"""
    if not asset or not license_row or not user:
        return None, False
    if asset.asset_type != 'image':
        return None, False

    existing = DownloadFingerprint.query.filter_by(
        license_id=license_row.id, asset_id=asset.id
    ).first()
    source = asset.watermarked_path or asset.storage_path
    if existing and existing.file_path and os.path.isfile(existing.file_path):
        return existing, False

    if not source or not os.path.isfile(source):
        return None, False

    try:
        with Image.open(source) as source_image:
            width, height = source_image.size
            if width * height > MAX_FINGERPRINT_PIXELS:
                return None, False
            image = source_image.convert('RGB')
    except Exception:
        logger.warning('读取下载指纹源图失败', exc_info=True)
        return None, False

    code = existing.fingerprint_code if existing else generate_fingerprint_code()
    username = _ascii(
        user.nickname or user.username, f'user{user.id}'
    )
    lines = [
        f'{_ascii(asset.asset_code, "ASSET")}  |  {_ascii(license_row.license_code, "LICENSE")}',
        f'{username}  |  {code}',
    ]
    try:
        output = _draw_footer(image, lines)
    except Exception:
        logger.warning('绘制下载指纹页脚失败', exc_info=True)
        return None, False

    root = os.path.abspath(current_app.config.get('UPLOAD_FOLDER', './uploads'))
    folder = os.path.join(root, 'fingerprints', str(asset.id))
    os.makedirs(folder, exist_ok=True)
    ext = '.jpg' if (asset.file_format or '').lower() in ('jpg', 'jpeg') else '.png'
    path = os.path.join(folder, f'{code}{ext}')
    try:
        if ext == '.jpg':
            output.save(path, 'JPEG', quality=92)
        else:
            output.save(path, 'PNG')
    except Exception:
        logger.warning('保存下载指纹文件失败', exc_info=True)
        return None, False

    if existing:
        record = existing
    else:
        record = DownloadFingerprint(
            fingerprint_code=code,
            asset_id=asset.id,
            license_id=license_row.id,
            user_id=user.id,
            file_path=path,
        )
        db.session.add(record)

    record.file_path = path
    record.file_hash = _hash_file(path)
    record.file_size = os.path.getsize(path)
    db.session.flush()
    return record, True


def _hash_file(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()
