"""
栅格图像读取工具：统一处理 16 位 / 浮点 / 调色板等格式，避免 convert('L') 截断。
"""
import numpy as np
from PIL import Image


def load_image_array(image_path, mode='RGB'):
    """读取图像为 uint8 数组。

    - 16 位 / 浮点图像按 min-max 归一化到 0-255（PIL convert 会直接截断成近纯白）。
    - 其余模式交给 PIL 转换（P/CMYK/LA 转 RGB/L）。
    """
    image = Image.open(image_path)
    source_mode = image.mode

    if source_mode in ('I', 'I;16', 'I;16B', 'I;16L', 'I;16S', 'F'):
        array = np.asarray(image, dtype=np.float64)
        minimum = float(array.min())
        maximum = float(array.max())
        if maximum > minimum:
            array = (array - minimum) / (maximum - minimum) * 255.0
        else:
            array = np.zeros_like(array)
        array = np.clip(array, 0, 255).astype(np.uint8)
        if mode == 'L':
            return array
        return np.repeat(array[:, :, None], 3, axis=2)

    if mode == 'L':
        return np.array(image.convert('L'))
    return np.array(image.convert('RGB'))


def alpha_channel(image_path):
    """返回 RGBA/LA 图像的 alpha 通道数组；没有 alpha 时返回 None。"""
    image = Image.open(image_path)
    if image.mode not in ('RGBA', 'LA'):
        return None
    return np.array(image.getchannel('A'))
