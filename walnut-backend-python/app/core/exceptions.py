"""异常体系与全局异常处理。

契约：
- 业务错误返回 HTTP 200，真实错误码写入响应体 ``code`` 字段（前端据此判断）；
- ``ServiceException`` 是唯一业务异常；认证异常 ``NotLoginException``(401)、
  ``NotPermissionException``/``NotRoleException``(403) 同样走信封体；
- 请求校验类错误（pydantic 参数校验）返回信封体 ``code=400``，消息为各校验错误以 ``, `` 拼接；
- 401/403/404/405 等 HTTP 语义错误返回真实 HTTP 状态码 + 信封体。
"""

from collections.abc import Sequence
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError, ResponseValidationError
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from starlette.exceptions import HTTPException
from starlette.responses import JSONResponse

from app.common.enums import EnvironmentEnum, HttpStatus
from app.common.response import ErrorResponse
from app.config.setting import settings
from app.core.logger import logger
from app.utils.i18n import MessageUtils


class AppBaseException(Exception):
    """应用基础异常（命名避免遮蔽内置 BaseException）。

    通过 i18n 消息键解析消息，解析失败回退 ``default_message``。
    """

    def __init__(self, module: str | None = None, message_code: str | None = None, args: tuple | None = None, default_message: str | None = None) -> None:
        super().__init__(default_message or message_code or "")
        self.module = module
        self.message_code = message_code
        self.args_ = args or ()
        self.default_message = default_message

    @property
    def message(self) -> str:
        if self.message_code:
            resolved = MessageUtils.message(self.message_code, *self.args_)
            if resolved and resolved != self.message_code:
                return resolved
        return self.default_message or ""

    def __str__(self) -> str:
        return self.message


class ServiceException(AppBaseException):
    """业务异常。

    用法:
        raise ServiceException("用户名已存在")
        raise ServiceException("用户名已存在", code=20001)
        raise ServiceException(message_code="repeat.submit.message")
        raise ServiceException.of(AuthErrorCode.XXX, *args)
    """

    def __init__(
        self,
        message: str | None = None,
        code: int | None = None,
        *,
        detail_message: str | None = None,
        message_code: str | None = None,
        args: tuple | None = None,
        module: str | None = None,
    ) -> None:
        if message is None and message_code:
            message = MessageUtils.message(message_code, *(args or ()))
        super().__init__(module=module, message_code=message_code, args=args, default_message=message)
        self.code = code
        self._message = message or ""
        self.detail_message = detail_message

    @property
    def message(self) -> str:
        if self.message_code:
            resolved = MessageUtils.message(self.message_code, *self.args_)
            if resolved and resolved != self.message_code:
                return resolved
        return self._message

    def __str__(self) -> str:
        return self.message

    @classmethod
    def of(cls, error_code, *args) -> "ServiceException":
        """从错误码枚举构造（code + i18n key，如 AuthErrorCode）。"""
        return cls(message=str(error_code.name), code=int(error_code), message_code=getattr(error_code, "key", "") or None, args=args)


class NotLoginException(ServiceException):
    """认证失败。"""

    def __init__(self, message: str = "认证失败，无法访问系统资源", code: int = HttpStatus.UNAUTHORIZED) -> None:
        super().__init__(message, code)


class NotPermissionException(ServiceException):
    """权限码校验失败。"""

    def __init__(self, message: str = "没有访问权限，请联系管理员授权", code: int = HttpStatus.FORBIDDEN) -> None:
        super().__init__(message, code)


class NotRoleException(ServiceException):
    """角色权限校验失败。"""

    def __init__(self, message: str = "没有访问权限，请联系管理员授权", code: int = HttpStatus.FORBIDDEN) -> None:
        super().__init__(message, code)


def _validation_msg(errors: Sequence[Any]) -> str:
    msgs = []
    for err in errors:
        msg = err.get("msg", str(err))
        if isinstance(msg, str) and msg.startswith("Value error"):
            msg = msg[11:].lstrip(" ,")
        msgs.append(str(msg))
    return ", ".join(msgs) if msgs else "请求参数验证失败"


