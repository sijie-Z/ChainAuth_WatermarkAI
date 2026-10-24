"""存证校验必须使用原始文件指纹，而不是水印派生文件"""
from io import BytesIO

from PIL import Image

from app.extensions import db
from app.models import Asset


def _jpeg(color=(40, 100, 80), size=(320, 240)):
    buffer = BytesIO()
    Image.new('RGB', size, color).save(buffer, 'JPEG')
    buffer.seek(0)
    return buffer


def test_watermarked_asset_verifies_against_original_hash(
    client, app, tmp_path, auth_header
):
    app.config['UPLOAD_FOLDER'] = str(tmp_path)

    upload = client.post(
        '/api/assets/upload',
        data={
            'file': (_jpeg(), '存证校验.jpg'),
            'title': '存证校验影像',
            'asset_type': 'image'
        },
        headers=auth_header,
        content_type='multipart/form-data'
    )
    assert upload.status_code == 200
    asset_id = upload.get_json()['data']['asset_id']

    embedded = client.post(
        '/api/watermark/embed', json={'asset_id': asset_id}, headers=auth_header
    )
    assert embedded.status_code == 200, embedded.get_json()

    registered = client.post(
        '/api/blockchain/register', json={'asset_id': asset_id}, headers=auth_header
    )
    assert registered.status_code == 200, registered.get_json()

    with app.app_context():
        asset = db.session.get(Asset, asset_id)
        asset.status = 'published'
        db.session.commit()

    verified = client.get(f'/api/blockchain/verify/{asset_id}')
    assert verified.status_code == 200
    payload = verified.get_json()
    assert payload['verified'] is True, payload
    assert payload['data']['checks']['file_hash'] is True
    assert payload['data']['simulated'] is True
