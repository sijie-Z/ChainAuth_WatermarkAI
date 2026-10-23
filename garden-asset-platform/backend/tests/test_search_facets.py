"""检索分面：标签、格式、日期与上传者筛选"""
from datetime import datetime, timedelta

import pytest

from app.extensions import db
from app.models import Asset, AssetTag, Garden, User


@pytest.fixture
def facet_assets(app, auth_header):
    with app.app_context():
        owner = User.query.filter_by(username='testuser').first()
        garden = Garden(code='FAC', name='分面测试园', status='active')
        db.session.add(garden)
        db.session.flush()
        now = datetime.utcnow()
        specs = [
            ('FAC-IMG-001', 'image', 'JPG', ['古典建筑', '山水景观'], now - timedelta(days=10)),
            ('FAC-IMG-002', 'image', 'PNG', ['古典建筑'], now - timedelta(days=2)),
            ('FAC-DOC-003', 'document', 'PDF', ['历史文献'], now),
        ]
        for code, asset_type, fmt, tags, created_at in specs:
            asset = Asset(
                asset_code=code,
                title=f'分面资产 {code}',
                asset_type=asset_type,
                file_format=fmt,
                garden_id=garden.id,
                creator_id=owner.id,
                owner_id=owner.id,
                uploader_id=owner.id,
                status='published',
                created_at=created_at
            )
            db.session.add(asset)
            db.session.flush()
            for tag in tags:
                db.session.add(AssetTag(asset_id=asset.id, name=tag))
        db.session.commit()
        return {'user_id': owner.id, 'now': now}


def test_tag_facets(client, auth_header, facet_assets):
    response = client.get('/api/tags')
    assert response.status_code == 200
    tags = {item['name']: item['count'] for item in response.get_json()['data']}
    assert tags['古典建筑'] == 2
    assert tags['历史文献'] == 1


def test_filter_by_tag_and_format(client, auth_header, facet_assets):
    tagged = client.get('/api/assets?tag=古典建筑', headers=auth_header)
    assert tagged.status_code == 200
    assert tagged.get_json()['data']['total'] == 2

    pdf = client.get('/api/assets?file_format=pdf', headers=auth_header)
    assert pdf.status_code == 200
    assert pdf.get_json()['data']['total'] == 1


def test_filter_by_date_and_uploader(client, auth_header, facet_assets):
    today = facet_assets['now'].strftime('%Y-%m-%d')
    response = client.get(
        f'/api/assets?date_from={today}&date_to={today}',
        headers=auth_header
    )
    assert response.status_code == 200
    assert response.get_json()['data']['total'] == 1

    by_uploader = client.get(
        f"/api/assets?uploader_id={facet_assets['user_id']}",
        headers=auth_header
    )
    assert by_uploader.get_json()['data']['total'] == 3


def test_invalid_date_filter_returns_400(client, auth_header, facet_assets):
    response = client.get('/api/assets?date_from=not-a-date', headers=auth_header)
    assert response.status_code == 400


def test_keyword_searches_tags_garden_and_uploader(client, auth_header, facet_assets):
    by_tag = client.get('/api/assets?keyword=古典建筑', headers=auth_header)
    assert by_tag.get_json()['data']['total'] == 2

    by_garden = client.get('/api/assets?keyword=分面测试园', headers=auth_header)
    assert by_garden.get_json()['data']['total'] == 3

    by_uploader = client.get('/api/assets?keyword=testuser', headers=auth_header)
    assert by_uploader.get_json()['data']['total'] == 3

    relevance = client.get('/api/assets?keyword=FAC-DOC-003', headers=auth_header)
    assert relevance.get_json()['data']['items'][0]['asset_code'] == 'FAC-DOC-003'
