"""
园林模块测试
"""
import pytest


class TestGarden:
    """园林测试类"""

    def test_garden_list_empty(self, client):
        """测试空园林列表"""
        response = client.get('/api/gardens')

        assert response.status_code == 200
        data = response.get_json()
        assert data['code'] == 200
        assert isinstance(data['data'], list)

    def test_garden_list_with_data(self, client, sample_garden):
        """测试有数据的园林列表"""
        response = client.get('/api/gardens')

        assert response.status_code == 200
        data = response.get_json()
        assert data['code'] == 200
        assert len(data['data']) >= 1

    def test_garden_detail(self, client, sample_garden):
        """测试园林详情"""
        response = client.get(f'/api/gardens/{sample_garden}')

        assert response.status_code == 200
        data = response.get_json()
        assert data['code'] == 200
        assert data['data']['name'] == '拙政园'
        assert data['data']['code'] == 'ZY'

    def test_garden_detail_not_found(self, client):
        """测试不存在的园林详情"""
        response = client.get('/api/gardens/999')

        assert response.status_code == 404
        data = response.get_json()
        assert data['code'] == 404

    def test_garden_stats(self, client, auth_header, sample_garden):
        """测试园林统计"""
        response = client.get(
            f'/api/gardens/{sample_garden}/stats',
            headers=auth_header
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data['code'] == 200
        assert 'stats' in data['data']
        assert 'total_assets' in data['data']['stats']

    def test_garden_stats_unauthorized(self, client, sample_garden):
        """测试未认证访问园林统计"""
        response = client.get(f'/api/gardens/{sample_garden}/stats')

        assert response.status_code == 401

    def test_garden_stats_not_found(self, client, auth_header):
        """测试不存在园林的统计"""
        response = client.get(
            '/api/gardens/999/stats',
            headers=auth_header
        )

        assert response.status_code == 404
