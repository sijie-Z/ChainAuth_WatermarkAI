"""
栅格水印算法 - 嵌入模块
基于DCT域的栅格图像水印嵌入算法
"""
import os
import logging
from datetime import datetime
import uuid
import numpy as np
from PIL import Image
import cv2


logger = logging.getLogger(__name__)


def generate_watermark_id(garden_code, asset_type_code='IMG'):
    """生成水印ID"""
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    checksum = uuid.uuid4().hex[:4].upper()
    return f"{garden_code}-{asset_type_code}-{timestamp}-{checksum}"


def dct_embed(image_array, watermark_bits, alpha=0.1):
    """
    DCT域水印嵌入

    Args:
        image_array: 图像数组
        watermark_bits: 水印比特序列
        alpha: 嵌入强度

    Returns:
        嵌入水印后的图像数组
    """
    # 分块大小
    block_size = 8

    # 获取图像尺寸
    height, width = image_array.shape[:2]

    # 确保图像尺寸是block_size的整数倍
    height = height // block_size * block_size
    width = width // block_size * block_size
    image_array = image_array[:height, :width]

    # 嵌入位置 (中频系数)
    embed_positions = [(3, 3), (4, 4), (5, 5)]

    # 水印索引
    watermark_idx = 0

    result = image_array.copy()

    # 对每个8x8块进行DCT变换并嵌入水印
    for i in range(0, height, block_size):
        for j in range(0, width, block_size):
            if watermark_idx >= len(watermark_bits):
                break

            block = image_array[i:i+block_size, j:j+block_size]

            # DCT变换
            dct_block = cv2.dct(block.astype(np.float32))

            # 嵌入水印
            for pos in embed_positions:
                if watermark_idx >= len(watermark_bits):
                    break
                x, y = pos
                if watermark_bits[watermark_idx] == 1:
                    dct_block[x, y] += alpha
                else:
                    dct_block[x, y] -= alpha
                watermark_idx += 1

            # IDCT变换
            result[i:i+block_size, j:j+block_size] = cv2.idct(dct_block)

    return result


def lsb_embed(image_array, watermark_bits):
    """
    LSB水印嵌入（简单版本）

    Args:
        image_array: 图像数组
        watermark_bits: 水印比特序列

    Returns:
        嵌入水印后的图像数组
    """
    result = image_array.copy()
    watermark_idx = 0

    # 在像素的最低位嵌入水印
    for i in range(result.shape[0]):
        for j in range(result.shape[1]):
            if watermark_idx >= len(watermark_bits):
                break

            # 获取像素值
            pixel = result[i, j]

            # 修改最低位
            if watermark_bits[watermark_idx] == 1:
                pixel = pixel | 1  # 设置最低位为1
            else:
                pixel = pixel & 0xFE  # 设置最低位为0

            result[i, j] = pixel
            watermark_idx += 1

        if watermark_idx >= len(watermark_bits):
            break

    return result


def watermark_to_bits(watermark_image):
    """
    将水印图像转换为比特序列

    Args:
        watermark_image: 水印图像数组

    Returns:
        水印比特序列
    """
    # 二值化
    binary = (watermark_image > 127).astype(np.uint8)
    return binary.flatten().tolist()


def embed_raster_watermark(image_path, watermark_path, output_folder, method='dct', garden_code='GEN', alpha=0.1):
    """
    栅格图像水印嵌入主函数

    Args:
        image_path: 原始图像路径
        watermark_path: 水印图像路径
        output_folder: 输出文件夹
        method: 嵌入方法 (dct/lsb)
        garden_code: 园林编码
        alpha: 嵌入强度

    Returns:
        嵌入结果字典
    """
    # 生成水印ID
    watermark_id = generate_watermark_id(garden_code, 'IMG')

    logger.info(f"开始栅格水印嵌入, 水印ID: {watermark_id}, 方法: {method}")

    # 读取图像
    original_image = Image.open(image_path)

    # 转换为灰度图像（如果是彩色）
    if original_image.mode != 'L':
        image_array = np.array(original_image.convert('L'))
    else:
        image_array = np.array(original_image)

    # 读取水印
    watermark_image = np.array(Image.open(watermark_path).convert('L'))
    watermark_bits = watermark_to_bits(watermark_image)

    logger.info(f"水印比特数: {len(watermark_bits)}")

    # 嵌入水印
    if method == 'dct':
        watermarked_array = dct_embed(image_array, watermark_bits, alpha)
    else:
        watermarked_array = lsb_embed(image_array, watermark_bits)

    # 计算PSNR
    mse = np.mean((image_array - watermarked_array) ** 2)
    psnr = 20 * np.log10(255.0 / np.sqrt(mse)) if mse > 0 else float('inf')

    logger.info(f"PSNR: {psnr:.2f} dB")

    # 保存结果
    os.makedirs(output_folder, exist_ok=True)

    output_filename = f"{watermark_id}.png"
    output_path = os.path.join(output_folder, output_filename)

    watermarked_image = Image.fromarray(watermarked_array.astype(np.uint8))
    watermarked_image.save(output_path)

    logger.info(f"水印嵌入完成, 输出: {output_path}")

    return {
        'watermarked_path': output_path,
        'watermark_id': watermark_id,
        'method': method,
        'psnr': psnr,
        'watermark_bits_count': len(watermark_bits)
    }


def embed_raster_watermark_color(image_path, watermark_path, output_folder, method='dct', garden_code='GEN', alpha=0.1):
    """
    彩色图像水印嵌入

    Args:
        image_path: 原始图像路径
        watermark_path: 水印图像路径
        output_folder: 输出文件夹
        method: 嵌入方法
        garden_code: 园林编码
        alpha: 嵌入强度

    Returns:
        嵌入结果字典
    """
    watermark_id = generate_watermark_id(garden_code, 'IMG')

    logger.info(f"开始彩色图像水印嵌入, 水印ID: {watermark_id}")

    # 读取图像
    original_image = Image.open(image_path)
    image_array = np.array(original_image)

    # 读取水印
    watermark_image = np.array(Image.open(watermark_path).convert('L'))
    watermark_bits = watermark_to_bits(watermark_image)

    # 对每个通道嵌入水印
    result = image_array.copy()
    psnr_values = []

    for channel in range(image_array.shape[2]):
        if method == 'dct':
            result[:, :, channel] = dct_embed(image_array[:, :, channel], watermark_bits, alpha)
        else:
            result[:, :, channel] = lsb_embed(image_array[:, :, channel], watermark_bits)

        # 计算PSNR
        mse = np.mean((image_array[:, :, channel] - result[:, :, channel]) ** 2)
        psnr = 20 * np.log10(255.0 / np.sqrt(mse)) if mse > 0 else float('inf')
        psnr_values.append(psnr)

    avg_psnr = np.mean(psnr_values)
    logger.info(f"平均PSNR: {avg_psnr:.2f} dB")

    # 保存结果
    os.makedirs(output_folder, exist_ok=True)
    output_filename = f"{watermark_id}.png"
    output_path = os.path.join(output_folder, output_filename)

    watermarked_image = Image.fromarray(result.astype(np.uint8))
    watermarked_image.save(output_path)

    return {
        'watermarked_path': output_path,
        'watermark_id': watermark_id,
        'method': method,
        'psnr': avg_psnr
    }