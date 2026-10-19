"""
栅格水印算法 - 提取模块
基于DCT域的栅格图像水印提取算法
"""
import os
import re
import logging
import numpy as np
from PIL import Image
import cv2

from algorithm.raster.embed import (
    DEFAULT_ALPHA,
    EMBED_POSITIONS,
    ID_TOTAL_BITS,
    bits_to_id,
    payload_geometry,
)

ID_PATTERN = re.compile(r'^[A-Z]{2,4}-(?:IMG|VEC|MDL|DOC|VID)-\d{14}-[0-9A-F]{4}$')

# 缩放攻击恢复：按常见比例把图像放大/缩小后重新尝试解码 ID
SCALE_CANDIDATES = [2.0, 1.5, 4 / 3, 1.25, 1.2, 1.1, 0.9, 0.8, 0.75, 2 / 3, 0.5]


def _decode_valid_id(image_array, alpha=DEFAULT_ALPHA):
    """只解码 ID 位并用格式校验，避免把随机比特误判为水印 ID"""
    bits = dct_extract(image_array, ID_TOTAL_BITS, alpha=alpha)
    watermark_id = bits_to_id(bits)
    if watermark_id and ID_PATTERN.match(watermark_id):
        return watermark_id
    return None


def _resolve_scaled_image(image, alpha=DEFAULT_ALPHA):
    """ID 解码失败时，尝试常见缩放比例，返回能解出有效 ID 的图像与 ID"""
    base_width, base_height = image.size
    for factor in SCALE_CANDIDATES:
        size = (max(8, int(base_width * factor)), max(8, int(base_height * factor)))
        candidate = image.resize(size, Image.LANCZOS)
        watermark_id = _decode_valid_id(np.array(candidate.convert('L')), alpha)
        if watermark_id:
            logger.info(f'检测到缩放攻击，按 {factor:.2f} 倍恢复后解码成功')
            return candidate, watermark_id
    return None, None


logger = logging.getLogger(__name__)


