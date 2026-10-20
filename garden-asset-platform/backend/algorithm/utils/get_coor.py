"""
工具模块 - 坐标提取
"""
import logging
import numpy as np

logger = logging.getLogger(__name__)


def _geometry_coords(geom):
    """把单个几何体的坐标拆成 (x 数组列表, y 数组列表)；未知类型返回 None。"""
    geom_type = geom.geom_type
    if geom_type == 'Point':
        return [np.array([geom.x])], [np.array([geom.y])]
    if geom_type == 'LineString':
        return [np.array(geom.xy[0])], [np.array(geom.xy[1])]
    if geom_type == 'MultiLineString':
        return (
            [np.array(line.xy[0]) for line in geom.geoms],
            [np.array(line.xy[1]) for line in geom.geoms],
        )
    if geom_type == 'Polygon':
        coords = np.array(geom.exterior.coords)
        return [coords.T[0, :]], [coords.T[1, :]]
    if geom_type == 'MultiPolygon':
        xs, ys = [], []
        for polygon in geom.geoms:
            coords = np.array(polygon.exterior.coords)
            xs.append(coords.T[0, :])
            ys.append(coords.T[1, :])
        return xs, ys
    if geom_type == 'MultiPoint':
        return (
            [np.array([point.x]) for point in geom.geoms],
            [np.array([point.y]) for point in geom.geoms],
        )
    if geom_type == 'GeometryCollection':
        xs, ys = [], []
        for sub in geom.geoms:
            sub_coords = _geometry_coords(sub)
            if sub_coords:
                xs.extend(sub_coords[0])
                ys.extend(sub_coords[1])
        return (xs, ys) if xs else None
    return None


def get_coor_nested(shpfile):
    """
    获取坐标，使每个对象成为一个数组，并将所有数组合并成一个大数组

    Args:
        shpfile: GeoDataFrame

    Returns:
        (coor_nested, feature_type) 坐标嵌套数组和要素类型列表

    注意：feature_type 与坐标列表必须一一对应；未解析的几何类型直接跳过，
    不能只记录类型不记录坐标，否则后续按列下标写回会串要素。
    """
    x_coords = []
    y_coords = []
    feature_type = []

    for geom in shpfile.geometry:
        coords = _geometry_coords(geom) if geom is not None else None
        if not coords:
            if geom is not None:
                logger.warning(f"存在未解析类型: {geom.geom_type}，该要素保持原样")
            # 占位，保证 coor_nested 下标与原始要素下标一一对应；
            # 否则跳过任何一个要素都会让后续要素写回错位。
            x_coords.append(np.array([], dtype=float))
            y_coords.append(np.array([], dtype=float))
            feature_type.append(geom.geom_type if geom is not None else None)
            continue

        xs, ys = coords
        if len(xs) == 1:
            x_coords.append(xs[0])
            y_coords.append(ys[0])
        else:
            x_coords.append(xs)
            y_coords.append(ys)
        feature_type.append(geom.geom_type)

    # 显式逐格填充 object 数组：np.array([x_coords, y_coords]) 在各要素顶点数
    # 相同时会把它们广播成多维数组，导致多部件要素被压平、下标错位。
    coor_nested = np.empty((2, len(x_coords)), dtype=object)
    for feature_index, value in enumerate(x_coords):
        coor_nested[0, feature_index] = value
    for feature_index, value in enumerate(y_coords):
        coor_nested[1, feature_index] = value

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