"""
枚举定义
"""
from enum import Enum


class UserRole(str, Enum):
    """用户角色"""
    USER = 'user'
    ASSET_ADMIN = 'asset_admin'
    LICENSE_ADMIN = 'license_admin'
    ADM1 = 'adm1'
    ADM2 = 'adm2'
    ADMIN = 'admin'


class UserStatus(str, Enum):
    """用户状态"""
    ACTIVE = 'active'
    INACTIVE = 'inactive'
    BANNED = 'banned'


class AssetType(str, Enum):
    """资产类型"""
    IMAGE = 'image'
    MODEL = 'model'
    VECTOR = 'vector'
    DOCUMENT = 'document'
    VIDEO = 'video'


class WatermarkStatus(str, Enum):
    """水印状态"""
    PENDING = 'pending'
    PROCESSING = 'processing'
    EMBEDDED = 'embedded'
    FAILED = 'failed'


class ChainStatus(str, Enum):
    """存证状态"""
    PENDING = 'pending'
    PROCESSING = 'processing'
    CONFIRMED = 'confirmed'
    FAILED = 'failed'


class LicenseType(str, Enum):
    """授权类型"""
    PERSONAL = 'personal'
    ACADEMIC = 'academic'
    COMMERCIAL = 'commercial'
    DISPLAY = 'display'
    DERIVATIVE = 'derivative'


class LicenseStatus(str, Enum):
    """授权状态"""
    PENDING = 'pending'
    ADM1_APPROVED = 'adm1_approved'
    APPROVED = 'approved'
    REJECTED = 'rejected'
    ACTIVE = 'active'
    EXPIRED = 'expired'
    REVOKED = 'revoked'


class ApprovalStatus(str, Enum):
    """审批状态"""
    PENDING = 'pending'
    APPROVED = 'approved'
    REJECTED = 'rejected'


class OperationAction(str, Enum):
    """操作类型"""
    # 用户
    LOGIN = 'login'
    LOGOUT = 'logout'
    REGISTER = 'register'

    # 资产
    UPLOAD = 'upload'
    DOWNLOAD = 'download'
    DELETE = 'delete'

    # 水印
    WATERMARK_EMBED = 'watermark_embed'
    WATERMARK_EXTRACT = 'watermark_extract'

    # 区块链
    BLOCKCHAIN_REGISTER = 'blockchain_register'
    BLOCKCHAIN_VERIFY = 'blockchain_verify'

    # 授权
    LICENSE_APPLY = 'license_apply'
    LICENSE_APPROVE = 'license_approve'


class FileType(str, Enum):
    """文件类型"""
    IMAGE = 'image'
    VECTOR = 'vector'
    DOCUMENT = 'document'
    VIDEO = 'video'
    MODEL = 'model'
    OTHER = 'other'


# 获取枚举值列表
def get_enum_values(enum_class):
    """获取枚举所有值"""
    return [e.value for e in enum_class]


# 检查值是否在枚举中
def is_valid_enum_value(enum_class, value):
    """检查值是否有效"""
    return value in get_enum_values(enum_class)