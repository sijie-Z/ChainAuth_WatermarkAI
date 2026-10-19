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

# 水印 ID 固定占 48 字节（384 bit），不足补零；重复 3 份做多数表决
ID_FIELD_BYTES = 48
ID_BITS = ID_FIELD_BYTES * 8
ID_REPEAT = 5
ID_TOTAL_BITS = ID_BITS * ID_REPEAT
DEFAULT_ALPHA = 32.0
# 低频系数在 JPEG 量化表中步长更小，鲁棒性更好
EMBED_POSITIONS = [(1, 1), (1, 2), (2, 1)]


def id_to_bits(watermark_id):
    """把水印 ID 编码为固定长度的比特序列（重复 3 份）"""
    payload = watermark_id.encode('utf-8')[:ID_FIELD_BYTES].ljust(ID_FIELD_BYTES, b'\x00')
    bits = []
    for byte in payload:
        for shift in range(7, -1, -1):
            bits.append((byte >> shift) & 1)
    return bits * ID_REPEAT


def bits_to_id(bits):
    """从重复编码的比特序列还原水印 ID（多数表决）"""
    if len(bits) < ID_TOTAL_BITS:
        return None

    voted = []
    for i in range(ID_BITS):
        ones = sum(bits[i + k * ID_BITS] for k in range(ID_REPEAT))
        voted.append(1 if ones > ID_REPEAT // 2 else 0)

    payload = bytearray()
    for i in range(0, ID_BITS, 8):
        byte = 0
        for bit in voted[i:i + 8]:
            byte = (byte << 1) | int(bit)
        payload.append(byte)

    try:
        return payload.rstrip(b'\x00').decode('utf-8')
    except UnicodeDecodeError:
        return None


def payload_geometry(height, width):
    """
    根据图像尺寸计算可嵌入的水印边长。

    DCT 每 8x8 块使用 3 个中频系数，容量为块数 * 3；
    其中前 ID_BITS 位固定留给水印 ID，剩余容量给水印图像。
    """
    usable_height = ((height + 7) // 8) * 8
    usable_width = ((width + 7) // 8) * 8
    capacity = (usable_height // 8) * (usable_width // 8) * 3
    available = capacity - ID_TOTAL_BITS

    if available < 64:
        raise ValueError('图像尺寸过小，无法嵌入水印')

    side = max(8, min(int(np.sqrt(available)), 128))
    return side, capacity


def build_payload(watermark_path, height, width, watermark_id):
    """构建待嵌入比特：水印 ID + 缩放后的水印图像"""
    side, _ = payload_geometry(height, width)
    watermark_image = Image.open(watermark_path).convert('L').resize(
        (side, side), Image.LANCZOS
    )
    watermark_bits = watermark_to_bits(np.array(watermark_image))
    return id_to_bits(watermark_id) + watermark_bits, side


def generate_watermark_id(garden_code, asset_type_code='IMG'):
    """生成水印ID"""
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    checksum = uuid.uuid4().hex[:4].upper()
    return f"{garden_code}-{asset_type_code}-{timestamp}-{checksum}"


def dct_embed(image_array, watermark_bits, alpha=DEFAULT_ALPHA):
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

    # 获取图像尺寸；不足 8 的倍数时反射填充，嵌入后再裁回原尺寸
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

    # 嵌入位置（低频中频系数）
    embed_positions = EMBED_POSITIONS

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

            # QIM 量化索引调制：把系数量化到奇/偶格点，JPEG 压缩后仍可按奇偶判定
            for pos in embed_positions:
                if watermark_idx >= len(watermark_bits):
                    break
                x, y = pos
                value = dct_block[x, y]
                q = int(np.floor(value / alpha + 0.5))
                bit = int(watermark_bits[watermark_idx])
                if (q % 2) != bit:
                    q += 1
                dct_block[x, y] = q * alpha
                watermark_idx += 1

            # IDCT变换
            result[i:i+block_size, j:j+block_size] = cv2.idct(dct_block)

    return result[:original_height, :original_width]


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


def embed_raster_watermark(image_path, watermark_path, output_folder, method='dct', garden_code='GEN', alpha=DEFAULT_ALPHA):
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

    height, width = image_array.shape[:2]
    watermark_bits, watermark_side = build_payload(
        watermark_path, height, width, watermark_id
    )

    logger.info(f"水印边长: {watermark_side}, 总比特数: {len(watermark_bits)}")

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


def embed_raster_watermark_color(image_path, watermark_path, output_folder, method='dct', garden_code='GEN', alpha=DEFAULT_ALPHA):
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

    # 读取图像，统一为 RGB 三通道，保留原始颜色
    original_image = Image.open(image_path).convert('RGB')
    image_array = np.array(original_image)
    height, width = image_array.shape[:2]

    watermark_bits, watermark_side = build_payload(
        watermark_path, height, width, watermark_id
    )

    logger.info(f"水印边长: {watermark_side}, 总比特数: {len(watermark_bits)}")

    # 对每个通道嵌入相同的水印
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