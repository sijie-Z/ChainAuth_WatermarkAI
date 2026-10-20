"""
授权模块测试
"""
import pytest


class TestLicense:
    """授权测试类"""

    def test_apply_missing_asset_id(self, client, auth_header):
        """测试申请授权缺少资产ID"""
        response = client.post('/api/license/apply',
            json={'license_type': 'personal', 'purpose': '学习'},
            headers=auth_header
        )

        assert response.status_code == 400
        data = response.get_json()
        assert '资产ID' in data['message']

    def test_apply_asset_not_found(self, client, auth_header):
        """测试申请授权资产不存在"""
        response = client.post('/api/license/apply',
            json={'asset_id': 'nonexistent-id', 'license_type': 'personal'},
            headers=auth_header
        )

        assert response.status_code == 404

    def test_apply_success(self, client, auth_header, sample_asset):
        """测试成功提交授权申请"""
        response = client.post('/api/license/apply',
            json={
                'asset_id': sample_asset,
                'license_type': 'personal',
                'purpose': '学术研究',
                'valid_period': '1y',
                'contact': '张三'
            },
            headers=auth_header
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data['code'] == 200
        assert 'application_code' in data['data']

    def test_apply_unauthorized(self, client, sample_asset):
        """测试未认证申请授权"""
        response = client.post('/api/license/apply',
            json={'asset_id': sample_asset, 'license_type': 'personal'}
        )

        assert response.status_code == 401

    def test_pending_list_unauthorized(self, client):
        """测试未认证访问待审批列表"""
        response = client.get('/api/license/pending')

        assert response.status_code == 401

    def test_pending_list_normal_user(self, client, auth_header):
        """测试普通用户访问待审批列表（应无权限）"""
        response = client.get('/api/license/pending',
            headers=auth_header
        )

        assert response.status_code == 403

    def test_my_licenses_empty(self, client, auth_header):
        """测试我的授权列表为空"""
        response = client.get('/api/license/my',
            headers=auth_header
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data['code'] == 200
        assert data['data']['total'] == 0

    def test_approved_list(self, client, admin_header):
        """测试已审批列表（仅审批/管理员可访问）"""
        response = client.get('/api/license/approved',
            headers=admin_header
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data['code'] == 200
        assert 'items' in data['data']
        assert 'total' in data['data']

    def test_approved_list_forbidden_for_user(self, client, auth_header):
        """普通用户不能拉取全平台授权记录"""
        response = client.get('/api/license/approved', headers=auth_header)
        assert response.status_code == 403

    def test_approve_not_found(self, client, admin_header):
        """测试审批不存在的申请"""
        response = client.post('/api/license/approve/999',
            json={'action': 'approve'},
            headers=admin_header
        )

        assert response.status_code == 404

    def test_dual_approval_workflow(self, client, auth_header, admin_header, sample_asset):
        """测试双重审批流程：adm1审批 → adm2审批 → 生成授权"""
        # 1. 普通用户提交申请
        resp = client.post('/api/license/apply',
            json={
                'asset_id': sample_asset,
                'license_type': 'personal',
                'purpose': '学术研究',
                'valid_period': '1y',
                'contact': 'test@test.com'
            },
            headers=auth_header
        )
        assert resp.status_code == 200
        app_id = resp.get_json()['data']['id']

        # 2. 管理员第一步审批（adm1）
        resp = client.post(f'/api/license/approve/{app_id}',
            json={'action': 'approve', 'comment': '资产审核通过'},
            headers=admin_header
        )
        assert resp.status_code == 200

        # 3. 管理员第二步审批（adm2）
        resp = client.post(f'/api/license/approve/{app_id}',
            json={'action': 'approve', 'comment': '授权审核通过'},
            headers=admin_header
        )
        assert resp.status_code == 200

        # 4. 验证授权已创建
        resp = client.get('/api/license/my', headers=auth_header)
        assert resp.status_code == 200

    def test_reject_workflow(self, client, auth_header, admin_header, sample_asset):
        """测试拒绝审批流程"""
        # 提交申请
        resp = client.post('/api/license/apply',
            json={
                'asset_id': sample_asset,
                'license_type': 'commercial',
                'purpose': '商业用途',
                'contact': 'test@test.com'
            },
            headers=auth_header
        )
        app_id = resp.get_json()['data']['id']

        # 拒绝申请
        resp = client.post(f'/api/license/approve/{app_id}',
            json={'action': 'reject', 'comment': '不符合授权条件'},
            headers=admin_header
        )
        assert resp.status_code == 200
