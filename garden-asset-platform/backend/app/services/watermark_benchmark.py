"""水印鲁棒性实验服务

在用户上传的图片上真实执行「嵌入 → 攻击 → 提取」，返回 PSNR、NC 与
水印 ID 恢复情况。实验只使用临时目录，结束后立即清理，不写入资产库。
指标来自实际算法输出，不做任何估算或伪造。
"""
import base64
import io
import logging
import math
import os
import shutil
import tempfile
import time

from flask import current_app

logger = logging.getLogger(__name__)

# 攻击清单：JPEG 压缩、高斯噪声、缩放与组合攻击。
# 顺序固定，前端据此展示；每项都在独立临时文件中执行。
ATTACK_SPECS = (
    {
        'id': 'origin',
        'label': '无攻击',
        'description': '直接提取嵌入后的原图，作为基准',
        'kind': 'copy',
    },
    {
        'id': 'jpeg90',
        'label': 'JPEG 质量 90',
        'description': '轻微有损压缩，模拟常见二次保存',
        'kind': 'jpeg',
        'quality': 90,
    },
    {
        'id': 'jpeg70',
        'label': 'JPEG 质量 70',
        'description': '中等压缩，模拟社交平台转发',
        'kind': 'jpeg',
        'quality': 70,
    },
    {
        'id': 'jpeg50',
        'label': 'JPEG 质量 50',
        'description': '较强压缩，检验频域嵌入的生存能力',
        'kind': 'jpeg',
        'quality': 50,
    },
    {
        'id': 'noise',
        'label': '高斯噪声',
        'description': 'σ = 3.0 的像素噪声',
        'kind': 'noise',
        'sigma': 3.0,
    },
    {
        'id': 'scale50',
        'label': '缩小到 50%',
        'description': '常见缩略图尺寸，提取端尝试自动恢复缩放',
        'kind': 'resize',
        'factor': 0.5,
    },
    {
        'id': 'scale150',
        'label': '放大到 150%',
        'description': '常见展示放大，检验缩放恢复',
        'kind': 'resize',
        'factor': 1.5,
    },
    {
        'id': 'jpeg50_scale75',
        'label': '缩放 75% + JPEG 50',
        'description': '组合攻击，模拟压缩后再缩放分发',
        'kind': 'resize_jpeg',
        'factor': 0.75,
        'quality': 50,
    },
)

ALLOWED_IMAGE_EXTS = {'.png', '.jpg', '.jpeg', '.bmp', '.tif', '.tiff', '.webp'}
NOISE_SEED = 20261023


def _normalize_image(image_path, target_path, max_side):
    """统一为 RGB/L、限制工作尺寸并保存为 PNG，保证攻击结果可复现。"""
    from PIL import Image

    with Image.open(image_path) as source:
        if source.width * source.height > 60_000_000:
            raise ValueError('图片像素过大，请缩小后重试')
        source.load()
        original_size = source.size
        original_mode = source.mode

        if source.mode == 'L':
            image = source.copy()
        else:
            # 透明图先垫白底，避免 alpha 通道干扰压缩/噪声攻击
            rgba = source.convert('RGBA')
            background = Image.new('RGB', rgba.size, (255, 255, 255))
            background.paste(rgba, mask=rgba.getchannel('A'))
            image = background

        downscaled = False
        longest = max(image.size)
        if longest > max_side:
            ratio = max_side / float(longest)
            size = (
                max(8, int(round(image.width * ratio))),
                max(8, int(round(image.height * ratio))),
            )
            image = image.resize(size, Image.LANCZOS)
            downscaled = True

        image.save(target_path, 'PNG')

    return {
        'original_width': original_size[0],
        'original_height': original_size[1],
        'original_mode': original_mode,
        'working_width': image.width,
        'working_height': image.height,
        'downscaled': downscaled,
        'max_side': max_side,
    }


