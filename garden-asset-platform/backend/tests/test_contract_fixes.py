"""契约回归：注册日志失败不回滚用户；webp 溯源与允许扩展名一致（issue #37）。"""
import numpy as np
from PIL import Image

from app.extensions import db
from app.models.log import OperationLog
from app.models.user import User


def test_register_succeeds_when_logging_fails(client, app, monkeypatch):
    def boom(*args, **kwargs):
        raise RuntimeError('log backend down')

    monkeypatch.setattr(OperationLog, 'log', staticmethod(boom))

    response = client.post('/api/register', json={
        'username': 'logfailuser',
        'password': 'pass1234',
        'email': 'logfail@test.com',
    })
    assert response.status_code == 200, response.get_json()

    with app.app_context():
        assert User.query.filter_by(username='logfailuser').first() is not None


def test_trace_supports_webp(tmp_path, app):
    from algorithm.raster.embed import embed_raster_watermark_color
    from app.services.watermark_service import WatermarkService

    gradient = np.linspace(0, 255, 256 * 256, dtype=np.uint8).reshape(256, 256)
    rgb = np.stack([gradient, gradient, gradient], axis=-1)
    source = tmp_path / 'source.png'
    Image.fromarray(rgb).save(source)

    with app.app_context():
        result = embed_raster_watermark_color(
            image_path=str(source),
            watermark_path='data/watermark/default.png',
            output_folder=str(tmp_path / 'embedded'),
            method='dct',
            garden_code='TST',
        )

    webp_path = tmp_path / 'watermarked.webp'
    with Image.open(result['watermarked_path']) as watermarked:
        watermarked.save(webp_path, 'WEBP', lossless=True)

    with app.app_context():
        traced = WatermarkService.trace_from_file(str(webp_path))

    assert traced['success'] is True
    assert traced['watermark_id'] == result['watermark_id']
