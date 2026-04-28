"""
WKT几何工具
用于处理地理数据
"""
from shapely.geometry import Point, Polygon, MultiPolygon
from shapely.wkt import loads, dumps


def point_to_wkt(lng, lat):
    """经纬度转WKT"""
    return f'POINT({lng} {lat})'


def wkt_to_point(wkt):
    """WKT转经纬度"""
    geom = loads(wkt)
    if geom.geom_type == 'Point':
        return geom.x, geom.y
    return None


def polygon_to_wkt(coordinates):
    """多边形坐标转WKT"""
    if not coordinates:
        return None
    poly = Polygon(coordinates)
    return dumps(poly)


def wkt_to_polygon(wkt):
    """WKT转多边形坐标"""
    geom = loads(wkt)
    if geom.geom_type == 'Polygon':
        return list(geom.exterior.coords)
    return None


def get_geometry_bounds(wkt):
    """获取几何范围"""
    geom = loads(wkt)
    return geom.bounds  # (minx, miny, maxx, maxy)


def get_geometry_area(wkt):
    """获取几何面积"""
    geom = loads(wkt)
    return geom.area


def get_geometry_centroid(wkt):
    """获取几何中心点"""
    geom = loads(wkt)
    centroid = geom.centroid
    return centroid.x, centroid.y


def is_point_in_polygon(lng, lat, polygon_wkt):
    """判断点是否在多边形内"""
    point = Point(lng, lat)
    polygon = loads(polygon_wkt)
    return polygon.contains(point)


def calculate_distance(lng1, lat1, lng2, lat2):
    """计算两点距离 (米)"""
    from math import radians, sin, cos, sqrt, atan2

    R = 6371000  # 地球半径(米)
    lat1, lat2, lng1, lng2 = map(radians, [lat1, lat2, lng1, lng2])

    dlat = lat2 - lat1
    dlng = lng2 - lng1

    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlng/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))

    return R * c