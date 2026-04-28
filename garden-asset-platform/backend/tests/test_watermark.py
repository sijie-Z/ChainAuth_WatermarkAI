"""
水印模块测试
"""
import pytest


class TestWatermark:
    """水印测试类"""

    def test_verify_watermark_missing_id(self, client):
        """测试缺少水印ID验证"""
        response = client.post('/api/watermark/verify', json={})

        assert response.status_code == 400

    def test_verify_watermark_not_found(self, client):
        """测试验证不存在的水印ID"""
        response = client.post('/api/watermark/verify', json={
            'watermark_id': 'ZY-IMG-999999999999-XXXX'
        })

        assert response.status_code == 404

    def test_trace_missing_file(self, client):
        """测试溯源缺少文件"""
        response = client.post('/api/watermark/trace')

        assert response.status_code == 400


class TestBlockchain:
    """区块链测试类"""

    def test_get_blockchain_status(self, client):
        """测试获取区块链状态"""
        response = client.get('/api/blockchain/status')

        assert response.status_code == 200
        data = response.get_json()
        assert 'connected' in data['data']

    def test_get_certificate_not_found(self, client):
        """测试获取不存在的证书"""
        response = client.get('/api/blockchain/certificate/nonexistent')

        assert response.status_code == 404