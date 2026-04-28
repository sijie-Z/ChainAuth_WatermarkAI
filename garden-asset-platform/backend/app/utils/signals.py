"""
信号处理
用于解耦的业务逻辑触发
"""
from blinker import Signal

# 定义信号

# 用户相关
user_registered = Signal('user-registered')
user_login = Signal('user-login')
user_logout = Signal('user-logout')

# 资产相关
asset_uploaded = Signal('asset-uploaded')
asset_deleted = Signal('asset-deleted')

# 水印相关
watermark_embedded = Signal('watermark-embedded')
watermark_extracted = Signal('watermark-extracted')

# 区块链相关
blockchain_registered = Signal('blockchain-registered')
blockchain_verified = Signal('blockchain-verified')

# 授权相关
license_applied = Signal('license-applied')
license_approved = Signal('license-approved')
license_rejected = Signal('license-rejected')


# 信号处理器

@watermark_embedded.connect
def on_watermark_embedded(sender, **kwargs):
    """水印嵌入后处理"""
    asset_id = kwargs.get('asset_id')
    watermark_id = kwargs.get('watermark_id')
    # 可以在这里触发通知、日志等


@blockchain_registered.connect
def on_blockchain_registered(sender, **kwargs):
    """区块链存证后处理"""
    asset_id = kwargs.get('asset_id')
    tx_hash = kwargs.get('tx_hash')
    # 可以在这里触发通知


@license_approved.connect
def on_license_approved(sender, **kwargs):
    """授权审批通过后处理"""
    license_id = kwargs.get('license_id')
    # 可以在这里发送邮件通知
