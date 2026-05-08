"""
水印模块测试
"""
import pytest
import io


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

    def test_embed_asset_not_found(self, client, auth_header):
        """测试嵌入水印到不存在的资产"""
        response = client.post('/api/watermark/embed',
            json={'asset_id': 'nonexistent-id'},
            headers=auth_header
        )

        assert response.status_code in [404, 400]

    def test_extract_asset_not_found(self, client, auth_header):
        """测试从不存在的资产提取水印"""
        response = client.post('/api/watermark/extract',
            json={'asset_id': 'nonexistent-id'},
            headers=auth_header
        )

        assert response.status_code in [404, 400]

    def test_embed_unauthorized(self, client):
        """测试未认证嵌入水印"""
        response = client.post('/api/watermark/embed',
            json={'asset_id': 'some-id'}
        )

        assert response.status_code == 401

    def test_trace_with_file(self, client):
        """测试上传文件溯源"""
        data = {
            'file': (io.BytesIO(b'\x89PNG\r\n\x1a\n' + b'\x00' * 100), 'test.png')
        }
        response = client.post('/api/watermark/trace',
            data=data,
            content_type='multipart/form-data'
        )

        # 应该返回结果（可能未找到匹配，但不应500）
        assert response.status_code in [200, 404]

    def test_get_logs_unauthorized(self, client):
        """测试未认证获取水印日志"""
        response = client.get('/api/watermark/logs')

        assert response.status_code == 401
