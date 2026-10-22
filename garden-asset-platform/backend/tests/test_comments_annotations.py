"""资产评论与图纸/影像区域标注测试

覆盖：评论创建/列表/回复/编辑/删除权限、未发布资产可见性；
标注创建/坐标校验/当前版本过滤/历史版本/状态过滤/
内容与状态的分级权限/删除权限/版本绑定。
"""
import uuid

import pytest

from app.extensions import db
from app.models.annotation import AssetAnnotation
from app.models.asset import Asset, AssetVersion
from app.models.comment import AssetComment
from app.models.user import User


def register_and_login(client, username):
    password = 'test1234'
    response = client.post('/api/register', json={
        'username': username,
        'password': password,
        'email': f'{username}@test.com'
    })
    assert response.status_code in (200, 201), response.get_json()
    response = client.post('/api/login', json={
        'username': username,
        'password': password
    })
    assert response.status_code == 200, response.get_json()
    token = response.get_json()['data']['access_token']
    return {'Authorization': f'Bearer {token}'}


def get_user_id(username):
    return User.query.filter_by(username=username).first().id


def create_asset(owner_id, *, status='published', asset_type='image',
                 version_count=1, title='测试资产'):
    """直接入库创建资产与版本，返回 (asset_id, [version_ids])"""
    asset = Asset(
        asset_code=f'ZY-TST-{uuid.uuid4().hex[:12].upper()}',
        title=title,
        asset_type=asset_type,
        creator_id=owner_id,
        owner_id=owner_id,
        uploader_id=owner_id,
        status=status,
    )
    db.session.add(asset)
    db.session.flush()

    version_ids = []
    for index in range(1, version_count + 1):
        version = AssetVersion(
            asset_id=asset.id,
            version_no=index,
            file_path=f'/tmp/{uuid.uuid4().hex}.jpg',
            file_name=f'v{index}.jpg',
        )
        db.session.add(version)
        db.session.flush()
        version_ids.append(version.id)

    db.session.commit()
    return asset.id, version_ids


def set_asset_status(asset_id, status):
    asset = db.session.get(Asset, asset_id)
    asset.status = status
    db.session.commit()


def annotation_payload(**overrides):
    payload = {
        'x': 0.1,
        'y': 0.2,
        'width': 0.2,
        'height': 0.3,
        'title': '屋檐开裂',
        'content': '需要现场复核',
        'annotation_type': 'issue',
    }
    payload.update(overrides)
    return payload


@pytest.fixture
def owner_header(client):
    return register_and_login(client, 'comment_owner')


@pytest.fixture
def other_header(client):
    return register_and_login(client, 'comment_other')


@pytest.fixture
def third_header(client):
    return register_and_login(client, 'comment_third')


# ---------------------------------------------------------------- 评论

