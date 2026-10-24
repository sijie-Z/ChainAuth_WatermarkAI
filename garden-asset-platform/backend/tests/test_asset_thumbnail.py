"""资产缩略图端点与上传缩略图生成测试"""
from io import BytesIO

from PIL import Image

from app.extensions import db
from app.models.asset import Asset
from app.utils.thumbnails import generate_thumbnail, generate_thumbnail_set


def make_jpeg(width=640, height=420, color=(47, 107, 90)):
    buffer = BytesIO()
    Image.new('RGB', (width, height), color).save(buffer, 'JPEG')
    buffer.seek(0)
    return buffer


def test_thumbnail_endpoint_serves_image(client, app, tmp_path, sample_asset):
    with app.app_context():
        app.config['UPLOAD_FOLDER'] = str(tmp_path)
        asset = db.session.get(Asset, sample_asset)
        source = tmp_path / 'source.jpg'
        source.write_bytes(make_jpeg().getvalue())
        asset.thumbnail_path = generate_thumbnail(source, asset.id)
        db.session.commit()

    response = client.get(f'/api/assets/{sample_asset}/thumbnail')

    assert response.status_code == 200
    assert response.content_type == 'image/jpeg'
    assert len(response.data) > 0
    response.close()


def test_thumbnail_card_variant_is_smaller(client, app, tmp_path, sample_asset):
    with app.app_context():
        app.config['UPLOAD_FOLDER'] = str(tmp_path)
        asset = db.session.get(Asset, sample_asset)
        source = tmp_path / 'source.jpg'
        source.write_bytes(make_jpeg(width=1600, height=1200).getvalue())
        detail_path, card_path = generate_thumbnail_set(source, asset.id)
        full_bytes = (tmp_path / detail_path).stat().st_size
        card_bytes = (tmp_path / card_path).stat().st_size
        asset.thumbnail_path = detail_path
        db.session.commit()

    response = client.get(f'/api/assets/{sample_asset}/thumbnail?size=card')

    assert response.status_code == 200
    assert card_bytes < full_bytes
    assert len(response.data) == card_bytes
    response.close()


def test_thumbnail_endpoint_404_when_missing(client, app, tmp_path, sample_asset):
    with app.app_context():
        app.config['UPLOAD_FOLDER'] = str(tmp_path)

    response = client.get(f'/api/assets/{sample_asset}/thumbnail')

    assert response.status_code == 404


def test_thumbnail_endpoint_hidden_for_deleted_asset(client, app, tmp_path, sample_asset):
    with app.app_context():
        app.config['UPLOAD_FOLDER'] = str(tmp_path)
        asset = db.session.get(Asset, sample_asset)
        source = tmp_path / 'source.jpg'
        source.write_bytes(make_jpeg().getvalue())
        asset.thumbnail_path = generate_thumbnail(source, asset.id)
        asset.status = 'deleted'
        db.session.commit()

    response = client.get(f'/api/assets/{sample_asset}/thumbnail')

    assert response.status_code == 404


def test_thumbnail_endpoint_unknown_id(client):
    response = client.get('/api/assets/not-a-uuid/thumbnail')

    assert response.status_code == 404


def test_upload_generates_thumbnail(client, app, tmp_path, auth_header):
    with app.app_context():
        app.config['UPLOAD_FOLDER'] = str(tmp_path)

    response = client.post(
        '/api/assets/upload',
        data={
            'file': (make_jpeg(), '拙政园测试.jpg'),
            'title': '拙政园测试影像',
            'asset_type': 'image'
        },
        headers=auth_header,
        content_type='multipart/form-data'
    )

    assert response.status_code == 200
    asset_id = response.get_json()['data']['asset_id']

    with app.app_context():
        asset = db.session.get(Asset, asset_id)
        assert asset.thumbnail_path
        assert (tmp_path / asset.thumbnail_path).is_file()
        assert (tmp_path / f'thumbnails/{asset_id}-card.jpg').is_file()

    thumb = client.get(f'/api/assets/{asset_id}/thumbnail')
    assert thumb.status_code == 200
    assert thumb.content_type == 'image/jpeg'
    thumb.close()
