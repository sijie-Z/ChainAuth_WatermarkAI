"""用户合集：创建、加入资产、可见性、编辑与删除"""
import pytest

from app.extensions import db
from app.models import Asset, Garden, User


@pytest.fixture
def collection_assets(app, auth_header):
    with app.app_context():
        owner = User.query.filter_by(username='testuser').first()
        garden = Garden(code='COL', name='合集测试园', status='active')
        db.session.add(garden)
        db.session.flush()

        published = Asset(
            asset_code='COL-IMG-001',
            title='已发布合集资产',
            asset_type='image',
            garden_id=garden.id,
            creator_id=owner.id,
            owner_id=owner.id,
            uploader_id=owner.id,
            status='published'
        )
        draft = Asset(
            asset_code='COL-IMG-002',
            title='自己的草稿',
            asset_type='image',
            garden_id=garden.id,
            creator_id=owner.id,
            owner_id=owner.id,
            uploader_id=owner.id,
            status='draft'
        )
        db.session.add_all([published, draft])
        db.session.commit()
        return {
            'owner_id': owner.id,
            'published_id': published.id,
            'draft_id': draft.id
        }


def test_collection_crud_and_add_assets(client, auth_header, collection_assets):
    created = client.post('/api/collections', headers=auth_header, json={
        'name': '拙政园水景',
        'description': '用于课程案例',
        'is_public': True
    })
    assert created.status_code == 200
    collection = created.get_json()['data']
    collection_id = collection['id']
    assert collection['asset_count'] == 0

    added = client.post(
        f'/api/collections/{collection_id}/assets',
        headers=auth_header,
        json={'asset_ids': [collection_assets['published_id'], collection_assets['draft_id']]}
    )
    assert added.status_code == 200
    assert added.get_json()['data']['added'] == 2

    listing = client.get(
        f"/api/collections?asset_id={collection_assets['published_id']}",
        headers=auth_header
    )
    item = next(row for row in listing.get_json()['data'] if row['id'] == collection_id)
    assert item['contains'] is True
    assert item['asset_count'] == 2

    detail = client.get(f'/api/collections/{collection_id}', headers=auth_header)
    assert detail.status_code == 200
    assert len(detail.get_json()['data']['assets']) == 2

    removed = client.delete(
        f"/api/collections/{collection_id}/assets/{collection_assets['draft_id']}",
        headers=auth_header
    )
    assert removed.status_code == 200
    assert removed.get_json()['data']['asset_count'] == 1

    updated = client.put(
        f'/api/collections/{collection_id}',
        headers=auth_header,
        json={'name': '拙政园水景（修订）', 'is_public': False}
    )
    assert updated.status_code == 200
    assert updated.get_json()['data']['name'] == '拙政园水景（修订）'

    deleted = client.delete(f'/api/collections/{collection_id}', headers=auth_header)
    assert deleted.status_code == 200
    assert client.get(f'/api/collections/{collection_id}', headers=auth_header).status_code == 404


def test_other_user_cannot_edit_collection(client, auth_header, collection_assets):
    created = client.post('/api/collections', headers=auth_header, json={
        'name': '私有合集'
    })
    collection_id = created.get_json()['data']['id']

    client.post('/api/register', json={
        'username': 'collectionother',
        'password': 'test123',
        'email': 'collectionother@test.com'
    })
    login = client.post('/api/login', json={
        'username': 'collectionother',
        'password': 'test123'
    })
    other_headers = {
        'Authorization': f"Bearer {login.get_json()['data']['access_token']}"
    }

    assert client.put(
        f'/api/collections/{collection_id}',
        headers=other_headers,
        json={'name': '改别人的合集'}
    ).status_code == 403
    assert client.delete(
        f'/api/collections/{collection_id}',
        headers=other_headers
    ).status_code == 403
    assert client.get(
        f'/api/collections/{collection_id}',
        headers=other_headers
    ).status_code == 403


def test_public_collection_only_exposes_published_assets(client, auth_header, collection_assets):
    created = client.post('/api/collections', headers=auth_header, json={
        'name': '公开合集',
        'is_public': True
    })
    collection_id = created.get_json()['data']['id']
    client.post(
        f'/api/collections/{collection_id}/assets',
        headers=auth_header,
        json={'asset_ids': [collection_assets['published_id'], collection_assets['draft_id']]}
    )

    client.post('/api/register', json={
        'username': 'collectionviewer',
        'password': 'test123',
        'email': 'collectionviewer@test.com'
    })
    login = client.post('/api/login', json={
        'username': 'collectionviewer',
        'password': 'test123'
    })
    viewer_headers = {
        'Authorization': f"Bearer {login.get_json()['data']['access_token']}"
    }

    detail = client.get(f'/api/collections/{collection_id}', headers=viewer_headers)
    assert detail.status_code == 200
    assets = detail.get_json()['data']['assets']
    assert [asset['id'] for asset in assets] == [collection_assets['published_id']]


def test_collection_name_is_required(client, auth_header):
    assert client.post('/api/collections', headers=auth_header, json={
        'name': '   '
    }).status_code == 400
