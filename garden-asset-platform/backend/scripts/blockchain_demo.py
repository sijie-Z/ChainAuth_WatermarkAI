"""
区块链示例交互脚本
演示如何与FISCO BCOS进行交互
"""
import json
import hashlib
from web3 import Web3
from app.config import config


class BlockchainDemo:
    """区块链示例类"""

    def __init__(self):
        self.w3 = None
        self.contract = None
        self.account = None

    def connect(self, rpc_url):
        """连接区块链节点"""
        self.w3 = Web3(Web3.HTTPProvider(rpc_url))
        if not self.w3.is_connected():
            raise Exception("无法连接区块链节点")
        print(f"✓ 已连接区块链节点: {rpc_url}")
        print(f"  当前区块高度: {self.w3.eth.block_number}")

    def load_contract(self, address, abi):
        """加载智能合约"""
        self.contract = self.w3.eth.contract(
            address=self.w3.to_checksum_address(address),
            abi=abi
        )
        print(f"✓ 已加载合约: {address}")

    def set_account(self, private_key):
        """设置账户"""
        self.account = self.w3.eth.account.from_key(private_key)
        print(f"✓ 已设置账户: {self.account.address}")

    def register_asset(self, asset_id, watermark_id, file_hash, metadata):
        """注册资产上链"""
        if not self.contract or not self.account:
            raise Exception("合约或账户未配置")

        tx = self.contract.functions.registerAsset(
            asset_id,
            watermark_id,
            file_hash,
            json.dumps(metadata)
        ).build_transaction({
            'from': self.account.address,
            'nonce': self.w3.eth.get_transaction_count(self.account.address),
            'gas': 200000,
            'gasPrice': self.w3.eth.gas_price
        })

        signed = self.w3.eth.account.sign_transaction(tx, self.account.key)
        tx_hash = self.w3.eth.send_raw_transaction(signed.rawTransaction)
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)

        return {
            'tx_hash': tx_hash.hex(),
            'block_number': receipt['blockNumber'],
            'status': 'success' if receipt['status'] == 1 else 'failed'
        }

    def verify_asset(self, asset_id):
        """验证资产"""
        if not self.contract:
            raise Exception("合约未配置")

        result = self.contract.functions.verifyAsset(asset_id).call()

        return {
            'exists': result[0],
            'watermark_id': result[1],
            'file_hash': result[2],
            'registered_at': result[3]
        }

    def grant_license(self, license_id, asset_id, licensee, license_type, valid_until):
        """授权"""
        if not self.contract or not self.account:
            raise Exception("合约或账户未配置")

        tx = self.contract.functions.grantLicense(
            license_id,
            asset_id,
            licensee,
            license_type,
            valid_until
        ).build_transaction({
            'from': self.account.address,
            'nonce': self.w3.eth.get_transaction_count(self.account.address),
            'gas': 200000,
            'gasPrice': self.w3.eth.gas_price
        })

        signed = self.w3.eth.account.sign_transaction(tx, self.account.key)
        tx_hash = self.w3.eth.send_raw_transaction(signed.rawTransaction)
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)

        return {
            'tx_hash': tx_hash.hex(),
            'status': 'success' if receipt['status'] == 1 else 'failed'
        }


def demo():
    """演示区块链交互"""
    print("=" * 60)
    print("FISCO BCOS 区块链交互演示")
    print("=" * 60)

    # 示例配置
    RPC_URL = "http://127.0.0.1:20200"
    CONTRACT_ADDRESS = "0x..."
    PRIVATE_KEY = "..."

    demo = BlockchainDemo()

    try:
        # 1. 连接节点
        demo.connect(RPC_URL)

        # 2. 加载合约
        abi = [...]  # 合约ABI
        demo.load_contract(CONTRACT_ADDRESS, abi)

        # 3. 设置账户
        demo.set_account(PRIVATE_KEY)

        # 4. 注册资产
        result = demo.register_asset(
            asset_id="asset_001",
            watermark_id="ZY-IMG-20260426120000-A1B2",
            file_hash=hashlib.sha256(b"test_file").hexdigest(),
            metadata={"title": "拙政园全景", "type": "image"}
        )
        print(f"\n✓ 资产注册结果:")
        print(f"  交易哈希: {result['tx_hash']}")
        print(f"  区块高度: {result['block_number']}")

        # 5. 验证资产
        verify_result = demo.verify_asset("asset_001")
        print(f"\n✓ 资产验证结果:")
        print(f"  存在: {verify_result['exists']}")
        print(f"  水印ID: {verify_result['watermark_id']}")

        # 6. 授权
        license_result = demo.grant_license(
            license_id="lic_001",
            asset_id="asset_001",
            licensee="0x...",
            license_type="personal",
            valid_until=1735689600  # 2025-01-01
        )
        print(f"\n✓ 授权结果:")
        print(f"  交易哈希: {license_result['tx_hash']}")

    except Exception as e:
        print(f"\n✗ 错误: {e}")

    print("\n" + "=" * 60)


if __name__ == '__main__':
    demo()