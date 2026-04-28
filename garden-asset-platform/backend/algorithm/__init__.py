"""
水印算法模块
包含矢量水印和栅格水印的嵌入与提取算法
"""

from algorithm.vector.embed import embed_vector_watermark
from algorithm.vector.extract import extract_vector_watermark
from algorithm.raster.embed import embed_raster_watermark
from algorithm.raster.extract import extract_raster_watermark
from algorithm.utils.nc import NC, image_to_array

__all__ = [
    'embed_vector_watermark',
    'extract_vector_watermark',
    'embed_raster_watermark',
    'extract_raster_watermark',
    'NC',
    'image_to_array'
]