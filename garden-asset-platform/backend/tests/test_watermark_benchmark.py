"""水印鲁棒性实验室接口测试"""
import io
import re


def _sample_image_bytes(width=160, height=120):
    """生成尺寸可复现的测试图，避免依赖外部图片资源。"""
    from PIL import Image, ImageDraw

    image = Image.new('RGB', (width, height), (232, 238, 230))
    draw = ImageDraw.Draw(image)

    # 渐变 + 几何线条，覆盖平滑区与高频边缘
    for x in range(width):
        shade = int(190 + 40 * x / max(1, width - 1))
        draw.line([(x, 0), (x, height)], fill=(shade, 225, 220))
    draw.rectangle([12, 16, width - 24, height - 20], outline=(60, 90, 78), width=2)
    draw.ellipse([width // 3, height // 4, width * 2 // 3, height * 3 // 4],
                 fill=(120, 160, 145))

    buffer = io.BytesIO()
    image.save(buffer, 'PNG')
    return buffer.getvalue()


def test_benchmark_requires_login(client):
    response = client.post('/api/watermark/benchmark')

    assert response.status_code == 401


def test_missing_token_is_401_when_debug_propagation_is_off(client, app):
    """生产模式（debug/testing 均为 False）不能把 JWT 异常变成 500。"""
    app.config['TESTING'] = False
    app.debug = False

    response = client.post('/api/watermark/benchmark')
    assert response.status_code == 401
    payload = response.get_json()
    assert payload['code'] == 401
    assert 'Token' in payload['message']


def test_benchmark_rejects_non_image(client, auth_header):
    data = {'file': (io.BytesIO(b'not really an image'), 'notes.txt')}
    response = client.post(
        '/api/watermark/benchmark',
        data=data,
        content_type='multipart/form-data',
        headers=auth_header,
    )

    assert response.status_code == 400
    assert '图片' in response.get_json()['message']


def test_benchmark_rejects_corrupt_image(client, auth_header):
    data = {'file': (io.BytesIO(b'not really a png'), 'broken.png')}
    response = client.post(
        '/api/watermark/benchmark',
        data=data,
        content_type='multipart/form-data',
        headers=auth_header,
    )

    assert response.status_code == 400
    assert '无法解析' in response.get_json()['message']


def test_benchmark_runs_real_attacks(client, auth_header, app):
    data = {'file': (io.BytesIO(_sample_image_bytes()), 'garden.png')}
    response = client.post(
        '/api/watermark/benchmark',
        data=data,
        content_type='multipart/form-data',
        headers=auth_header,
    )

    assert response.status_code == 200
    payload = response.get_json()['data']

    assert re.match(r'^LAB-IMG-\d{14}-[0-9A-F]{4}$', payload['watermark_id'])
    assert payload['psnr'] > 20
    assert payload['method'] == 'DCT + QIM'
    assert payload['summary']['total'] == 8
    assert payload['summary']['recovered'] >= 1
    assert payload['watermark_preview'].startswith('data:image/png;base64,')

    origin = next(item for item in payload['attacks'] if item['key'] == 'origin')
    assert origin['id_recovered'] is True
    assert origin['recovered_id'] == payload['watermark_id']
    assert 0.9 <= origin['nc'] <= 1.0
    assert origin['extract_ms'] >= 0

    # 所有攻击都有明确结果（成功或带说明的失败），不会静默丢失
    assert len(payload['attacks']) == 8
    assert all(item['label'] and item['description'] for item in payload['attacks'])

    # 临时实验目录在请求结束后清理
    import os
    upload_root = os.path.join(
        app.config.get('UPLOAD_FOLDER', './uploads'), 'benchmark_tmp'
    )
    leftovers = [
        name for name in os.listdir(upload_root)
        if name.startswith('bench_')
    ] if os.path.isdir(upload_root) else []
    assert leftovers == []


def test_benchmark_rejects_oversized_upload(client, auth_header, app):
    app.config['WATERMARK_BENCHMARK_MAX_BYTES'] = 100
    data = {'file': (io.BytesIO(_sample_image_bytes()), 'garden.png')}
    response = client.post(
        '/api/watermark/benchmark',
        data=data,
        content_type='multipart/form-data',
        headers=auth_header,
    )

    assert response.status_code == 400
    assert '大小超过限制' in response.get_json()['message']
