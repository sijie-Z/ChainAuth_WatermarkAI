"""
授权接口边界测试

覆盖两级审批的角色/归属权限、有效期校验、状态筛选与分页边界。
"""
import uuid
from datetime import datetime

import pytest

from app.extensions import db
from app.models.asset import Asset
from app.models.license import License, LicenseApplication
from app.models.user import User


def apply_license(client, headers, asset_id, **extra):
    payload = {
        'asset_id': asset_id,
        'license_type': 'personal',
        'purpose': '边界测试',
    }
    payload.update(extra)
    return client.post('/api/license/apply', json=payload, headers=headers)


def approve(client, headers, application_id, action='approve', **extra):
    payload = {'action': action}
    payload.update(extra)
    return client.post(f'/api/license/approve/{application_id}', json=payload, headers=headers)


def pending_ids(client, headers):
    return {item['id'] for item in client.get('/api/license/pending', headers=headers).get_json()['data']}


def create_draft_asset(app, owner_id):
    with app.app_context():
        asset = Asset(
            asset_code=f'LIC-{uuid.uuid4().hex[:10].upper()}',
            title='未发布授权测试资产',
            asset_type='image',
            file_format='PNG',
            creator_id=owner_id,
            uploader_id=owner_id,
            owner_id=owner_id,
            status='draft',
        )
        db.session.add(asset)
        db.session.commit()
        return asset.id


def complete_approval(client, auth_header, sample_asset, adm1_header, adm2_header, **apply_extra):
    response = apply_license(client, auth_header, sample_asset, **apply_extra)
    assert response.status_code == 200, response.get_json()
    application_id = response.get_json()['data']['id']
    assert approve(client, adm1_header, application_id).status_code == 200
    assert approve(client, adm2_header, application_id).status_code == 200
    return application_id


class TestApplyBranches:
    def test_rejects_unpublished_asset(self, client, auth_header, app):
        owner_id = client.get('/api/user/current', headers=auth_header).get_json()['data']['id']
        draft_id = create_draft_asset(app, owner_id)

        response = apply_license(client, auth_header, draft_id)

        assert response.status_code == 400
        assert '已发布' in response.get_json()['message']

    def test_rejects_duplicate_pending_application(self, client, auth_header, sample_asset):
        assert apply_license(client, auth_header, sample_asset).status_code == 200

        response = apply_license(client, auth_header, sample_asset)

        assert response.status_code == 400
        assert '待审批' in response.get_json()['message']

    @pytest.mark.parametrize('period, expected', [
        ('1m', 1),
        ('3m', 3),
        ('6m', 6),
        ('1y', 12),
        ('permanent', None),
        ('unknown-period', None),
    ])
    def test_valid_period_mapping(self, client, auth_header, sample_asset, period, expected):
        response = apply_license(client, auth_header, sample_asset, valid_period=period)

        assert response.status_code == 200
        assert response.get_json()['data']['duration_months'] == expected


class TestPendingList:
    def test_role_specific_queues(self, client, auth_header, adm1_header, adm2_header, admin_header, sample_asset):
        response = apply_license(client, auth_header, sample_asset)
        application_id = response.get_json()['data']['id']

        # 一级审批：adm1 与 admin 可见，adm2 不可见
        assert application_id in pending_ids(client, adm1_header)
        assert application_id not in pending_ids(client, adm2_header)
        assert application_id in pending_ids(client, admin_header)

        assert approve(client, adm1_header, application_id).status_code == 200

        # 二级审批：adm2 与 admin 可见，adm1 不再可见
        assert application_id in pending_ids(client, adm2_header)
        assert application_id in pending_ids(client, admin_header)
        assert application_id not in pending_ids(client, adm1_header)

    def test_hides_application_assigned_to_another_reviewer(self, client, auth_header, adm1_header, sample_asset, app):
        application_id = apply_license(client, auth_header, sample_asset).get_json()['data']['id']
        with app.app_context():
            other = User(username='other_adm1', email='other_adm1@test.com', role='adm1')
            other.set_password('pass1234')
            db.session.add(other)
            db.session.commit()
            application = db.session.get(LicenseApplication, application_id)
            application.adm1_reviewer_id = other.id
            db.session.commit()

        assert application_id not in pending_ids(client, adm1_header)

    def test_second_level_reviewer_assignment_is_enforced(self, client, auth_header, adm1_header, adm2_header, sample_asset, app):
        application_id = apply_license(client, auth_header, sample_asset).get_json()['data']['id']
        assert approve(client, adm1_header, application_id).status_code == 200

        with app.app_context():
            other = User(username='other_adm2', email='other_adm2@test.com', role='adm2')
            other.set_password('pass1234')
            db.session.add(other)
            db.session.commit()
            application = db.session.get(LicenseApplication, application_id)
            application.adm2_reviewer_id = other.id
            db.session.commit()

        response = approve(client, adm2_header, application_id)

        assert response.status_code == 403
        assert '其他审批人' in response.get_json()['message']


