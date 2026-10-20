"""
矢量水印算法 - 嵌入模块
基于坐标扰动的矢量数据水印嵌入算法
"""
import os
import zipfile
import random
import logging
from decimal import Decimal
from datetime import datetime
import uuid
import numpy as np
from PIL import Image
import geopandas as gpd

from algorithm.utils.get_coor import get_coor_nested, get_coor_array
from algorithm.utils.to_geodataframe import to_geodataframe


logger = logging.getLogger(__name__)


def watermark_embed(coor, coor_l, w, n, R):
    """
    对坐标嵌入水印

    Args:
        coor: 变换后的坐标 (x, y)
        coor_l: 区域左下角顶点的坐标 (xl, yl)
        w: 水印值
        n: 嵌入强度
        R: 区域大小

    Returns:
        嵌入水印后的坐标
    """
    x, y = coor
    xl, yl = coor_l
    k = (x - xl) / 2 ** n
    embed_x = xl + w * (R / 2 ** n) + k
    embed_y = y
    return np.vstack([embed_x, embed_y])


def coor_process(coor, argument, dis):
    """
    对坐标进行处理

    Args:
        coor: 需要处理的坐标
        argument: 算法参数字典 {n, R, W}
        dis: 用于随机种子生成的距离值

    Returns:
        嵌入水印的坐标
    """
    n, R, W = argument.values()

    random.seed(dis)
    index = random.randint(0, len(W) - 1)
    w = int(''.join(map(str, W[index])), 2)

    coor = np.array([Decimal(str(x)) for x in np.nditer(coor, flags=['refs_ok'])])
    coor_l = coor // R * R
    embed_coor = watermark_embed(coor, coor_l, w, n, R)
    return embed_coor


def coor_group_process(coor_group, argument):
    """
    对坐标组进行处理

    Args:
        coor_group: 需要处理的坐标组
        argument: 算法参数字典

    Returns:
        嵌入水印的坐标组
    """
    embed_coor_group = np.array([[], []])
    for i in range(coor_group.shape[1]):
        coor = coor_group[:, i]
        if i == coor_group.shape[1] - 1:
            embed_coor = coor[:, np.newaxis]
        else:
            dis = abs(coor[1] - coor_group[:, i + 1][1])
            embed_coor = coor_process(coor, argument, dis)
        embed_coor_group = np.concatenate((embed_coor_group, embed_coor), axis=1)
    return embed_coor_group


def traversal_nested_coor_group(x_nested, y_nested, feature_type, argument):
    """
    对于多线、多面、多点等情况，按部件逐个处理

    Args:
        x_nested: 该要素各部件 x 坐标数组
        y_nested: 该要素各部件 y 坐标数组
        feature_type: 要素的类型
        argument: 算法参数字典

    Returns:
        该要素更新后的嵌套坐标组
    """
    processed_x_nested = []
    processed_y_nested = []

    for x_part, y_part in zip(x_nested, y_nested):
        coor_group = np.vstack((x_part, y_part))
        if coor_group.size == 0:
            continue
        processed_coor_group = coor_group_process(coor_group, argument)

        # 如果部件为面，则需要满足首尾顶点的坐标相同
        if (feature_type == 'MultiPolygon'
                and np.size(processed_coor_group) not in [0, 2]
                and not np.array_equal(processed_coor_group[:, 0], processed_coor_group[:, -1])):
            processed_coor_group[:, -1] = processed_coor_group[:, 0]

        processed_x_nested.append(processed_coor_group[0, :])
        processed_y_nested.append(processed_coor_group[1, :])

    return np.array([processed_x_nested, processed_y_nested], dtype=object)


def traversal_coor_group(coor_nested, shp_type, processed_shpfile, argument):
    """
    对所有要素进行遍历

    Args:
        coor_nested: 所有要素组成的嵌套坐标数组
        shp_type: 每个要素类型组成的数组
        processed_shpfile: 处理后的shp文件
        argument: 算法参数字典

    Returns:
        processed_shpfile
    """
    for feature_index in range(coor_nested.shape[1]):
        x_entry = coor_nested[0, feature_index]
        y_entry = coor_nested[1, feature_index]
        feature_type = shp_type[feature_index]

        # 多部件几何（MultiPoint/MultiLineString/MultiPolygon）按部件逐个处理
        if isinstance(x_entry, list):
            processed_coor_group = traversal_nested_coor_group(
                x_entry, y_entry, feature_type, argument
            )
        else:
            coor_group = np.vstack((x_entry, y_entry))
            # 空占位（None / 暂不支持的几何）保持原几何不动
            if coor_group.size == 0:
                continue
            processed_coor_group = coor_group_process(coor_group, argument)
            # 如果要素为面，则需要满足首尾顶点的坐标相同
            if (feature_type == 'Polygon'
                    and np.size(processed_coor_group) not in [0, 2]
                    and not np.array_equal(processed_coor_group[:, 0], processed_coor_group[:, -1])):
                processed_coor_group[:, -1] = processed_coor_group[:, 0]

        # 将改变的要素坐标组更新到geodataframe
        processed_shpfile = to_geodataframe(processed_shpfile, feature_index, processed_coor_group,
                                            feature_type)

    return processed_shpfile


