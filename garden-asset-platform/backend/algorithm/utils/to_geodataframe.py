"""
工具模块 - GeoDataFrame转换
"""
import numpy as np
from decimal import Decimal
from shapely.geometry import (
    Point,
    LineString,
    Polygon,
    MultiPoint,
    MultiLineString,
    MultiPolygon
)


def _convert_coords_to_decimal(coords_list):
    """
    将坐标列表中的浮点数转换为 Decimal 类型
    """
    return [(Decimal(str(x)), Decimal(str(y))) for x, y in coords_list]


def to_geodataframe(dataframe, index, coor_nested, shpfile_type):
    """
    将嵌套坐标数组转换为 GeoDataFrame 的几何对象

    Args:
        dataframe: GeoDataFrame
        index: 要素索引
        coor_nested: 嵌套坐标数组 [x_coords, y_coords]
        shpfile_type: 几何类型

    Returns:
        更新后的 GeoDataFrame
    """
    x_coords = coor_nested[0]
    y_coords = coor_nested[1]

    # 检查是否为空
    if hasattr(x_coords, 'size'):
        if x_coords.size == 0 or y_coords.size == 0:
            dataframe.loc[index, 'geometry'] = None
            return dataframe

    if shpfile_type == 'Point':
        if hasattr(x_coords, 'size') and x_coords.size > 0:
            dataframe.loc[index, 'geometry'] = Point(
                Decimal(str(x_coords[0])),
                Decimal(str(y_coords[0]))
            )
        else:
            dataframe.loc[index, 'geometry'] = None

    elif shpfile_type == 'LineString':
        if hasattr(x_coords, 'size') and x_coords.size > 1:
            points = _convert_coords_to_decimal(zip(x_coords, y_coords))
            dataframe.loc[index, 'geometry'] = LineString(points)
        else:
            dataframe.loc[index, 'geometry'] = None

    elif shpfile_type == 'MultiLineString':
        lines = []
        if isinstance(x_coords[0], list) or isinstance(x_coords[0], np.ndarray):
            for i in range(len(x_coords)):
                if hasattr(x_coords[i], 'size') and x_coords[i].size > 1:
                    points = _convert_coords_to_decimal(zip(x_coords[i], y_coords[i]))
                    lines.append(LineString(points))
        else:
            if hasattr(x_coords, 'size') and x_coords.size > 1:
                points = _convert_coords_to_decimal(zip(x_coords, y_coords))
                lines.append(LineString(points))

        if lines:
            dataframe.loc[index, 'geometry'] = MultiLineString(lines)
        else:
            dataframe.loc[index, 'geometry'] = None

    elif shpfile_type == 'MultiPoint':
        points = []
        if isinstance(x_coords[0], list) or isinstance(x_coords[0], np.ndarray):
            for i in range(len(x_coords)):
                if hasattr(x_coords[i], 'size') and x_coords[i].size > 0:
                    points.append(Point(
                        Decimal(str(x_coords[i][0])),
                        Decimal(str(y_coords[i][0]))
                    ))
        else:
            if hasattr(x_coords, 'size') and x_coords.size > 0:
                points.append(Point(
                    Decimal(str(x_coords[0])),
                    Decimal(str(y_coords[0]))
                ))

        dataframe.loc[index, 'geometry'] = MultiPoint(points) if points else None

    elif shpfile_type == 'Polygon':
        if hasattr(x_coords, 'size') and x_coords.size > 2:
            exterior_coords = _convert_coords_to_decimal(zip(x_coords, y_coords))
            dataframe.loc[index, 'geometry'] = Polygon(exterior_coords)
        else:
            dataframe.loc[index, 'geometry'] = None

    elif shpfile_type == 'MultiPolygon':
        polygons = []
        if isinstance(x_coords[0], list) or isinstance(x_coords[0], np.ndarray):
            for i in range(len(x_coords)):
                if hasattr(x_coords[i], 'size') and x_coords[i].size > 2:
                    exterior_coords = _convert_coords_to_decimal(zip(x_coords[i], y_coords[i]))
                    polygons.append(Polygon(exterior_coords))
        else:
            if hasattr(x_coords, 'size') and x_coords.size > 2:
                exterior_coords = _convert_coords_to_decimal(zip(x_coords, y_coords))
                polygons.append(Polygon(exterior_coords))

        if polygons:
            dataframe.loc[index, 'geometry'] = MultiPolygon(polygons)
        else:
            dataframe.loc[index, 'geometry'] = None

    else:
        dataframe.loc[index, 'geometry'] = None

    return dataframe