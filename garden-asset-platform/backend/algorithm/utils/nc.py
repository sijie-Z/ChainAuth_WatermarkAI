"""
工具模块 - NC值计算
"""
import numpy as np
from PIL import Image


def image_to_array(path):
    """
    将图像转换为numpy数组

    Args:
        path: 图像路径

    Returns:
        numpy数组
    """
    image = Image.open(path)
    image_array = np.array(image).astype(int)
    return image_array


def NC(original_watermark, extract_watermark):
    """
    计算归一化相关系数 (Normalized Correlation)

    Args:
        original_watermark: 原始水印
        extract_watermark: 提取的水印

    Returns:
        NC值 (0-1之间，越接近1越相似)
    """
    if original_watermark.shape != extract_watermark.shape:
        raise ValueError('输入图像尺寸不一致！')

    if not (np.all(np.isin(original_watermark, [0, 1])) and np.all(np.isin(extract_watermark, [0, 1]))):
        raise ValueError('输入图像必须是二值图像（0或1）！')

    # 计算相同像素的比率
    same_pixels = (original_watermark.astype(bool) == extract_watermark.astype(bool))
    return np.sum(same_pixels) / original_watermark.size


def calculate_psnr(original, watermarked):
    """
    计算峰值信噪比 (PSNR)

    Args:
        original: 原始图像
        watermarked: 含水印图像

    Returns:
        PSNR值 (dB)
    """
    mse = np.mean((original - watermarked) ** 2)
    if mse == 0:
        return float('inf')

    max_pixel = 255.0
    psnr = 20 * np.log10(max_pixel / np.sqrt(mse))
    return psnr


def calculate_ssim(original, watermarked):
    """
    计算结构相似性指数 (SSIM)
    简化版本

    Args:
        original: 原始图像
        watermarked: 含水印图像

    Returns:
        SSIM值 (0-1之间)
    """
    C1 = (0.01 * 255) ** 2
    C2 = (0.03 * 255) ** 2

    original = original.astype(np.float64)
    watermarked = watermarked.astype(np.float64)

    mu1 = np.mean(original)
    mu2 = np.mean(watermarked)

    sigma1_sq = np.var(original)
    sigma2_sq = np.var(watermarked)
    sigma12 = np.cov(original.flatten(), watermarked.flatten())[0, 1]

    ssim = ((2 * mu1 * mu2 + C1) * (2 * sigma12 + C2)) / \
           ((mu1 ** 2 + mu2 ** 2 + C1) * (sigma1_sq + sigma2_sq + C2))

    return ssim