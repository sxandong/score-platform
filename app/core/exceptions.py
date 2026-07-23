"""应用自定义异常"""
from typing import Any


class AppException(Exception):
    def __init__(self, message: str = "服务器错误", code: int = 500, data: Any = None):
        self.message = message
        self.code = code
        self.data = data


class NotFoundException(AppException):
    def __init__(self, message: str = "资源不存在"):
        super().__init__(message=message, code=404)


class ForbiddenException(AppException):
    def __init__(self, message: str = "权限不足"):
        super().__init__(message=message, code=403)


class UnauthorizedException(AppException):
    def __init__(self, message: str = "未认证"):
        super().__init__(message=message, code=401)


class ValidationException(AppException):
    def __init__(self, message: str = "参数校验失败", data: Any = None):
        super().__init__(message=message, code=400, data=data)