def _apply_attack(source_path, output_path, spec):
    """把一种攻击施加到嵌入后的图片，并写入 output_path。"""
    import numpy as np
    from PIL import Image

    kind = spec['kind']
    if kind == 'copy':
        shutil.copyfile(source_path, output_path)
        return

    with Image.open(source_path) as source:
        image = source.copy()

        if kind in ('jpeg', 'resize_jpeg'):
            if image.mode not in ('RGB', 'L'):
                image = image.convert('RGB')

        if kind in ('resize', 'resize_jpeg'):
            factor = spec['factor']
            size = (
                max(8, int(round(image.width * factor))),
                max(8, int(round(image.height * factor))),
            )
            image = image.resize(size, Image.LANCZOS)

        if kind == 'noise':
            array = np.asarray(image).astype(np.float32)
            rng = np.random.default_rng(NOISE_SEED)
            noisy = array + rng.normal(0, spec['sigma'], array.shape)
            image = Image.fromarray(
                np.clip(noisy, 0, 255).astype(np.uint8), image.mode
            )

        if kind in ('jpeg', 'resize_jpeg'):
            image.save(output_path, 'JPEG', quality=spec['quality'])
        else:
            image.save(output_path, 'PNG')


def _preview_data_uri(path, size=96):
    """把提取出的水印图转成小尺寸 data URI，供前端直接展示。"""
    from PIL import Image

    with Image.open(path) as image:
        preview = image.convert('L').resize((size, size), Image.NEAREST)
        buffer = io.BytesIO()
        preview.save(buffer, 'PNG')
    return 'data:image/png;base64,' + base64.b64encode(buffer.getvalue()).decode('ascii')


def _attack_suffix(spec):
    return '.jpg' if spec['kind'] in ('jpeg', 'resize_jpeg') else '.png'


