"""HTTP 层错误返回中文提示（405/413 等不再透出 Werkzeug 英文描述）"""
import io


def test_method_not_allowed_returns_chinese_json(client):
    response = client.patch('/api/stats')

    assert response.status_code == 405
    payload = response.get_json()
    assert payload['code'] == 405
    assert '请求方法' in payload['message']


def test_oversized_upload_returns_chinese_json(client, app, auth_header):
    original_limit = app.config.get('MAX_CONTENT_LENGTH')
    app.config['MAX_CONTENT_LENGTH'] = 1024
    try:
        response = client.post(
            '/api/assets/upload',
            data={'file': (io.BytesIO(b'x' * 4096), 'large.jpg')},
            headers=auth_header,
            content_type='multipart/form-data',
        )
    finally:
        app.config['MAX_CONTENT_LENGTH'] = original_limit

    assert response.status_code == 413
    payload = response.get_json()
    assert payload['code'] == 413
    assert '过大' in payload['message']
