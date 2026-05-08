"""
区块链模块测试
"""
import pytest


class TestBlockchain:
    """区块链测试类"""

    def test_blockchain_status(self, client):
        """测试区块链连接状态"""
        response = client.get('/api/blockchain/status')

        assert response.status_code == 200
        data = response.get_json()
        assert data['code'] == 200
        assert 'connected' in data['data']
        assert 'simulated' in data['data']

    def test_register_missing_asset_id(self, client, auth_header):
        """测试存证缺少资产ID"""
        response = client.post('/api/blockchain/register',
            json={},
            headers=auth_header
        )

        assert response.status_code == 400
        data = response.get_json()
        assert '资产ID' in data['message']

    def test_register_asset_not_found(self, client, auth_header):
        """测试存证资产不存在"""
        response = client.post('/api/blockchain/register',
            json={'asset_id': 'nonexistent-id'},
            headers=auth_header
        )

        assert response.status_code == 404

    def test_register_unauthorized(self, client, sample_asset):
        """测试未认证存证"""
        response = client.post('/api/blockchain/register',
            json={'asset_id': sample_asset}
        )

        assert response.status_code == 401

    def test_verify_asset_not_found(self, client):
        """测试验证不存在的资产"""
        response = client.get('/api/blockchain/verify/nonexistent-id')

        assert response.status_code == 404

    def test_verify_by_watermark_missing_id(self, client):
        """测试通过水印ID验证缺少ID"""
        response = client.post('/api/blockchain/verify',
            json={}
        )

        assert response.status_code == 400

    def test_certificate_not_found(self, client):
        """测试获取不存在的证书"""
        response = client.get('/api/blockchain/certificate/nonexistent-cert')

        assert response.status_code == 404

    def test_history_all(self, client):
        """测试获取所有存证历史"""
        response = client.get('/api/blockchain/history')

        assert response.status_code == 200
        data = response.get_json()
        assert data['code'] == 200
        assert isinstance(data['data'], list)

    def test_history_asset_not_found(self, client):
        """测试获取不存在资产的存证历史"""
        response = client.get('/api/blockchain/history/nonexistent-id')

        assert response.status_code == 404