def run_benchmark(image_path, watermark_path=None, max_side=640):
    """执行一次完整的鲁棒性实验。

    Args:
        image_path: 用户上传的原始图片
        watermark_path: 水印图路径，缺省使用平台默认水印
        max_side: 工作图片最长边，控制单次实验的 CPU 时间

    Returns:
        可直接 JSON 序列化的实验结果

    Raises:
        ValueError: 图片格式/尺寸不受支持等可向用户说明的问题
    """
    from algorithm.raster.embed import (
        DEFAULT_ALPHA,
        ID_BITS,
        embed_raster_watermark,
        embed_raster_watermark_color,
        payload_geometry,
    )
    from algorithm.raster.extract import extract_raster_watermark
    from app.services.watermark_service import WatermarkService

    if not os.path.exists(image_path):
        raise ValueError('图片文件不存在')

    try:
        max_side = max(128, min(int(max_side), 1600))
    except (TypeError, ValueError):
        max_side = 640

    upload_root = os.path.abspath(
        os.path.join(current_app.config.get('UPLOAD_FOLDER', './uploads'), 'benchmark_tmp')
    )
    os.makedirs(upload_root, exist_ok=True)
    workdir = tempfile.mkdtemp(prefix='bench_', dir=upload_root)

    started = time.perf_counter()
    try:
        source_path = os.path.join(workdir, 'source.png')
        try:
            source_meta = _normalize_image(image_path, source_path, max_side)
        except Exception as exc:
            logger.warning('无法解析水印实验图片: %s', exc)
            if isinstance(exc, ValueError) and '像素过大' in str(exc):
                raise
            raise ValueError('图片无法解析，请更换 PNG/JPG/WebP 文件') from exc
        source_meta['upload_kb'] = round(os.path.getsize(image_path) / 1024.0, 1)

        watermark_path = watermark_path or WatermarkService.get_watermark_path()
        if not os.path.exists(watermark_path):
            raise ValueError('平台水印图缺失，无法执行实验')

        embedded_dir = os.path.join(workdir, 'embedded')
        os.makedirs(embedded_dir, exist_ok=True)

        embed_started = time.perf_counter()
        if source_meta['original_mode'] == 'L':
            embed_result = embed_raster_watermark(
                image_path=source_path,
                watermark_path=watermark_path,
                output_folder=embedded_dir,
                method='dct',
                garden_code='LAB',
            )
        else:
            embed_result = embed_raster_watermark_color(
                image_path=source_path,
                watermark_path=watermark_path,
                output_folder=embedded_dir,
                method='dct',
                garden_code='LAB',
            )
        embed_ms = int(round((time.perf_counter() - embed_started) * 1000))

        watermarked_path = embed_result['watermarked_path']
        watermark_id = embed_result['watermark_id']
        id_repeat = embed_result.get('id_repeat') or 1
        side, capacity = payload_geometry(
            source_meta['working_height'],
            source_meta['working_width'],
            ID_BITS * id_repeat,
        )

        extracted_dir = os.path.join(workdir, 'extracted')
        os.makedirs(extracted_dir, exist_ok=True)

        attacks = []
        for spec in ATTACK_SPECS:
            attack_path = os.path.join(
                workdir, f"attack_{spec['id']}{_attack_suffix(spec)}"
            )
            attack_started = time.perf_counter()
            entry = {
                'id': spec['id'],
                'label': spec['label'],
                'description': spec['description'],
                'id_recovered': False,
                'recovered_id': None,
                'nc': 0.0,
                'extract_ms': 0,
                'watermark_preview': None,
                'error': None,
            }
            try:
                _apply_attack(watermarked_path, attack_path, spec)
                extract_started = time.perf_counter()
                extract_result = extract_raster_watermark(
                    watermarked_path=attack_path,
                    original_watermark_path=watermark_path,
                    output_folder=extracted_dir,
                )
                entry['extract_ms'] = int(
                    round((time.perf_counter() - extract_started) * 1000)
                )
                recovered_id = extract_result.get('watermark_id')
                entry['recovered_id'] = recovered_id
                entry['id_recovered'] = recovered_id == watermark_id
                entry['nc'] = round(float(extract_result.get('nc_value') or 0.0), 4)

                extracted_path = extract_result.get('extracted_watermark_path')
                if extracted_path and os.path.exists(extracted_path):
                    entry['watermark_preview'] = _preview_data_uri(extracted_path)
            except Exception:
                logger.exception(
                    '鲁棒性实验攻击失败: %s (%s)', spec['id'], watermark_id
                )
                entry['error'] = '该攻击下提取失败'
            entry['total_ms'] = int(round((time.perf_counter() - attack_started) * 1000))
            attacks.append(entry)

        recovered = sum(1 for item in attacks if item['id_recovered'])
        nc_values = [item['nc'] for item in attacks]
        if recovered == len(attacks):
            verdict = '全部攻击下均可恢复水印 ID'
        elif recovered == 0:
            verdict = '所有攻击下均未恢复水印 ID'
        elif recovered >= max(1, math.ceil(len(attacks) * 0.6)):
            verdict = '多数攻击下可恢复水印 ID'
        else:
            verdict = '部分攻击下水印 ID 已失效'

        logger.info(
            '鲁棒性实验完成: id=%s, %s/%s 恢复, psnr=%.2f',
            watermark_id, recovered, len(attacks), embed_result.get('psnr') or 0,
        )

        return {
            'watermark_id': watermark_id,
            'psnr': round(float(embed_result.get('psnr') or 0.0), 2),
            'alpha': DEFAULT_ALPHA,
            'method': 'DCT + QIM',
            'source': source_meta,
            'watermark': {
                'id_repeat': id_repeat,
                'side': side,
                'capacity_bits': capacity,
                'id_bits': ID_BITS,
            },
            'embed_ms': embed_ms,
            'total_ms': int(round((time.perf_counter() - started) * 1000)),
            'attacks': attacks,
            'summary': {
                'total': len(attacks),
                'recovered': recovered,
                'success_rate': round(recovered / float(len(attacks)), 4),
                'min_nc': round(min(nc_values), 4) if nc_values else 0.0,
                'verdict': verdict,
            },
            'watermark_preview': _preview_data_uri(watermark_path),
            'disclaimer': (
                '实验只对上传图片的临时副本执行，不写入资产库。'
                '大幅裁剪会破坏嵌入区域，需要结合存证与人工核验。'
            ),
        }
    finally:
        shutil.rmtree(workdir, ignore_errors=True)