class TestApproveBranches:
    def test_rejects_invalid_valid_until_format(self, client, auth_header, adm1_header, sample_asset):
        application_id = apply_license(client, auth_header, sample_asset).get_json()['data']['id']

        response = approve(client, adm1_header, application_id, valid_until='not-a-date')

        assert response.status_code == 400
        assert '有效期格式无效' in response.get_json()['message']

    def test_rejects_past_valid_until(self, client, auth_header, adm1_header, sample_asset):
        application_id = apply_license(client, auth_header, sample_asset).get_json()['data']['id']

        response = approve(client, adm1_header, application_id, valid_until='2000-01-01T00:00:00')

        assert response.status_code == 400
        assert '晚于当前时间' in response.get_json()['message']

    def test_adm2_cannot_act_before_first_level_approval(self, client, auth_header, adm2_header, sample_asset):
        application_id = apply_license(client, auth_header, sample_asset).get_json()['data']['id']

        response = approve(client, adm2_header, application_id)

        assert response.status_code == 400
        assert '不可审批' in response.get_json()['message']

    def test_first_level_reviewer_assignment_is_enforced(self, client, auth_header, adm1_header, sample_asset, app):
        application_id = apply_license(client, auth_header, sample_asset).get_json()['data']['id']
        with app.app_context():
            other = User(username='assigned_adm1', email='assigned_adm1@test.com', role='adm1')
            other.set_password('pass1234')
            db.session.add(other)
            db.session.commit()
            application = db.session.get(LicenseApplication, application_id)
            application.adm1_reviewer_id = other.id
            db.session.commit()

        response = approve(client, adm1_header, application_id)

        assert response.status_code == 403
        assert '其他审批人' in response.get_json()['message']

    def test_second_level_approval_with_explicit_valid_until(
        self, client, auth_header, adm1_header, adm2_header, sample_asset
    ):
        application_id = apply_license(client, auth_header, sample_asset, valid_period='1y').get_json()['data']['id']
        assert approve(client, adm1_header, application_id).status_code == 200

        response = approve(client, adm2_header, application_id, valid_until='2099-01-01T00:00:00Z')

        assert response.status_code == 200
        licenses = client.get('/api/license/my', headers=auth_header).get_json()['data']
        assert licenses['total'] == 1
        record = licenses['items'][0]
        assert record['end_time'].startswith('2099-01-01T00:00:00')
        assert record['status'] == 'active'

    def test_second_level_approval_derives_end_time_from_duration(
        self, client, auth_header, adm1_header, adm2_header, sample_asset
    ):
        application_id = apply_license(client, auth_header, sample_asset, valid_period='3m').get_json()['data']['id']
        assert approve(client, adm1_header, application_id).status_code == 200
        assert approve(client, adm2_header, application_id).status_code == 200

        record = client.get('/api/license/my', headers=auth_header).get_json()['data']['items'][0]
        start = datetime.fromisoformat(record['start_time'])
        end = datetime.fromisoformat(record['end_time'])
        assert (end - start).days == 90

    def test_second_level_rejection_creates_no_license(
        self, client, auth_header, adm1_header, adm2_header, sample_asset, app
    ):
        application_id = apply_license(client, auth_header, sample_asset).get_json()['data']['id']
        assert approve(client, adm1_header, application_id).status_code == 200

        response = approve(client, adm2_header, application_id, action='reject', comment='不符合条件')

        assert response.status_code == 200
        with app.app_context():
            application = db.session.get(LicenseApplication, application_id)
            assert application.status == 'rejected'
            assert License.query.count() == 0


class TestLicenseQueries:
    def test_approved_list_rejects_invalid_status(self, client, admin_header):
        response = client.get('/api/license/approved?status=zombie', headers=admin_header)

        assert response.status_code == 400
        assert '无效的状态筛选' in response.get_json()['message']

    def test_approved_list_filters_and_clamps_pagination(
        self, client, auth_header, adm1_header, adm2_header, admin_header, sample_asset
    ):
        complete_approval(client, auth_header, sample_asset, adm1_header, adm2_header)

        response = client.get(
            '/api/license/approved?status=active&page=0&per_page=1000',
            headers=admin_header,
        )

        assert response.status_code == 200
        data = response.get_json()['data']
        assert data['total'] == 1
        assert data['items'][0]['licensee_name'] == 'testuser'
        assert data['items'][0]['licensor_name'] == 'testuser'

    def test_my_licenses_rejects_invalid_status(self, client, auth_header):
        response = client.get('/api/license/my?status=zombie', headers=auth_header)

        assert response.status_code == 400

    def test_my_licenses_filters_active(self, client, auth_header, adm1_header, adm2_header, sample_asset):
        complete_approval(client, auth_header, sample_asset, adm1_header, adm2_header)

        response = client.get('/api/license/my?status=active', headers=auth_header)

        assert response.status_code == 200
        assert response.get_json()['data']['total'] == 1

    def test_my_applications_rejects_invalid_status(self, client, auth_header):
        response = client.get('/api/license/my-applications?status=zombie', headers=auth_header)

        assert response.status_code == 400

    def test_my_applications_status_filter(self, client, auth_header, adm1_header, adm2_header, sample_asset):
        application_id = apply_license(client, auth_header, sample_asset).get_json()['data']['id']

        pending = client.get('/api/license/my-applications?status=pending', headers=auth_header)
        assert pending.status_code == 200
        assert any(item['id'] == application_id for item in pending.get_json()['data']['items'])

        assert approve(client, adm1_header, application_id).status_code == 200
        assert approve(client, adm2_header, application_id).status_code == 200

        approved = client.get('/api/license/my-applications?status=approved', headers=auth_header)
        assert approved.status_code == 200
        assert any(item['id'] == application_id for item in approved.get_json()['data']['items'])
