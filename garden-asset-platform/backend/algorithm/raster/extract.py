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

from algorithm.raster.image_io import load_image_array
from algorithm.raster.embed import (
    DEFAULT_ALPHA,
    EMBED_POSITIONS,
    ID_BITS,
    ID_REPEAT,
    ID_REPEAT_CANDIDATES,
    bits_to_id,
    choose_id_repeat,
    payload_geometry,
)

ID_PATTERN = re.compile(r'^[A-Z]{2,4}-(?:IMG|VEC|MDL|DOC|VID)-\d{14}-[0-9A-F]{4}$')

# 缩放攻击恢复：按常见比例把图像放大/缩小后重新尝试解码 ID
SCALE_CANDIDATES = [2.0, 1.5, 4 / 3, 1.25, 1.2, 1.1, 0.9, 0.8, 0.75, 2 / 3, 0.5]


def _extract_bits(image_array, watermark_length, method='dct', alpha=DEFAULT_ALPHA):
    """2D 图直接提取；彩色图逐通道提取后按位多数表决。

    彩色嵌入时三个通道写入相同比特，但各自的量化格点可能不同，
    单取灰度平均会在格点边界附近产生误码；逐通道表决可消除这类错误。
    """
    if image_array.ndim == 2:
        if method == 'dct':
            return dct_extract(image_array, watermark_length, alpha=alpha)
        return lsb_extract(image_array, watermark_length)

    channel_bits = []
    for channel in range(image_array.shape[2]):
        channel_array = image_array[:, :, channel]
        if method == 'dct':
            channel_bits.append(dct_extract(channel_array, watermark_length, alpha=alpha))
        else:
            channel_bits.append(lsb_extract(channel_array, watermark_length))

    # 小尺寸候选图的 DCT 容量可能不足，按实际可用比特数表决
    length = min((len(bits) for bits in channel_bits), default=0)
    voted = []
    for index in range(length):
        ones = sum(bits[index] for bits in channel_bits)
        voted.append(1 if ones * 2 >= len(channel_bits) else 0)
    return voted


def _detect_id(image_array, alpha=DEFAULT_ALPHA):
    """解码 ID 并返回 (id, 重复份数)；兼容不同重复份数的历史编码。"""
    height, width = image_array.shape[:2]
    try:
        preferred = choose_id_repeat(height, width)
    except ValueError:
        preferred = ID_REPEAT
    # 现行编码的重复份数由图像容量决定，优先尝试；再回退历史 5/8/12 等
    repeats = [preferred] + [
        repeat for repeat in ID_REPEAT_CANDIDATES if repeat != preferred
    ]
    bits = _extract_bits(
        image_array, ID_BITS * max(repeats), 'dct', alpha
    )
    for repeat in repeats:
        watermark_id = bits_to_id(bits[:ID_BITS * repeat], repeat)
        if watermark_id and ID_PATTERN.match(watermark_id):
            return watermark_id, repeat
    return None, None


def _decode_valid_id(image_array, alpha=DEFAULT_ALPHA):
    """只解码 ID 位并用格式校验，避免把随机比特误判为水印 ID"""
    return _detect_id(image_array, alpha)[0]


def _resolve_scaled_image(image, alpha=DEFAULT_ALPHA):
    """ID 解码失败时，尝试常见缩放比例，返回能解出有效 ID 的图像与 ID。

    2.0 倍还额外尝试最近邻插值：图片被精确缩小一半时（缩略图常见），
    最近邻放大能完整还原原像素块，QIM 系数不会被插值平滑破坏。
    """
    base_width, base_height = image.size
    use_color = image.mode in ('RGB', 'RGBA', 'P', 'CMYK', 'LA')
    for factor in SCALE_CANDIDATES:
        size = (max(8, int(base_width * factor)), max(8, int(base_height * factor)))
        resample_options = (Image.LANCZOS, Image.NEAREST) if factor == 2.0 else (Image.LANCZOS,)
        for resample in resample_options:
            candidate = image.resize(size, resample)
            candidate_array = np.array(candidate.convert('RGB' if use_color else 'L'))
            watermark_id = _decode_valid_id(candidate_array, alpha)
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
    use_color = watermarked_image.mode in ('RGB', 'RGBA', 'P', 'CMYK', 'LA')
    image_array = load_image_array(watermarked_path, 'RGB' if use_color else 'L')
    height, width = image_array.shape[:2]

    # 先尝试直接解码 ID；失败则尝试常见缩放比例（缩放攻击恢复）
    id_repeat = ID_REPEAT
    watermark_id = None
    if method == 'dct':
        watermark_id, id_repeat = _detect_id(image_array, alpha)
        if not watermark_id:
            restored_image, _ = _resolve_scaled_image(
                watermarked_image, alpha
            )
            if restored_image is not None:
                image_array = np.array(
                    restored_image.convert('RGB' if use_color else 'L')
                )
                height, width = image_array.shape[:2]
                watermark_id, id_repeat = _detect_id(image_array, alpha)
                id_repeat = id_repeat or ID_REPEAT

    id_total_bits = ID_BITS * (id_repeat or ID_REPEAT)
    try:
        watermark_side, capacity = payload_geometry(
            height, width, id_total_bits
        )
    except ValueError:
        # 极小图片或 ID 未解出时，退到 1 份重复，尽量完成提取
        id_repeat = 1
        id_total_bits = ID_BITS
        watermark_side, capacity = payload_geometry(
            height, width, id_total_bits
        )
    total_bits = id_total_bits + watermark_side * watermark_side

    logger.info(
        f"图像 {width}x{height}, 容量 {capacity} bit, "
        f"水印 {watermark_side}x{watermark_side}, 读取 {total_bits} bit"
    )

    # 提取比特：前 id_total_bits 位是水印 ID，其余是水印图像
    bits = _extract_bits(image_array, total_bits, method, alpha)

    watermark_id = watermark_id or bits_to_id(
        bits[:id_total_bits], id_repeat or ID_REPEAT
    )
    extracted_watermark = bits_to_watermark(
        bits[id_total_bits:id_total_bits + watermark_side * watermark_side],
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