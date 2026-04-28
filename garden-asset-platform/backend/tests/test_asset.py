"""
资产模块测试
"""
import pytest


class TestAsset:
    """资产测试类"""

    def test_get_assets_list(self, client, auth_header):
        """测试获取资产列表"""
        response = client.get('/api/assets', headers=auth_header)

        assert response.status_code == 200
        data = response.get_json()
        assert 'items' in data['data'] or 'data' in data

    def test_get_assets_unauthorized(self, client):
        """测试未认证获取资产列表"""
        response = client.get('/api/assets')

        assert response.status_code == 401

    def test_get_asset_detail_not_found(self, client, auth_header):
        """测试获取不存在的资产"""
        response = client.get('/api/assets/nonexistent-id', headers=auth_header)

        assert response.status_code == 404

    def test_asset_pagination(self, client, auth_header):
        """测试资产分页"""
        response = client.get('/api/assets?page=1&per_page=10', headers=auth_header)

        assert response.status_code == 200