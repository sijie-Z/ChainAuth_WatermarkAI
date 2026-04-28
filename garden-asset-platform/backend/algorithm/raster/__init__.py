"""
栅格水印算法 __init__.py
"""
from algorithm.raster.embed import embed_raster_watermark, embed_raster_watermark_color
from algorithm.raster.extract import extract_raster_watermark

__all__ = [
    'embed_raster_watermark',
    'embed_raster_watermark_color',
    'extract_raster_watermark'
]