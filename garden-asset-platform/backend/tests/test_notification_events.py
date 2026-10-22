"""事件型通知：资产审核结果会通知上传者"""
from datetime import datetime

import pytest

from app.extensions import db
from app.models import Asset, Garden, User


@pytest.fixture
def pending_asset(app, auth_header):
    with app.app_context():
        owner = User.query.filter_by(username='testuser').first()
        garden = Garden(code='NOTIF', name='通知测试园', status='active')
        db.session.add(garden)
        db.session.flush()
        asset = Asset(
            asset_code='NOTIF-IMG-001',
            title='通知测试资产',
            asset_type='document',
            garden_id=garden.id,
            creator_id=owner.id,
            owner_id=owner.id,
            uploader_id=owner.id,
            status='pending',
            created_at=datetime.utcnow()
        )
        db.session.add(asset)
        db.session.commit()
        return asset.id


def test_asset_approval_notifies_uploader(
    client, app, auth_header, admin_header, pending_asset
):
    response = client.post(
        f'/api/assets/{pending_asset}/approve',
        headers=admin_header,
        json={'action': 'approve'}
    )
    assert response.status_code == 200

    notifications = client.get('/api/notifications', headers=auth_header)
    assert notifications.status_code == 200
    items = notifications.get_json()['data']['items']
    titles = [item['title'] for item in items]
    assert '资产审核通过' in titles

    event = next(item for item in items if item['title'] == '资产审核通过')
    assert event['link'] == f'/assets/{pending_asset}'
    assert event['read'] is False
