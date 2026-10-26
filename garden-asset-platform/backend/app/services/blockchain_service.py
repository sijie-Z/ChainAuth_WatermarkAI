"""
区块链服务模块
支持FISCO BCOS联盟链存证
"""
import os
import json
import logging
import hashlib
from datetime import datetime
from typing import Optional, Dict, Any

from flask import current_app
from app.extensions import db
from app.models.blockchain import BlockchainTransaction, Certificate
from app.models.asset import Asset, AssetVersion
from app.services.object_storage import hash_ref, ref_exists


logger = logging.getLogger(__name__)


class BlockchainService:
    """区块链存证服务"""

    def __init__(self):
        self.rpc_url = None
        self.contract_address = None
        self.chain_id = None
        self.private_key = None
        self.enabled = False
        self._web3 = None
        self._contract = None

    def init_app(self, app):
        """从Flask应用初始化配置"""
        self.rpc_url = app.config.get('BLOCKCHAIN_RPC_URL')
        self.contract_address = app.config.get('CONTRACT_ADDRESS')
        self.chain_id = app.config.get('CHAIN_ID', 1)
        self.private_key = app.config.get('PRIVATE_KEY')
        self.enabled = app.config.get('BLOCKCHAIN_ENABLED', False)

        # 如果配置了RPC URL，尝试初始化Web3
        if self.rpc_url and self.enabled:
            self._init_web3()

    def _init_web3(self):
        """初始化Web3连接；只有配置了合约地址时才认为具备真实上链能力"""
        try:
            from web3 import Web3
            self._web3 = Web3(Web3.HTTPProvider(self.rpc_url))

            if not self._web3.is_connected():
                logger.warning(f"区块链连接失败: {self.rpc_url}")
                self.enabled = False
                return

            if not self.contract_address:
                logger.warning("未配置 CONTRACT_ADDRESS，区块链存证以模拟模式运行")
                self.enabled = False
                return

            from contracts.abi import CONTRACT_ABI
            address = self._web3.to_checksum_address(self.contract_address)
            self._contract = self._web3.eth.contract(address=address, abi=CONTRACT_ABI)
            logger.info(f"区块链连接成功: {self.rpc_url}, 合约: {address}")
        except ImportError:
            logger.warning("web3库未安装，使用模拟模式")
            self.enabled = False
        except Exception as e:
            logger.error(f"区块链初始化失败: {str(e)}")
            self.enabled = False

    def is_connected(self) -> bool:
        """检查区块链连接状态"""
        if not self.enabled or not self._web3:
            return False
        try:
            return self._web3.is_connected()
        except:
            return False

    @staticmethod
    def generate_file_hash(file_path: str) -> str:
        """计算文件SHA256哈希"""
        sha256 = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b''):
                sha256.update(chunk)
        return sha256.hexdigest()

    @staticmethod
    def generate_tx_hash() -> str:
        """生成模拟的FISCO BCOS风格交易哈希"""
        import uuid
        import time
        # FISCO BCOS交易哈希格式: 0x + 64位hex
        raw = f"{uuid.uuid4().hex}{uuid.uuid4().hex}"[:64]
        return f"0x{raw}"

    @staticmethod
    def generate_block_number() -> int:
        """生成模拟的区块号（递增风格）"""
        import random
        return random.randint(3000000, 9000000)

    @staticmethod
    def generate_gas_used() -> int:
        """生成模拟的Gas消耗"""
        import random
        return random.randint(21000, 300000)

    @staticmethod
    def current_version(asset: Asset):
        return AssetVersion.query.filter_by(asset_id=asset.id).order_by(
            AssetVersion.version_no.desc()
        ).first()

    @staticmethod
    def certificate_for_version(asset: Asset, version=None):
        if version:
            return Certificate.query.filter_by(
                asset_id=asset.id, version_id=version.id
            ).first()
        return Certificate.query.filter_by(asset_id=asset.id).order_by(
            Certificate.id.desc()
        ).first()

    @staticmethod
    def _existing_result(certificate):
        return {
            'success': True,
            'already': True,
            'message': '当前版本已存证',
            'tx_hash': certificate.tx_hash,
            'certificate_id': certificate.certificate_id,
            'block_number': certificate.block_number,
            'version_id': certificate.version_id,
            'version_no': certificate.version_no,
            'simulated': not (blockchain_service.enabled and blockchain_service._web3),
        }

    def register_asset(self, asset: Asset, user=None) -> Dict[str, Any]:
        """
        资产上链存证（按当前文件版本签发证书）

        Args:
            asset: 资产对象
            user: 操作用户

        Returns:
            存证结果字典；同一版本重复提交时返回已有证书（already=True），
            不会重复生成交易与证书。
        """
        version = self.current_version(asset)
        file_hash = None
        if asset.storage_path and ref_exists(asset.storage_path):
            file_hash = hash_ref(asset.storage_path)
        elif version and version.file_hash:
            file_hash = version.file_hash

        if not file_hash:
            return {
                'success': False,
                'message': '资产文件不存在，无法计算存证指纹'
            }

        # 幂等：同一版本已签发证书时直接返回原证书
        existing = self.certificate_for_version(asset, version)
        if existing and existing.file_hash == file_hash:
            return self._existing_result(existing)
        if version and existing:
            return {
                'success': False,
                'message': '当前版本已有证书，但文件指纹与证书不一致，请先核查文件'
            }

        # 特征哈希（如果有）
        feature_hash = None
        if asset.feature_vector_id:
            feature_hash = hashlib.sha256(str(asset.feature_vector_id).encode()).hexdigest()

        # 创建存证记录
        tx = BlockchainTransaction(
            tx_type='asset_register',
            asset_id=asset.id,
            status='pending',
            raw_data={
                'asset_code': asset.asset_code,
                'version_id': version.id if version else None,
                'version_no': version.version_no if version else None,
                'file_hash': file_hash,
                'watermark_id': asset.watermark_id,
            }
        )

        if self.enabled and self._web3 and self._contract:
            # 真实链上存证
            result = self._register_on_chain(
                asset_code=asset.asset_code,
                watermark_id=asset.watermark_id,
                file_hash=file_hash,
                feature_hash=feature_hash
            )

            if result['success']:
                tx.tx_hash = result['tx_hash']
                tx.block_number = result.get('block_number')
                tx.from_address = result.get('from_address')
                tx.to_address = self.contract_address
                tx.gas_used = result.get('gas_used')
                tx.status = 'confirmed'
                tx.confirmed_at = datetime.utcnow()
            else:
                tx.status = 'failed'
                tx.error_message = result.get('message')
        else:
            # 模拟模式（生成逼真的FISCO BCOS数据）
            tx.tx_hash = self.generate_tx_hash()
            tx.block_number = self.generate_block_number()
            tx.block_hash = self.generate_tx_hash()  # 区块哈希也是64位hex
            tx.gas_used = self.generate_gas_used()
            tx.from_address = f"0x{hashlib.sha256(b'garden-asset-platform').hexdigest()[:40]}"
            tx.to_address = f"0x{hashlib.sha256(b'asset-registry-contract').hexdigest()[:40]}"
            tx.confirmations = 12  # FISCO BCOS典型确认数
            tx.status = 'confirmed'
            tx.confirmed_at = datetime.utcnow()
            logger.info(f"模拟存证: {asset.asset_code}, tx={tx.tx_hash}")

        db.session.add(tx)

        # 链上交易失败时不能签发证书或把资产标记为已存证
        if tx.status == 'failed':
            db.session.commit()
            return {
                'success': False,
                'message': tx.error_message or '链上存证失败'
            }

        # 创建证书（绑定当前文件版本）
        certificate = Certificate(
            certificate_id=Certificate.generate_certificate_id(),
            asset_id=asset.id,
            version_id=version.id if version else None,
            version_no=version.version_no if version else None,
            tx_hash=tx.tx_hash,
            block_number=tx.block_number,
            watermark_id=asset.watermark_id,
            file_hash=file_hash
        )

        if user:
            certificate.creator_name = user.nickname or user.username

        db.session.add(certificate)

        # 更新资产状态（指向当前版本证书）
        asset.chain_status = 'confirmed'
        asset.chain_tx_hash = tx.tx_hash
        asset.chain_timestamp = datetime.utcnow()
        asset.certificate_id = certificate.certificate_id

        try:
            db.session.commit()
            logger.info(f"资产存证成功: {asset.asset_code} v{certificate.version_no or '-'}")

            return {
                'success': True,
                'already': False,
                'tx_hash': tx.tx_hash,
                'certificate_id': certificate.certificate_id,
                'block_number': tx.block_number,
                'version_id': certificate.version_id,
                'version_no': certificate.version_no,
                'simulated': not (self.enabled and self._web3 and self._contract)
            }
        except Exception as e:
            db.session.rollback()
            logger.error(f"资产存证失败: {str(e)}")
            return {
                'success': False,
                'message': str(e)
            }

    def _register_on_chain(self, asset_code: str, watermark_id: str,
                           file_hash: str, feature_hash: str) -> Dict[str, Any]:
        """在真实链上调用 AssetRegistry 合约存证"""
        try:
            if not self.private_key:
                raise ValueError('未配置 PRIVATE_KEY')
            if not self._contract:
                raise ValueError('未初始化合约实例')

            account = self._web3.eth.account.from_key(self.private_key)
            nonce = self._web3.eth.get_transaction_count(account.address)
            transaction = self._contract.functions.registerAsset(
                asset_code,
                watermark_id or '',
                file_hash or '',
                feature_hash or '',
            ).build_transaction({
                'from': account.address,
                'nonce': nonce,
                'gas': 3_000_000,
                'gasPrice': self._web3.eth.gas_price,
                'chainId': self.chain_id,
            })

            signed = self._web3.eth.account.sign_transaction(
                transaction, private_key=self.private_key
            )
            raw_transaction = getattr(signed, 'raw_transaction', None) or getattr(signed, 'rawTransaction')
            tx_hash = self._web3.eth.send_raw_transaction(raw_transaction)
            receipt = self._web3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)

            if receipt.status != 1:
                return {
                    'success': False,
                    'message': '链上交易执行失败（receipt.status != 1）'
                }

            return {
                'success': True,
                'tx_hash': tx_hash.hex(),
                'from_address': account.address,
                'block_number': receipt.blockNumber,
                'gas_used': receipt.gasUsed,
            }
        except Exception as e:
            logger.error(f"链上存证失败: {str(e)}")
            return {
                'success': False,
                'message': str(e)
            }

    def verify_asset(self, asset: Asset) -> Dict[str, Any]:
        """
        验证资产当前版本的存证

        Args:
            asset: 资产对象

        Returns:
            验证结果字典
        """
        version = self.current_version(asset)
        certificate = None
        if asset.certificate_id:
            certificate = Certificate.query.filter_by(
                certificate_id=asset.certificate_id
            ).first()
        if not certificate:
            certificate = Certificate.query.filter_by(asset_id=asset.id).order_by(
                Certificate.id.desc()
            ).first()

        if not certificate:
            return {
                'verified': False,
                'message': '资产未存证'
            }

        tx_hash = certificate.tx_hash or asset.chain_tx_hash

        # 查询交易记录
        tx = BlockchainTransaction.query.filter_by(
            tx_hash=tx_hash,
            asset_id=asset.id
        ).first()

        if not tx:
            return {
                'verified': False,
                'message': '未找到存证记录',
                'certificate_id': certificate.certificate_id
            }

        if tx.status != 'confirmed':
            return {
                'verified': False,
                'message': f'存证状态异常: {tx.status}',
                'certificate_id': certificate.certificate_id
            }

        # 证书是否对应当前文件版本（旧数据没有 version_id 时按文件指纹判断）
        version_matches = True
        if certificate.version_id and version:
            version_matches = certificate.version_id == version.id
        elif certificate.version_id and not version:
            version_matches = False

        checks = {
            'chain_record': True,
            'watermark': bool(asset.watermark_id),
            'certificate': False,
            'version': version_matches,
            'file_hash': None
        }

        expired = bool(
            certificate.valid_until and certificate.valid_until <= datetime.utcnow()
        )
        checks['certificate'] = certificate.status == 'valid' and not expired

        # 证书记录的是原始文件指纹；水印文件是派生副本。
        # 因此原始文件或水印文件任一与证书指纹一致，都视为文件未被替换。
        candidate_paths = []
        if certificate.version_id and certificate.version:
            candidate_paths.append(certificate.version.file_path)
        candidate_paths.extend([asset.storage_path, asset.watermarked_path])
        candidate_hashes = []
        for file_path in candidate_paths:
            if not file_path or not ref_exists(file_path):
                continue
            candidate_hashes.append(hash_ref(file_path))

        if candidate_hashes and certificate.file_hash:
            checks['file_hash'] = certificate.file_hash in candidate_hashes

        simulated = not (self.enabled and self._web3 and self._contract)
        verified = all(value is True for value in checks.values())

        if verified and simulated:
            message = '本地存证记录校验通过（演示环境，未连接链节点）'
        elif verified:
            message = '存证验证通过'
        elif not version_matches:
            message = '证书对应历史版本，当前版本尚未存证'
        elif checks['file_hash'] is None:
            message = '无法完成文件指纹比对（文件缺失或未签发证书）'
        else:
            message = '存证校验未通过，请检查文件、水印或证书状态'

        return {
            'verified': verified,
            'simulated': simulated,
            'checks': checks,
            'message': message,
            'tx_hash': tx.tx_hash,
            'block_number': tx.block_number,
            'confirmed_at': tx.confirmed_at.isoformat() if tx.confirmed_at else None,
            'certificate_id': certificate.certificate_id,
            'version_id': certificate.version_id,
            'version_no': certificate.version_no,
            'current_version_no': version.version_no if version else None
        }

    def get_asset_history(self, asset: Asset) -> list:
        """
        获取资产存证历史

        Args:
            asset: 资产对象

        Returns:
            交易历史列表
        """
        transactions = BlockchainTransaction.query.filter_by(
            asset_id=asset.id
        ).order_by(BlockchainTransaction.created_at.desc()).all()

        return [tx.to_dict() for tx in transactions]


# 全局区块链服务实例
blockchain_service = BlockchainService()