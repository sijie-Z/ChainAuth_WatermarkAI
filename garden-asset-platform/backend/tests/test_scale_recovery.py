"""回归测试：缩放恢复遇到容量不足的小尺寸候选图时不得抛 IndexError（issue #31）。"""
import numpy as np
from PIL import Image

from algorithm.raster.extract import _decode_valid_id, _resolve_scaled_image


def test_decode_valid_id_returns_none_for_tiny_image():
    image = Image.effect_noise((3, 3), 100).convert('RGB')
    assert _decode_valid_id(np.array(image)) is None


def test_resolve_scaled_image_skips_tiny_candidates():
    image = Image.effect_noise((5, 5), 100).convert('RGB')
    restored, watermark_id = _resolve_scaled_image(image)
    assert restored is None
    assert watermark_id is None