def handle_exception(app: FastAPI) -> None:
    """注册全局异常处理器。"""

    @app.exception_handler(ServiceException)
    async def service_exception_handler(request: Request, exc: ServiceException) -> JSONResponse:
        logger.error("[业务异常] {} {} | code={} | msg={}", request.method, request.url.path, exc.code, exc.message)
        code = exc.code if exc.code is not None else HttpStatus.ERROR
        # 生产环境不外泄 detail_message
        data = exc.detail_message if (exc.detail_message and settings.ENVIRONMENT != EnvironmentEnum.PROD) else None
        return ErrorResponse(msg=exc.message, code=code, data=data)

    @app.exception_handler(AppBaseException)
    async def base_exception_handler(request: Request, exc: AppBaseException) -> JSONResponse:
        logger.error("[基础异常] {} {} | msg={}", request.method, request.url.path, exc.message)
        return ErrorResponse(msg=exc.message, code=HttpStatus.ERROR)

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        errors = exc.errors()
        logger.error("[参数验证异常] {} {} | errors={}", request.method, request.url.path, errors)
        # JSON 解析失败 → 400
        if any(err.get("type") == "json_invalid" for err in errors):
            return ErrorResponse(msg="请求数据格式错误（JSON 解析失败）", code=HttpStatus.BAD_REQUEST)
        # 其余校验错误 → 400 + 消息拼接（校验类错误不属于服务器错误）
        return ErrorResponse(msg=_validation_msg(errors), code=HttpStatus.BAD_REQUEST)

    @app.exception_handler(ResponseValidationError)
    async def response_validation_handler(request: Request, exc: ResponseValidationError) -> JSONResponse:
        logger.error("[响应验证异常] {} {} | errors={}", request.method, request.url.path, exc.errors())
        return ErrorResponse(msg="服务器响应格式错误", code=HttpStatus.ERROR)

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        logger.error("[HTTP异常] {} {} | status={} | detail={}", request.method, request.url.path, exc.status_code, exc.detail)
        if exc.status_code == 404:
            return ErrorResponse(msg="请求地址不存在", code=404, status_code=404)
        if exc.status_code == 405:
            return ErrorResponse(msg=str(exc.detail), code=405, status_code=405)
        return ErrorResponse(msg=str(exc.detail), code=exc.status_code, status_code=exc.status_code)

    @app.exception_handler(SQLAlchemyError)
    async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError) -> JSONResponse:
        logger.error("[数据库异常] {} {} | type={} | detail={}", request.method, request.url.path, type(exc).__name__, exc)
        if isinstance(exc, IntegrityError):
            detail = str(exc.orig) if exc.orig else str(exc)
            if "Duplicate entry" in detail or "UNIQUE constraint failed" in detail:
                return ErrorResponse(msg="数据库中已存在该记录，请联系管理员确认", code=HttpStatus.CONFLICT)
            if "foreign key constraint" in detail.lower():
                return ErrorResponse(msg="存在关联数据，无法删除", code=HttpStatus.CONFLICT)
            return ErrorResponse(msg="数据已存在或违反完整性约束", code=HttpStatus.CONFLICT)
        return ErrorResponse(msg="数据库操作失败", code=HttpStatus.ERROR)

    @app.exception_handler(ValueError)
    async def value_exception_handler(request: Request, exc: ValueError) -> JSONResponse:
        logger.error("[值异常] {} {} | msg={}", request.method, request.url.path, exc)
        return ErrorResponse(msg=str(exc), code=HttpStatus.BAD_REQUEST)

    @app.exception_handler(Exception)
    async def all_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("[未捕获异常] {} {} | type={} | detail={}", request.method, request.url.path, type(exc).__name__, exc)
        return ErrorResponse(msg="发生系统异常，请联系管理员", code=HttpStatus.ERROR)