def test_comment_create_list_reply_edit_delete(
    client, owner_header, other_header, admin_header
):
    owner_id = get_user_id('comment_owner')
    asset_id, _ = create_asset(owner_id)
    base = f'/api/assets/{asset_id}/comments'

    # 发表评论（首尾空白被去除）
    response = client.post(base, json={'content': '  这个构图很好  '}, headers=other_header)
    assert response.status_code == 200, response.get_json()
    first = response.get_json()['data']
    assert first['content'] == '这个构图很好'
    assert first['author_name']
    assert first['author_role'] == 'user'
    assert first['is_own'] is True
    assert first['can_delete'] is True
    assert first['parent_id'] is None
    assert first['reply_to_name'] is None
    assert first['created_at']

    # 回复
    response = client.post(
        base,
        json={'content': '同意，色调也舒服', 'parent_id': first['id']},
        headers=owner_header
    )
    assert response.status_code == 200, response.get_json()
    reply = response.get_json()['data']
    assert reply['parent_id'] == first['id']
    assert reply['reply_to_name'] == first['author_name']
    assert reply['is_own'] is True

    # 列表按 created_at 升序
    response = client.get(base, headers=other_header)
    assert response.status_code == 200
    data = response.get_json()['data']
    assert data['total'] == 2
    assert [item['id'] for item in data['items']] == [first['id'], reply['id']]
    assert data['items'][0]['is_own'] is True
    assert data['items'][1]['is_own'] is False
    assert data['items'][1]['reply_to_name'] == first['author_name']

    # 分页参数生效
    data = client.get(f'{base}?page=2&per_page=1', headers=other_header).get_json()['data']
    assert data['total'] == 2
    assert data['page'] == 2
    assert data['per_page'] == 1
    assert data['pages'] == 2
    assert [item['id'] for item in data['items']] == [reply['id']]

    # 作者编辑评论
    response = client.put(
        f'{base}/{first["id"]}', json={'content': '改一下措辞'}, headers=other_header
    )
    assert response.status_code == 200
    assert response.get_json()['data']['content'] == '改一下措辞'

    # 非作者（含资产所有者）不能编辑
    assert client.put(
        f'{base}/{first["id"]}', json={'content': 'x'}, headers=owner_header
    ).status_code == 403

    # 内容校验
    assert client.post(base, json={'content': '   '}, headers=other_header).status_code == 400
    assert client.post(
        base, json={'content': 'x' * 2001}, headers=other_header
    ).status_code == 400
    assert client.put(
        f'{base}/{first["id"]}', json={'content': ''}, headers=other_header
    ).status_code == 400
    # 父评论必须属于同一资产
    other_asset_id, _ = create_asset(owner_id, title='另一个资产')
    assert client.post(
        f'/api/assets/{other_asset_id}/comments',
        json={'content': '跨资产回复', 'parent_id': first['id']},
        headers=owner_header
    ).status_code == 400

    # 非作者不能删除；管理员可删除
    assert client.delete(f'{base}/{first["id"]}', headers=owner_header).status_code == 403
    extra = client.post(
        base, json={'content': '临时评论'}, headers=other_header
    ).get_json()['data']
    assert client.delete(f'{base}/{extra["id"]}', headers=admin_header).status_code == 200

    # 作者软删除，重复删除保持幂等
    assert client.delete(f'{base}/{first["id"]}', headers=other_header).status_code == 200
    assert client.delete(f'{base}/{first["id"]}', headers=other_header).status_code == 200

    # 父评论已删除：回复仍在，但 reply_to_name 不再暴露作者
    data = client.get(base, headers=other_header).get_json()['data']
    assert data['total'] == 1
    assert data['items'][0]['id'] == reply['id']
    assert data['items'][0]['reply_to_name'] is None

    with db.session.no_autoflush:
        deleted = db.session.get(AssetComment, first['id'])
        assert deleted.is_deleted is True


def test_comment_visibility_matches_asset(
    client, owner_header, other_header, admin_header
):
    owner_id = get_user_id('comment_owner')
    asset_id, _ = create_asset(owner_id, status='draft')
    base = f'/api/assets/{asset_id}/comments'

    # 草稿：非所有者不可见
    assert client.get(base, headers=other_header).status_code == 404
    assert client.post(
        base, json={'content': '偷偷评论'}, headers=other_header
    ).status_code == 404
    # 所有者与管理员可见
    assert client.get(base, headers=owner_header).status_code == 200
    assert client.post(
        base, json={'content': '自己的草稿'}, headers=owner_header
    ).status_code == 200
    assert client.get(base, headers=admin_header).status_code == 200

    # 发布后所有登录用户可见
    set_asset_status(asset_id, 'published')
    assert client.get(base, headers=other_header).status_code == 200
    assert client.post(
        base, json={'content': '公开讨论'}, headers=other_header
    ).status_code == 200

    # 已删除：所有者不可见，管理员可见
    set_asset_status(asset_id, 'deleted')
    assert client.get(base, headers=owner_header).status_code == 404
    assert client.post(
        base, json={'content': 'x'}, headers=owner_header
    ).status_code == 404
    assert client.get(base, headers=admin_header).status_code == 200

    # 未登录
    assert client.get(base).status_code == 401


# ---------------------------------------------------------------- 标注

