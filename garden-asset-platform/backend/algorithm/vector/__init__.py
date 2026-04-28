"""
矢量水印算法 __init__.py
"""
from algorithm.vector.embed import embed_vector_watermark, embed
from algorithm.vector.extract import extract_vector_watermark, extract

__all__ = [
    'embed_vector_watermark',
    'extract_vector_watermark',
    'embed',
    'extract'
]