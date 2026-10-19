"""
矢量水印算法 - 提取模块
基于坐标扰动的矢量数据水印提取算法
"""
import os
import math
import random
import logging
from decimal import Decimal
from collections import Counter
from datetime import datetime
import numpy as np
from PIL import Image
import geopandas as gpd

from algorithm.utils.get_coor import get_coor_nested, get_coor_array
from algorithm.utils.to_geodataframe import to_geodataframe
from algorithm.utils.nc import NC


logger = logging.getLogger(__name__)


def watermark_extract(coor, coor_l, R, n):
    """
    从坐标中提取水印

    Args:
        coor: 嵌入水印后的坐标
        coor_l: 区域左下角顶点的坐标
        R: 区域大小
        n: 嵌入强度

    Returns:
        (原始坐标, 水印值)
    """
    x, y = coor
    xl, yl = coor_l
    w = (x - xl) // (R / 2 ** n)
    original_x = xl + 2 ** n * (x - xl) - w * R
    original_y = y
    return np.vstack([original_x, original_y]), int(w)


def coor_process(coor, W, dis, argument):
    """
    对坐标进行处理

    Args:
        coor: 需要处理的坐标
        W: 水印收集数组
        dis: 用于随机种子生成的距离值
        argument: 算法参数字典

    Returns:
        (原始坐标, 更新后的W)
    """
    n, R, side_length, ratio = argument.values()
    random.seed(dis)

    index = random.randint(0, len(W) - 1)
    coor = np.array([Decimal(str(x)) for x in coor])
    coor_l = coor // R * R
    original_coor, w = watermark_extract(coor, coor_l, R, n)
    W[index].append(w)
    return original_coor, W


def coor_group_process(coor_group, W, argument):
    """
    对坐标组进行处理

    Args:
        coor_group: 需要处理的坐标组
        W: 水印收集数组
        argument: 算法参数字典

    Returns:
        (原始坐标组, 更新后的W)
    """
    n, R, side_length, ratio = argument.values()
    coor_group = coor_group * ratio
    original_coor_group = np.array([[], []])

    for i in range(coor_group.shape[1]):
        coor = coor_group[:, i]
        if i == coor_group.shape[1] - 1:
            original_coor = coor[:, np.newaxis]
        else:
            dis = abs(coor[1] - coor_group[:, i + 1][1])
            original_coor, W = coor_process(coor, W, dis, argument)
        original_coor_group = np.concatenate((original_coor_group, original_coor), axis=1)

    return original_coor_group, W


def traversal_nested_coor_group(coor_nested, feature_type, W, argument):
    """
    对于多线、多面等情况，执行此函数
    """
    processed_x_nested = []
    processed_y_nested = []

    for feature_index in range(coor_nested.shape[1]):
        coor_group = np.vstack(coor_nested[:, feature_index])
        processed_coor_group, W = coor_group_process(coor_group, W, argument)

        if (feature_type == 'MultiPolygon'
                and np.size(processed_coor_group) not in [0, 2]
                and not np.array_equal(processed_coor_group[:, 0], processed_coor_group[:, -1])):
            processed_coor_group[:, -1] = processed_coor_group[:, 0]

        processed_x_nested.append(processed_coor_group[0, :])
        processed_y_nested.append(processed_coor_group[1, :])

    return np.array([processed_x_nested, processed_y_nested], dtype=object), W


def traversal_coor_group(coor_nested, shp_type, processed_shpfile, l, argument):
    """
    对所有要素进行遍历
    """
    W = [[] for _ in range(l)]

    for feature_index in range(coor_nested.shape[1]):
        coor_group = np.vstack(coor_nested[:, feature_index])
        if isinstance(coor_nested[:, feature_index][0], list):
            continue

        feature_type = shp_type[feature_index]

        if isinstance(coor_group[0, 0], np.ndarray):
            processed_coor_group, W = traversal_nested_coor_group(coor_group, feature_type, W, argument)
        else:
            processed_coor_group, W = coor_group_process(coor_group, W, argument)
            if (feature_type == 'Polygon'
                    and np.size(processed_coor_group) not in [0, 2]
                    and not np.array_equal(processed_coor_group[:, 0], processed_coor_group[:, -1])):
                processed_coor_group[:, -1] = processed_coor_group[:, 0]

        processed_shpfile = to_geodataframe(processed_shpfile, feature_index, processed_coor_group,
                                             shp_type[feature_index])

    return processed_shpfile, W