def test_annotation_create_and_coordinate_validation(
    client, owner_header, other_header
):
    owner_id = get_user_id('comment_owner')
    asset_id, version_ids = create_asset(owner_id, version_count=1)
    base = f'/api/assets/{asset_id}/annotations'

    response = client.post(base, json=annotation_payload(), headers=other_header)
    assert response.status_code == 200, response.get_json()
    created = response.get_json()['data']
    assert created['version_id'] == version_ids[0]
    assert created['version_no'] == 1
    assert created['status'] == 'open'
    assert created['author_name']
    assert created['is_own'] is True
    assert created['can_edit'] is True
    assert created['can_resolve'] is False  # 作者不是资产所有者
    assert created['can_delete'] is True
    assert created['resolved_at'] is None

    # 坐标/字段校验
    invalid_payloads = [
        annotation_payload(x=1.2),
        annotation_payload(y=-0.1),
        annotation_payload(width=0.004),       # 必须大于 0.004
        annotation_payload(height=0.003),
        annotation_payload(x=0.9, width=0.2),  # x + width > 1.001
        annotation_payload(y=0.9, height=0.2),  # y + height > 1
        annotation_payload(width='abc'),
    ]
    for payload in invalid_payloads:
        assert client.post(base, json=payload, headers=other_header).status_code == 400

    no_width = annotation_payload()
    del no_width['width']
    assert client.post(base, json=no_width, headers=other_header).status_code == 400

    assert client.post(
        base, json=annotation_payload(title=''), headers=other_header
    ).status_code == 400
    assert client.post(
        base, json=annotation_payload(title='x' * 101), headers=other_header
    ).status_code == 400
    assert client.post(
        base, json=annotation_payload(annotation_type='bad'), headers=other_header
    ).status_code == 400
    assert client.post(
        base, json=annotation_payload(content='x' * 2001), headers=other_header
    ).status_code == 400

    # 版本必须属于该资产
    other_asset_id, other_versions = create_asset(owner_id, title='其他影像')
    assert client.post(
        base,
        json=annotation_payload(version_id=other_versions[0]),
        headers=other_header
    ).status_code == 400

    # 非图纸/影像类型：创建 400，列表为空不报错
    document_id, _ = create_asset(owner_id, asset_type='document')
    assert client.post(
        f'/api/assets/{document_id}/annotations',
        json=annotation_payload(),
        headers=owner_header
    ).status_code == 400
    response = client.get(
        f'/api/assets/{document_id}/annotations', headers=owner_header
    )
    assert response.status_code == 200
    assert response.get_json()['data']['items'] == []

    # 未登录
    assert client.get(base).status_code == 401


def test_annotation_version_filtering_and_status(
    client, owner_header, other_header
):
    owner_id = get_user_id('comment_owner')
    asset_id, version_ids = create_asset(owner_id, version_count=2)
    v1, v2 = version_ids
    base = f'/api/assets/{asset_id}/annotations'

    current = client.post(
        base, json=annotation_payload(title='当前版本标注'), headers=other_header
    ).get_json()['data']
    assert current['version_id'] == v2

    historical = client.post(
        base,
        json=annotation_payload(title='历史版本标注', version_id=v1),
        headers=other_header
    ).get_json()['data']
    assert historical['version_id'] == v1
    assert historical['version_no'] == 1

    # 默认只返回当前版本
    data = client.get(base, headers=other_header).get_json()['data']
    assert data['version_filter'] == 'current'
    assert data['current_version_id'] == v2
    assert data['current_version_no'] == 2
    assert data['total'] == 1
    assert [item['id'] for item in data['items']] == [current['id']]

    # all=1 返回全部版本
    data = client.get(f'{base}?all=1', headers=other_header).get_json()['data']
    assert data['version_filter'] == 'all'
    assert data['total'] == 2
    assert {item['version_id'] for item in data['items']} == {v1, v2}

    # 指定历史版本
    data = client.get(f'{base}?version_id={v1}', headers=other_header).get_json()['data']
    assert data['version_filter'] == str(v1)
    assert data['total'] == 1
    assert [item['id'] for item in data['items']] == [historical['id']]

    # 其他资产的版本按不存在处理
    other_asset_id, other_versions = create_asset(owner_id, title='其他影像')
    assert client.get(
        f'{base}?version_id={other_versions[0]}', headers=owner_header
    ).status_code == 404

    # 状态过滤：所有者解决当前版本标注
    assert client.put(
        f'{base}/{current["id"]}', json={'status': 'resolved'}, headers=owner_header
    ).status_code == 200
    data = client.get(f'{base}?status=resolved', headers=other_header).get_json()['data']
    assert data['total'] == 1
    assert data['items'][0]['id'] == current['id']
    data = client.get(f'{base}?status=open', headers=other_header).get_json()['data']
    assert data['total'] == 0
    data = client.get(f'{base}?all=1&status=open', headers=other_header).get_json()['data']
    assert [item['id'] for item in data['items']] == [historical['id']]
    assert client.get(
        f'{base}?status=done', headers=other_header
    ).status_code == 400


