"""
工具模块 - 坐标提取
"""
import logging
import numpy as np

logger = logging.getLogger(__name__)


def get_coor_nested(shpfile):
    """
    获取坐标，使每个对象成为一个数组，并将所有数组合并成一个大数组

    Args:
        shpfile: GeoDataFrame

    Returns:
        (coor_nested, feature_type) 坐标嵌套数组和要素类型列表
    """
    x_coords = []
    y_coords = []
    feature_type = []

    for geom in shpfile.geometry:
        if geom is not None:
            if geom.geom_type == 'Point':
                x_coords.append(np.array([geom.x]))
                y_coords.append(np.array([geom.y]))

            elif geom.geom_type == 'LineString':
                x_coords.append(np.array(geom.xy[0]))
                y_coords.append(np.array(geom.xy[1]))

            elif geom.geom_type == 'MultiLineString':
                x_mult = []
                y_mult = []
                for line in geom.geoms:
                    coords = np.array(line.xy)
                    x_mult.append(coords[0])
                    y_mult.append(coords[1])
                x_coords.append(x_mult)
                y_coords.append(y_mult)

            elif geom.geom_type == 'Polygon':
                coords = geom.exterior.coords
                x_coords.append(np.array(coords).T[0, :])
                y_coords.append(np.array(coords).T[1, :])

            elif geom.geom_type == 'MultiPolygon':
                x_mult = []
                y_mult = []
                for polygon in geom.geoms:
                    coords = polygon.exterior.coords
                    x_mult.append(np.array(coords).T[0, :])
                    y_mult.append(np.array(coords).T[1, :])
                x_coords.append(x_mult)
                y_coords.append(y_mult)

            else:
                if geom.geom_type not in feature_type:
                    logger.warning(f"存在未解析类型: {geom.geom_type}")

            feature_type.append(geom.geom_type)

    coor_nested = np.array([x_coords, y_coords], dtype=object)
    return coor_nested, feature_type


def get_coor_array(coor_nested, shp_type):
    """
    将嵌套坐标数组合并成一个数组

    Args:
        coor_nested: shp数据顶点的嵌套数组
        shp_type: 要素类型的数组

    Returns:
        合并后的坐标数组
    """
    x_array = []
    y_array = []

    for i in range(coor_nested.shape[1]):
        try:
            if isinstance(coor_nested[:, i][0][0], np.ndarray):
                if len(coor_nested[:, i][0]) == 0:
                    continue
                else:
                    for j in range(len(coor_nested[:, i][0])):
                        coor_group = np.vstack((coor_nested[:, i][0][j], coor_nested[:, i][1][j]))
                        x_array = np.hstack((x_array, coor_group[0, :]))
                        y_array = np.hstack((y_array, coor_group[1, :]))
            else:
                x_array = np.hstack((x_array, coor_nested[0, i]))
                y_array = np.hstack((y_array, coor_nested[1, i]))

        except IndexError:
            if shp_type[i] in ['MultiPolygon', 'MultiLineString']:
                if len(coor_nested[:, i][0]) == 0:
                    continue
                else:
                    for j in range(len(coor_nested[:, i][0])):
                        coor_group = np.vstack((coor_nested[:, i][0][j], coor_nested[:, i][1][j]))
                        x_array = np.hstack((x_array, coor_group[0, :]))
                        y_array = np.hstack((y_array, coor_group[1, :]))
            else:
                x_array = np.hstack((x_array, coor_nested[0, i]))
                y_array = np.hstack((y_array, coor_nested[1, i]))

    coor_array = np.vstack((x_array, y_array))
    return coor_array