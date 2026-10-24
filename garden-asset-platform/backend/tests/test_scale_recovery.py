"""回归测试：缩放恢复与 ID 字段解析的边界。"""
import numpy as np
from PIL import Image

from algorithm.raster.embed import ID_FIELD_BYTES, bits_to_id
from algorithm.raster.extract import _decode_valid_id, _resolve_scaled_image


def _payload_bits(payload, repeat=20):
    payload = payload.ljust(ID_FIELD_BYTES, b'\x00')
    bits = []
    for byte in payload:
        for shift in range(7, -1, -1):
            bits.append((byte >> shift) & 1)
    return bits * repeat


def test_bits_to_id_ignores_padding_noise():
    """攻击后 ID 之后的填充区可能被改写，不应连累合法 ID。"""
    payload = b'ZY-IMG-20260101000000-ABCD\x00GARBAGE'
    assert bits_to_id(_payload_bits(payload)) == 'ZY-IMG-20260101000000-ABCD'


def test_bits_to_id_rejects_non_utf8():
    assert bits_to_id(_payload_bits(b'\xff\xfe\xfd')) is None


def test_decode_valid_id_returns_none_for_tiny_image():
    image = Image.effect_noise((3, 3), 100).convert('RGB')
    assert _decode_valid_id(np.array(image)) is None


def test_resolve_scaled_image_skips_tiny_candidates():
    image = Image.effect_noise((5, 5), 100).convert('RGB')
    restored, watermark_id = _resolve_scaled_image(image)
    assert restored is None
    assert watermark_id is None