def test_annotation_edit_and_resolve_permissions(
    client, owner_header, other_header, third_header, admin_header
):
    owner_id = get_user_id('comment_owner')
    asset_id, _ = create_asset(owner_id)
    base = f'/api/assets/{asset_id}/annotations'

    created = client.post(
        base, json=annotation_payload(), headers=other_header
    ).get_json()['data']
    annotation_id = created['id']
    detail = f'{base}/{annotation_id}'

    # 作者修改内容
    response = client.put(
        detail,
        json={'title': '新标题', 'content': '补充说明', 'annotation_type': 'suggestion'},
        headers=other_header
    )
    assert response.status_code == 200, response.get_json()
    updated = response.get_json()['data']
    assert updated['title'] == '新标题'
    assert updated['content'] == '补充说明'
    assert updated['annotation_type'] == 'suggestion'

    # 作者不能改状态
    assert client.put(
        detail, json={'status': 'resolved'}, headers=other_header
    ).status_code == 403
    # 所有者不能改内容
    assert client.put(
        detail, json={'title': '所有者改标题'}, headers=owner_header
    ).status_code == 403
    assert client.put(
        detail, json={'content': '所有者改说明'}, headers=owner_header
    ).status_code == 403
    # 无关用户既不能改内容也不能改状态
    assert client.put(
        detail, json={'title': 'x'}, headers=third_header
    ).status_code == 403
    assert client.put(
        detail, json={'status': 'resolved'}, headers=third_header
    ).status_code == 403

    # 所有者解决
    response = client.put(detail, json={'status': 'resolved'}, headers=owner_header)
    assert response.status_code == 200, response.get_json()
    resolved = response.get_json()['data']
    assert resolved['status'] == 'resolved'
    assert resolved['resolved_at']
    assert resolved['resolver_name']
    with db.session.no_autoflush:
        annotation = db.session.get(AssetAnnotation, annotation_id)
        assert annotation.resolved_by == owner_id
        assert annotation.resolved_at is not None

    # 所有者重新打开，解决信息清空
    response = client.put(detail, json={'status': 'open'}, headers=owner_header)
    assert response.status_code == 200
    reopened = response.get_json()['data']
    assert reopened['status'] == 'open'
    assert reopened['resolved_at'] is None
    assert reopened['resolver_name'] is None
    with db.session.no_autoflush:
        annotation = db.session.get(AssetAnnotation, annotation_id)
        assert annotation.resolved_by is None
        assert annotation.resolved_at is None

    # 管理员（非作者非所有者）可以改内容与状态
    assert client.put(
        detail, json={'title': '管理员改标题'}, headers=admin_header
    ).status_code == 200
    response = client.put(detail, json={'status': 'resolved'}, headers=admin_header)
    assert response.status_code == 200
    assert response.get_json()['data']['status'] == 'resolved'

    # 非法状态 / 空更新
    assert client.put(detail, json={'status': 'done'}, headers=admin_header).status_code == 400
    assert client.put(detail, json={}, headers=admin_header).status_code == 400