def calculate_watermark_and_nc(watermarked_shpfile, l, argument):
    """
    计算提取的水印
    """
    watermarked_coor_nested, feature_type = get_coor_nested(watermarked_shpfile)
    n, R, side_length, ratio = argument.values()

    original_shpfile = watermarked_shpfile.copy()
    original_shpfile, W = traversal_coor_group(watermarked_coor_nested, feature_type, original_shpfile, l,
                                               argument)

    # 统计每个数字的出现次数
    empty_array_flag = False
    for i in range(len(W)):
        counter = Counter(W[i])
        if counter:
            w = counter.most_common(1)[0][0]
            w = 0 if w < 0 else w
            W[i] = [int(digit) for digit in format(w, f"0{n}b")]
        else:
            empty_array_flag = True
            W[i] = [0] * n

    if empty_array_flag:
        logger.warning('存在空数组，补零')

    W = [item for w in W for item in w]
    W = W[:side_length ** 2 - 192]

    # 重构水印图像
    watermark = np.full((side_length, side_length), 1)
    detection_pattern = np.full((7, 7), 0)
    detection_pattern[1:6, 1:6] = np.full((5, 5), 1)
    detection_pattern[2:5, 2:5] = np.full((3, 3), 0)
    watermark[:7, :7] = watermark[:7, -7:] = watermark[-7:, :7] = detection_pattern
    watermark[0:8, 8: -8] = np.reshape(W[0:(side_length - 16) * 8], (8, side_length - 16))
    watermark[8:-8, :] = np.reshape(W[(side_length - 16) * 8:-(side_length - 8) * 8], (side_length - 16, side_length))
    watermark[-8:, 8:] = np.reshape(W[-(side_length - 8) * 8:], (8, side_length - 8))

    return original_shpfile, watermark


def extract_vector_watermark(watermarked_shpfile_path, vr, output_folder):
    """
    矢量数据水印提取主函数

    Args:
        watermarked_shpfile_path: 含水印的矢量数据路径
        vr: 嵌入时生成的验证值
        output_folder: 输出文件夹

    Returns:
        提取结果字典
    """
    # 算法参数
    n = 4
    tau = 10 ** (-6)
    side_length = 45
    l = math.ceil((side_length ** 2 - 192) / n)
    R = Decimal('1e-7')

    logger.info(f"开始提取水印")

    # 数据读取
    watermarked_shpfile = gpd.read_file(watermarked_shpfile_path)

    # 嵌入时写入的属性列可直接用于溯源（DBF 字段名上限 10 字符）
    watermark_id = None
    if 'wm_id' in watermarked_shpfile.columns and len(watermarked_shpfile) > 0:
        watermark_id = str(watermarked_shpfile['wm_id'].iloc[0])

    # 数据预处理
    watermarked_coor_nested, feature_type = get_coor_nested(watermarked_shpfile)
    coor_array = get_coor_array(watermarked_coor_nested, feature_type)
    coor_mean = np.mean(coor_array, axis=1)

    logger.info(f"坐标均值: {coor_mean}, 验证值: {vr}")

    # 溯源场景没有 vr，按未缩放处理（ratio=1），仍可恢复水印图像
    if vr is None:
        vr = coor_mean

    ratio = np.mean(vr / coor_mean)
    logger.info(f"缩放比例: {ratio}")

    argument = {'n': n, 'R': R, 'side_length': side_length, 'ratio': ratio}

    original_shpfile, watermark = calculate_watermark_and_nc(watermarked_shpfile, l, argument)

    # 数据输出
    shp_output_folder = os.path.join(output_folder, 'shp')
    watermark_output_folder = os.path.join(output_folder, 'watermark')

    os.makedirs(shp_output_folder, exist_ok=True)
    os.makedirs(watermark_output_folder, exist_ok=True)

    # 输出原始数据
    output_shapefile_path = os.path.join(
        shp_output_folder,
        os.path.basename(watermarked_shpfile_path)
    )
    original_shpfile.to_file(output_shapefile_path)
    logger.info(f"原始数据保存: {output_shapefile_path}")

    # 输出提取的水印
    watermark_filename = f'{os.path.splitext(os.path.basename(watermarked_shpfile_path))[0]}_extracted.png'
    output_watermark_path = os.path.join(watermark_output_folder, watermark_filename)
    Image.fromarray(watermark.astype(bool)).save(output_watermark_path)
    logger.info(f"水印保存: {output_watermark_path}")

    return {
        'watermark_id': watermark_id,
        'original_shp_path': output_shapefile_path,
        'watermark_path': output_watermark_path,
        'watermark_array': watermark
    }


# 保持原有函数名的兼容性
def extract(watermarked_shpfile_path, vr):
    """兼容原有接口"""
    output_folder = os.path.join(os.getcwd(), 'extracted')
    return extract_vector_watermark(watermarked_shpfile_path, vr, output_folder)