def dct_extract(image_array, watermark_length, alpha=DEFAULT_ALPHA):
    """
    DCT域水印提取

    Args:
        image_array: 含水印的图像数组
        watermark_length: 水印长度
        alpha: 嵌入强度

    Returns:
        提取的水印比特序列
    """
    block_size = 8
    original_height, original_width = image_array.shape[:2]
    height = ((original_height + block_size - 1) // block_size) * block_size
    width = ((original_width + block_size - 1) // block_size) * block_size
    if height != original_height or width != original_width:
        image_array = cv2.copyMakeBorder(
            image_array,
            0, height - original_height,
            0, width - original_width,
            cv2.BORDER_REFLECT_101
        )

    # 与嵌入端一致的低频系数位置
    embed_positions = EMBED_POSITIONS

    watermark_bits = []
    watermark_idx = 0

    for i in range(0, height, block_size):
        for j in range(0, width, block_size):
            if watermark_idx >= watermark_length:
                break

            block = image_array[i:i+block_size, j:j+block_size]
            dct_block = cv2.dct(block.astype(np.float32))

            for pos in embed_positions:
                if watermark_idx >= watermark_length:
                    break
                x, y = pos

                # QIM 解码：最近格点的奇偶性就是水印比特
                q = int(np.floor(dct_block[x, y] / alpha + 0.5))
                watermark_bits.append(q % 2)
                watermark_idx += 1

    return watermark_bits


def lsb_extract(image_array, watermark_length):
    """
    LSB水印提取

    Args:
        image_array: 含水印的图像数组
        watermark_length: 水印长度

    Returns:
        提取的水印比特序列
    """
    watermark_bits = []
    watermark_idx = 0

    for i in range(image_array.shape[0]):
        for j in range(image_array.shape[1]):
            if watermark_idx >= watermark_length:
                break

            # 提取最低位
            bit = image_array[i, j] & 1
            watermark_bits.append(bit)
            watermark_idx += 1

        if watermark_idx >= watermark_length:
            break

    return watermark_bits


def bits_to_watermark(watermark_bits, watermark_shape):
    """
    将比特序列转换为水印图像

    Args:
        watermark_bits: 水印比特序列
        watermark_shape: 水印图像形状

    Returns:
        水印图像数组
    """
    # 确保比特数足够
    required_bits = watermark_shape[0] * watermark_shape[1]
    if len(watermark_bits) < required_bits:
        watermark_bits = watermark_bits + [0] * (required_bits - len(watermark_bits))
    else:
        watermark_bits = watermark_bits[:required_bits]

    # 重构水印图像
    watermark_array = np.array(watermark_bits).reshape(watermark_shape)
    watermark_array = (watermark_array * 255).astype(np.uint8)

    return watermark_array


def extract_raster_watermark(watermarked_path, original_watermark_path, output_folder, method='dct', alpha=DEFAULT_ALPHA):
    """
    栅格图像水印提取主函数

    Args:
        watermarked_path: 含水印图像路径
        original_watermark_path: 原始水印路径（用于确定水印尺寸）
        output_folder: 输出文件夹
        method: 提取方法 (dct/lsb)

    Returns:
        提取结果字典
    """
    logger.info(f"开始栅格水印提取, 方法: {method}")

    # 读取原始水印用于计算 NC（按实际嵌入尺寸缩放）
    watermarked_image = Image.open(watermarked_path)
    image_array = np.array(watermarked_image.convert('L'))
    height, width = image_array.shape[:2]

    # 先尝试直接解码 ID；失败则尝试常见缩放比例（缩放攻击恢复）
    watermark_id = _decode_valid_id(image_array, alpha) if method == 'dct' else None
    if method == 'dct' and not watermark_id:
        restored_image, restored_id = _resolve_scaled_image(watermarked_image, alpha)
        if restored_image is not None:
            watermarked_image = restored_image
            image_array = np.array(restored_image.convert('L'))
            height, width = image_array.shape[:2]
            watermark_id = restored_id

    watermark_side, capacity = payload_geometry(height, width)
    total_bits = ID_TOTAL_BITS + watermark_side * watermark_side

    logger.info(
        f"图像 {width}x{height}, 容量 {capacity} bit, "
        f"水印 {watermark_side}x{watermark_side}, 读取 {total_bits} bit"
    )

    # 提取比特：前 ID_BITS 位是水印 ID，其余是水印图像
    if method == 'dct':
        bits = dct_extract(image_array, total_bits, alpha=alpha)
    else:
        bits = lsb_extract(image_array, total_bits)

    watermark_id = watermark_id or bits_to_id(bits[:ID_TOTAL_BITS])
    extracted_watermark = bits_to_watermark(
        bits[ID_TOTAL_BITS:ID_TOTAL_BITS + watermark_side * watermark_side],
        (watermark_side, watermark_side)
    )

    # 计算 NC 值
    from algorithm.utils.nc import NC
    original_watermark = np.array(
        Image.open(original_watermark_path).convert('L').resize(
            (watermark_side, watermark_side), Image.LANCZOS
        )
    )
    original_binary = (original_watermark > 127).astype(np.uint8)
    extracted_binary = (extracted_watermark > 127).astype(np.uint8)
    nc_value = NC(original_binary, extracted_binary)

    logger.info(f"NC值: {nc_value:.4f}, 水印ID: {watermark_id}")

    # 保存结果
    os.makedirs(output_folder, exist_ok=True)

    base_name = os.path.splitext(os.path.basename(watermarked_path))[0]
    output_filename = f"{base_name}_extracted.png"
    output_path = os.path.join(output_folder, output_filename)

    Image.fromarray(extracted_watermark).save(output_path)
    logger.info(f"水印提取完成, 输出: {output_path}")

    return {
        'watermark_id': watermark_id,
        'extracted_watermark_path': output_path,
        'nc_value': nc_value,
        'watermark_shape': (watermark_side, watermark_side),
        'method': method
    }