def test_annotation_delete_permissions_and_version_binding(
    client, owner_header, other_header, third_header, admin_header
):
    owner_id = get_user_id('comment_owner')
    asset_id, version_ids = create_asset(owner_id, version_count=2)
    base = f'/api/assets/{asset_id}/annotations'

    # 绑定历史版本
    created = client.post(
        base, json=annotation_payload(version_id=version_ids[0]), headers=other_header
    ).get_json()['data']
    assert created['version_id'] == version_ids[0]
    with db.session.no_autoflush:
        stored = db.session.get(AssetAnnotation, created['id'])
        assert stored.version_id == version_ids[0]

    # 无关用户不能删除
    assert client.delete(
        f'{base}/{created["id"]}', headers=third_header
    ).status_code == 403

    # 资产所有者可以删除他人标注
    assert client.delete(
        f'{base}/{created["id"]}', headers=owner_header
    ).status_code == 200
    with db.session.no_autoflush:
        assert db.session.get(AssetAnnotation, created['id']) is None

    # 管理员可以删除
    second = client.post(
        base, json=annotation_payload(), headers=third_header
    ).get_json()['data']
    assert client.delete(
        f'{base}/{second["id"]}', headers=admin_header
    ).status_code == 200

    # 作者可以删除自己的标注
    third = client.post(
        base, json=annotation_payload(), headers=other_header
    ).get_json()['data']
    assert client.delete(
        f'{base}/{third["id"]}', headers=other_header
    ).status_code == 200

    # 标注与资产不匹配 → 404
    other_asset_id, other_versions = create_asset(owner_id, title='其他影像')
    assert client.delete(
        f'/api/assets/{other_asset_id}/annotations/{created["id"]}',
        headers=owner_header
    ).status_code == 404


def test_annotation_visibility_matches_asset(
    client, owner_header, other_header, admin_header
):
    owner_id = get_user_id('comment_owner')
    asset_id, _ = create_asset(owner_id, status='draft')
    base = f'/api/assets/{asset_id}/annotations'

    # 草稿：非所有者不可见
    assert client.get(base, headers=other_header).status_code == 404
    assert client.post(
        base, json=annotation_payload(), headers=other_header
    ).status_code == 404
    assert client.get(base, headers=owner_header).status_code == 200
    assert client.post(
        base, json=annotation_payload(), headers=owner_header
    ).status_code == 200

    # 发布后所有登录用户可见
    set_asset_status(asset_id, 'published')
    assert client.get(base, headers=other_header).status_code == 200
    assert client.post(
        base, json=annotation_payload(), headers=other_header
    ).status_code == 200

    # 已删除：所有者不可见，管理员可见
    set_asset_status(asset_id, 'deleted')
    assert client.get(base, headers=owner_header).status_code == 404
    assert client.get(base, headers=admin_header).status_code == 200


def test_annotation_without_versions_binds_null_version(client, owner_header):
    owner_id = get_user_id('comment_owner')
    asset_id, version_ids = create_asset(owner_id, version_count=0)
    assert version_ids == []
    base = f'/api/assets/{asset_id}/annotations'

    created = client.post(
        base, json=annotation_payload(), headers=owner_header
    ).get_json()['data']
    assert created['version_id'] is None
    assert created['version_no'] is None

    data = client.get(base, headers=owner_header).get_json()['data']
    assert data['current_version_id'] is None
    assert data['current_version_no'] is None
    assert [item['id'] for item in data['items']] == [created['id']]


def test_comment_creates_notification_for_asset_owner(
    client, owner_header, other_header
):
    owner_id = get_user_id('comment_owner')
    asset_id, _ = create_asset(owner_id, title='带评论通知的资产')

    response = client.post(
        f'/api/assets/{asset_id}/comments',
        json={'content': '这张图的注释需要补一版'},
        headers=other_header
    )
    assert response.status_code == 200

    notifications = client.get('/api/notifications', headers=owner_header)
    assert notifications.status_code == 200
    items = notifications.get_json()['data']['items']
    comment_items = [
        item for item in items
        if '评论了你的资产' in item['title']
    ]
    assert comment_items
    assert comment_items[0]['link'] == f'/assets/{asset_id}?tab=comments'
