"""
栅格水印算法 - 提取模块
基于DCT域的栅格图像水印提取算法
"""
import os
import logging
import numpy as np
from PIL import Image
import cv2


logger = logging.getLogger(__name__)


def dct_extract(image_array, watermark_length, alpha=0.1):
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
    height, width = image_array.shape[:2]
    height = height // block_size * block_size
    width = width // block_size * block_size
    image_array = image_array[:height, :width]

    # 嵌入位置
    embed_positions = [(3, 3), (4, 4), (5, 5)]

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

                # 判断水印值
                if dct_block[x, y] > 0:
                    watermark_bits.append(1)
                else:
                    watermark_bits.append(0)
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


def extract_raster_watermark(watermarked_path, original_watermark_path, output_folder, method='dct'):
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

    # 读取含水印图像
    watermarked_image = Image.open(watermarked_path)
    if watermarked_image.mode != 'L':
        image_array = np.array(watermarked_image.convert('L'))
    else:
        image_array = np.array(watermarked_image)

    # 读取原始水印获取尺寸
    original_watermark = np.array(Image.open(original_watermark_path).convert('L'))
    watermark_shape = original_watermark.shape
    watermark_length = watermark_shape[0] * watermark_shape[1]

    logger.info(f"水印尺寸: {watermark_shape}, 长度: {watermark_length}")

    # 提取水印
    if method == 'dct':
        watermark_bits = dct_extract(image_array, watermark_length)
    else:
        watermark_bits = lsb_extract(image_array, watermark_length)

    # 转换为图像
    extracted_watermark = bits_to_watermark(watermark_bits, watermark_shape)

    # 计算NC值
    from algorithm.utils.nc import NC
    original_binary = (original_watermark > 127).astype(np.uint8)
    extracted_binary = (extracted_watermark > 127).astype(np.uint8)
    nc_value = NC(original_binary, extracted_binary)

    logger.info(f"NC值: {nc_value:.4f}")

    # 保存结果
    os.makedirs(output_folder, exist_ok=True)

    base_name = os.path.splitext(os.path.basename(watermarked_path))[0]
    output_filename = f"{base_name}_extracted.png"
    output_path = os.path.join(output_folder, output_filename)

    Image.fromarray(extracted_watermark).save(output_path)
    logger.info(f"水印提取完成, 输出: {output_path}")

    return {
        'extracted_watermark_path': output_path,
        'nc_value': nc_value,
        'watermark_shape': watermark_shape,
        'method': method
    }