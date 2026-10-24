"""
区块链模块测试
"""
import uuid

import pytest

from app.extensions import db
from app.models.asset import Asset, AssetVersion
from app.models.blockchain import Certificate
from app.models.user import User


def _draft_document(app, with_certificate=True):
    with app.app_context():
        user = User.query.filter_by(username='testuser').first()
        asset = Asset(
            asset_code=f'DOC-{uuid.uuid4().hex[:8].upper()}',
            title='无盲水印文档存证测试',
            asset_type='document',
            file_format='PDF',
            file_hash='a' * 64,
            status='draft',
            creator_id=user.id,
            owner_id=user.id,
            uploader_id=user.id,
        )
        db.session.add(asset)
        db.session.flush()
        version = AssetVersion(
            asset_id=asset.id,
            version_no=1,
            file_path='/tmp/not-present.pdf',
            file_name='brief.pdf',
            file_format='PDF',
            file_size=128,
            file_hash='a' * 64,
        )
        db.session.add(version)
        db.session.flush()
        certificate = None
        if with_certificate:
            certificate = Certificate(
                certificate_id=f'CERT-{uuid.uuid4().hex[:12].upper()}',
                asset_id=asset.id,
                version_id=version.id,
                version_no=1,
                tx_hash='0x' + 'b' * 64,
                block_number=100,
                watermark_id=None,
                file_hash='a' * 64,
                creator_name=user.username,
                status='valid',
            )
            db.session.add(certificate)
        db.session.commit()
        return asset.id, certificate.certificate_id if certificate else None


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

    def test_history_all_requires_admin(self, client, auth_header):
        """全平台存证历史只允许管理员读取"""
        response = client.get('/api/blockchain/history', headers=auth_header)

        assert response.status_code == 403

    def test_history_all_admin(self, client, admin_header):
        """管理员可以获取全平台存证历史"""
        response = client.get('/api/blockchain/history', headers=admin_header)

        assert response.status_code == 200
        data = response.get_json()
        assert data['code'] == 200
        assert isinstance(data['data'], list)

    def test_history_asset_not_found(self, client, auth_header):
        """测试获取不存在资产的存证历史"""
        response = client.get('/api/blockchain/history/nonexistent-id', headers=auth_header)

        assert response.status_code == 404

    def test_document_can_be_certified_without_watermark(
        self, client, app, auth_header
    ):
        """模型/文档/视频没有盲水印，也应能按文件哈希存证并形成完整证据链"""
        asset_id, _ = _draft_document(app, with_certificate=False)

        response = client.post(
            '/api/blockchain/register',
            json={'asset_id': asset_id},
            headers=auth_header,
        )

        assert response.status_code == 200, response.get_json()
        certificate_id = response.get_json()['data']['certificate_id']
        assert certificate_id

        evidence = client.get(
            f'/api/assets/{asset_id}/evidence', headers=auth_header
        ).get_json()['data']
        watermark = next(
            item for item in evidence['items'] if item['key'] == 'watermark'
        )
        assert watermark['state'] == 'done'
        assert '不适用' in watermark['description']
        assert evidence['summary']['verified'] is True

    def test_image_still_requires_watermark_before_chaining(
        self, client, sample_asset, auth_header
    ):
        response = client.post(
            '/api/blockchain/register',
            json={'asset_id': sample_asset},
            headers=auth_header,
        )

        assert response.status_code == 400
        assert '水印' in response.get_json()['message']

    def test_draft_certificate_is_only_visible_to_owner(
        self, client, app, auth_header, adm1_header
    ):
        """草稿证书不能通过公开接口或无关账号枚举"""
        asset_id, certificate_id = _draft_document(app)

        anonymous = client.get(f'/api/blockchain/certificate/{certificate_id}')
        assert anonymous.status_code == 404

        unrelated = client.get(
            f'/api/blockchain/certificate/{certificate_id}',
            headers=adm1_header,
        )
        assert unrelated.status_code == 404

        owner = client.get(
            f'/api/blockchain/certificate/{certificate_id}',
            headers=auth_header,
        )
        assert owner.status_code == 200
        assert owner.get_json()['data']['asset']['title'] == '无盲水印文档存证测试'

    def test_public_chain_status_hides_rpc_url(self, client, admin_header):
        public = client.get('/api/blockchain/status').get_json()['data']
        assert 'rpc_url' not in public
        assert 'rpc_configured' in public

        admin = client.get(
            '/api/blockchain/status', headers=admin_header
        ).get_json()['data']
        assert 'rpc_url' in admin