def generate_watermark_id(garden_code, asset_type_code):
    """
    生成水印ID

    Args:
        garden_code: 园林编码
        asset_type_code: 资产类型编码

    Returns:
        水印ID字符串
    """
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    checksum = uuid.uuid4().hex[:4].upper()
    return f"{garden_code}-{asset_type_code}-{timestamp}-{checksum}"


def preprocess_watermark(watermark_path, n=4):
    """
    预处理水印图像

    Args:
        watermark_path: 水印图像路径
        n: 嵌入强度

    Returns:
        水印参数字典
    """
    watermark = np.array(Image.open(watermark_path)).astype(int)

    # 替换边缘区域
    replace_matrix = np.full((8, 8), -1)
    watermark[:8, :8] = watermark[:8, -8:] = watermark[-8:, :8] = replace_matrix
    watermark = watermark.flatten()
    watermark = list(filter(lambda x: x != -1, watermark))

    # 补零到n的整数倍
    watermark += [0] * ((n - len(watermark) % n) % n)
    W = np.array_split(watermark, len(watermark) // n)

    return {'n': n, 'R': Decimal('1e-7'), 'W': W}


def embed_vector_watermark(shpfile_path, watermark_path, output_folder, garden_code='GEN', asset_type_code='VEC'):
    """
    矢量数据水印嵌入主函数

    Args:
        shpfile_path: 矢量数据文件路径(SHP)
        watermark_path: 水印图像路径
        output_folder: 输出文件夹
        garden_code: 园林编码
        asset_type_code: 资产类型编码

    Returns:
        (zip_file_path, watermark_id, vr) 嵌入结果
    """
    # 算法参数
    n = 4
    tau = 10 ** (-6)
    R = Decimal('1e-7')

    # 生成水印ID
    watermark_id = generate_watermark_id(garden_code, asset_type_code)

    logger.info(f"开始嵌入水印, 水印ID: {watermark_id}")

    # 数据读取
    original_shpfile = gpd.read_file(shpfile_path)
    coor_nested, feature_type = get_coor_nested(original_shpfile)

    # 矢量算法按 45x45 的二维水印设计（提取端 side_length 也是 45）
    vector_side = 45
    watermark_image = Image.open(watermark_path).convert('L').resize(
        (vector_side, vector_side), Image.LANCZOS
    )
    watermark = np.array(watermark_image).astype(int)
    # 矢量算法按比特分组（每组 4 位），必须先二值化
    watermark = (watermark > 127).astype(int)

    # 水印预处理
    replace_matrix = np.full((8, 8), -1)
    watermark[:8, :8] = watermark[:8, -8:] = watermark[-8:, :8] = replace_matrix
    watermark = watermark.flatten()
    watermark = list(filter(lambda x: x != -1, watermark))
    watermark += [0] * ((n - len(watermark) % n) % n)
    W = np.array_split(watermark, len(watermark) // n)
    argument = {'n': n, 'R': R, 'W': W}

    # 水印嵌入
    watermarked_shpfile = original_shpfile.copy()
    watermarked_shpfile = traversal_coor_group(coor_nested, feature_type, watermarked_shpfile, argument)

    # 把水印 ID 写入属性列，供溯源时直接读取（几何水印仍是鲁棒性来源）
    # DBF 字段名最多 10 个字符，使用短名避免被截断
    watermarked_shpfile['wm_id'] = watermark_id

    # 计算验证值
    coor_nested, feature_type = get_coor_nested(watermarked_shpfile)
    coor_array = get_coor_array(coor_nested, feature_type)
    vr = np.mean(coor_array, axis=1)
    vr = [float(format(coor, '.15f')) for coor in vr]

    logger.info(f"验证值: {vr}")

    # 数据输出
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    # 输出文件名
    output_filename = f"{watermark_id}.shp"
    shapefile_path = os.path.join(output_folder, output_filename)
    watermarked_shpfile.to_file(shapefile_path)

    # 创建ZIP文件
    shapefile_extensions = ['.shp', '.shx', '.dbf', '.prj', '.cpg']
    zip_filename = f"{watermark_id}.zip"
    zip_file_path = os.path.join(output_folder, zip_filename)

    with zipfile.ZipFile(zip_file_path, 'w') as zipf:
        for ext in shapefile_extensions:
            filepath = shapefile_path.replace('.shp', ext)
            if os.path.exists(filepath):
                zipf.write(filepath, os.path.basename(filepath))

    logger.info(f"水印嵌入完成, 输出: {zip_file_path}")

    return {
        'zip_file_path': zip_file_path,
        'watermark_id': watermark_id,
        'vr': vr,
        'original_path': shpfile_path,
        'watermarked_path': shapefile_path
    }


# 保持原有函数名的兼容性
def embed(shpfile_path, watermark_path, output_filename):
    """兼容原有接口"""
    output_folder = os.path.dirname(output_filename)
    result = embed_vector_watermark(shpfile_path, watermark_path, output_folder)
    return result['zip_file_path'], result['vr']