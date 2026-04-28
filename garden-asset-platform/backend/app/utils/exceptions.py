"""
异常类定义
"""


class BaseError(Exception):
    """基础异常类"""
    def __init__(self, message, code=400):
        self.message = message
        self.code = code
        super().__init__(self.message)


class ValidationError(BaseError):
    """验证错误"""
    def __init__(self, message):
        super().__init__(message, 400)


class AuthenticationError(BaseError):
    """认证错误"""
    def __init__(self, message="认证失败"):
        super().__init__(message, 401)


class AuthorizationError(BaseError):
    """授权错误"""
    def __init__(self, message="权限不足"):
        super().__init__(message, 403)


class NotFoundError(BaseError):
    """资源不存在错误"""
    def __init__(self, message="资源不存在"):
        super().__init__(message, 404)


class ConflictError(BaseError):
    """冲突错误"""
    def __init__(self, message="资源冲突"):
        super().__init__(message, 409)


class WatermarkError(BaseError):
    """水印处理错误"""
    def __init__(self, message="水印处理失败"):
        super().__init__(message, 500)


class BlockchainError(BaseError):
    """区块链错误"""
    def __init__(self, message="区块链操作失败"):
        super().__init__(message, 500)


class AIError(BaseError):
    """AI服务错误"""
    def __init__(self, message="AI服务调用失败"):
        super().__init__(message, 500)


class FileError(BaseError):
    """文件操作错误"""
    def __init__(self, message="文件操作失败"):
        super().__init__(message, 500)


class DatabaseError(BaseError):
    """数据库错误"""
    def __init__(self, message="数据库操作失败"):
        super().__init__(message, 500)