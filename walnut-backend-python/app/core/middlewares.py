"""中间件。

- CustomCORSMiddleware: CORS（allowCredentials=true）
- LocaleMiddleware: 请求语言环境解析（Accept-Language → i18n ContextVar）
- RequestLogMiddleware: 请求计时日志 + 敏感字段剔除
- XssMiddleware: XSS 过滤（GET/DELETE 不过滤、清理 JSON 体）
- ApiDecryptMiddleware: 接口加解密（RSA+AES 请求/响应体）
- CustomGZipMiddleware / CustomHTTPSRedirectMiddleware / CustomTrustedHostMiddleware / CorrelationIdMiddleware
"""

import json
import time
import uuid

from starlette.datastructures import Headers, MutableHeaders
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.gzip import GZipMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.requests import Request
from starlette.responses import RedirectResponse, Response
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.common.constant import SystemConstants
from app.common.response import ErrorResponse
from app.config.setting import settings
from app.core.encrypt import decrypt_by_aes, decrypt_by_base64, decrypt_by_rsa, encrypt_by_aes, encrypt_by_base64, encrypt_by_rsa, random_string
from app.core.exceptions import ServiceException
from app.core.logger import logger, reset_correlation_id, set_correlation_id
from app.utils.xss_util import clean_html_tag

# ==================== 通用 body 读取/回注 ====================


async def _read_body(receive: Receive) -> bytes:
    body = b""
    while True:
        message = await receive()
        if message["type"] == "http.disconnect":
            break
        body += message.get("body", b"")
        if not message.get("more_body", False):
            break
    return body


def _make_receive(body: bytes, original_receive: Receive) -> Receive:
    sent = False

    async def receive() -> Message:
        nonlocal sent
        if not sent:
            sent = True
            return {"type": "http.request", "body": body, "more_body": False}
        return await original_receive()

    return receive


def _set_header(scope: Scope, name: bytes, value: bytes) -> None:
    headers = [(k, v) for k, v in scope["headers"] if k.lower() != name.lower()]
    headers.append((name, value))
    scope["headers"] = headers


# ==================== CORS / GZip / 安全 ====================


class CustomCORSMiddleware(CORSMiddleware):
    """CORS 中间件。"""

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(
            app,
            allow_origins=settings.ALLOW_ORIGINS,
            allow_methods=settings.ALLOW_METHODS,
            allow_headers=settings.ALLOW_HEADERS,
            allow_credentials=settings.ALLOW_CREDENTIALS,
            expose_headers=settings.CORS_EXPOSE_HEADERS,
            max_age=settings.CORS_MAX_AGE,
        )


class CustomGZipMiddleware(GZipMiddleware):
    """GZip 压缩中间件。"""

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app, minimum_size=settings.GZIP_MIN_SIZE, compresslevel=settings.GZIP_COMPRESS_LEVEL)


class CustomHTTPSRedirectMiddleware(BaseHTTPMiddleware):
    """HTTP → HTTPS 重定向（信任前端代理 X-Forwarded-Proto）。"""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if request.url.scheme != "https" and request.headers.get("X-Forwarded-Proto") != "https":
            url = request.url.replace(scheme="https")
            return RedirectResponse(url, status_code=301)
        return await call_next(request)


class CustomTrustedHostMiddleware(TrustedHostMiddleware):
    """可信主机 Host 头校验。"""

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app, allowed_hosts=settings.ALLOWED_HOSTS)


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """请求链路 ID 中间件。"""

    def __init__(self, app: ASGIApp) -> None:
        self._header = "X-Correlation-ID"
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        cid = request.headers.get(self._header) or str(uuid.uuid4())
        token = set_correlation_id(cid)
        try:
            response = await call_next(request)
            response.headers[self._header] = cid
            return response
        finally:
            reset_correlation_id(token)


# ==================== 请求语言环境 ====================


def _resolve_locale(headers: Headers) -> str:
    """解析请求语言环境。

    优先 ``Accept-Language``，``Content-Language`` 兜底；取首个语言项（剥离 q 值），
    规范化 ``-`` → ``_`` 后按语言前缀匹配受支持的语言（zh → zh_CN、en → en_US），
    其余回退默认 ``zh_CN``。
    """
    raw = headers.get("Accept-Language") or headers.get("Content-Language") or ""
    primary = raw.split(",")[0].split(";")[0].strip().replace("-", "_")
    prefix = primary.split("_")[0].lower()
    if prefix == "zh":
        return "zh_CN"
    if prefix == "en":
        return "en_US"
    return "zh_CN"


class LocaleMiddleware:
    """请求语言环境中间件（纯 ASGI，保证 ContextVar 与业务处理同任务可见）。

    请求开始时按 Accept-Language 设置 i18n ContextVar，请求结束重置，避免上下文串用。
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        from app.utils.i18n import reset_locale, set_locale

        token = set_locale(_resolve_locale(Headers(scope=scope)))
        try:
            await self.app(scope, receive, send)
        finally:
            reset_locale(token)


# ==================== 请求计时日志 ====================


def _scrub(obj):
    """递归剔除敏感字段（名单见 SystemConstants.EXCLUDE_PROPERTIES）。"""
    if isinstance(obj, dict):
        return {k: _scrub(v) for k, v in obj.items() if k not in SystemConstants.EXCLUDE_PROPERTIES}
    if isinstance(obj, list):
        return [_scrub(i) for i in obj]
    return obj


class RequestLogMiddleware:
    """请求计时日志中间件（纯 ASGI 以安全读取 body）。"""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        method = scope["method"]
        path = scope["path"]
        body = await _read_body(receive)
        receive = _make_receive(body, receive)

        # 记录请求开始（剔除敏感字段）
        content_type = Headers(scope=scope).get("content-type", "")
        if content_type.startswith("application/json") and body:
            try:
                params = _scrub(json.loads(body.decode("utf-8")))
            except Exception:
                params = "<binary>"
            logger.info("[PLUS]开始请求 => URL[{} {}],参数类型[json],参数:[{}]", method, path, params)
        else:
            qs = scope.get("query_string", b"").decode("utf-8", "ignore")
            logger.info("[PLUS]开始请求 => URL[{} {}],参数类型[param],参数:[{}]", method, path, qs)

        start = time.perf_counter()
        try:
            await self.app(scope, receive, send)
        finally:
            elapsed = (time.perf_counter() - start) * 1000
            logger.info("[PLUS]结束请求 => URL[{} {}],耗时:[{:.0f}]毫秒", method, path, elapsed)


# ==================== XSS 过滤 ====================


class XssMiddleware:
    """XSS 过滤中间件。

    GET/DELETE 请求不过滤；命中排除路径不过滤；其余清理查询参数与 JSON 请求体。
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    def _excluded(self, path: str) -> bool:
        for item in settings.XSS_EXCLUDE_URLS:
            if item and path.startswith(item.rstrip("*")):
                return True
        return False

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        method = scope["method"]
        path = scope["path"]
        # GET/DELETE 与排除路径直接放行
        if method in ("GET", "DELETE") or self._excluded(path):
            await self.app(scope, receive, send)
            return

        body = await _read_body(receive)
        headers = Headers(scope=scope)
        content_type = headers.get("content-type", "")
        if content_type.startswith("application/json") and body:
            try:
                cleaned = clean_html_tag(body.decode("utf-8"))
                body = cleaned.encode("utf-8")
                _set_header(scope, b"content-length", str(len(body)).encode())
            except Exception as e:
                logger.warning("XSS 清理请求体失败: {}", e)
        receive = _make_receive(body, receive)
        await self.app(scope, receive, send)


# ==================== 接口加解密 ====================


class ApiDecryptMiddleware:
    """接口加解密中间件。

    请求方向：请求头携带 ``encrypt-key``（RSA 加密的 AES 密钥）时，解密请求体。
    响应方向：端点标记 ``@api_encrypt(response=True)`` 时，加密响应体并回写 ``encrypt-key``。
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        method = scope["method"]
        headers = Headers(scope=scope)
        encrypt_key = headers.get(settings.API_DECRYPT_HEADER_FLAG)

        # ---- 请求解密 ----
        if method in ("POST", "PUT") and encrypt_key:
            body = await _read_body(receive)
            try:
                aes_password = decrypt_by_base64(decrypt_by_rsa(encrypt_key, settings.API_DECRYPT_PRIVATE_KEY))
                decrypted = decrypt_by_aes(body.decode("utf-8"), aes_password)
                body = decrypted.encode("utf-8")
                _set_header(scope, b"content-length", str(len(body)).encode())
                _set_header(scope, b"content-type", b"application/json")
            except ServiceException as e:
                logger.error("接口解密失败: {}", e.message)
                response = ErrorResponse(msg="没有访问权限，请联系管理员授权", code=403)
                await response(scope, receive, send)
                return
            except Exception as e:
                logger.error("接口解密异常: {}", e)
                response = ErrorResponse(msg="请求解密失败", code=400)
                await response(scope, receive, send)
                return
            receive = _make_receive(body, receive)

        # ---- 响应加密（仅端点显式声明时） ----
        start_message: Message | None = None
        body_chunks: list[bytes] = []
        encrypt_response = False

        async def send_wrapper(message: Message) -> None:
            nonlocal start_message, encrypt_response
            if message["type"] == "http.response.start":
                endpoint = scope.get("endpoint")
                if endpoint is not None and getattr(endpoint, "_api_encrypt_response", False):
                    encrypt_response = True
                    start_message = message
                    return
                await send(message)
            elif message["type"] == "http.response.body":
                if encrypt_response:
                    body_chunks.append(message.get("body", b""))
                    if not message.get("more_body", False):
                        await self._send_encrypted(start_message, b"".join(body_chunks), send)
                else:
                    await send(message)
            else:
                await send(message)

        await self.app(scope, receive, send_wrapper)

    async def _send_encrypted(self, start_message: Message | None, raw_body: bytes, send: Send) -> None:
        try:
            aes_password = random_string(32)
            encrypted_body = encrypt_by_aes(raw_body.decode("utf-8"), aes_password).encode("utf-8")
            encrypted_key = encrypt_by_rsa(encrypt_by_base64(aes_password), settings.API_DECRYPT_PUBLIC_KEY)

            headers = MutableHeaders(scope=start_message or {"type": "http.response.start", "status": 200, "headers": []})
            headers["Access-Control-Expose-Headers"] = settings.API_DECRYPT_HEADER_FLAG
            headers[settings.API_DECRYPT_HEADER_FLAG] = encrypted_key
            headers["Content-Length"] = str(len(encrypted_body))
            headers["Content-Type"] = "application/json; charset=utf-8"

            await send({"type": "http.response.start", "status": start_message.get("status", 200) if start_message else 200, "headers": headers.raw})
            await send({"type": "http.response.body", "body": encrypted_body, "more_body": False})
        except Exception as e:
            logger.error("接口响应加密失败: {}", e)
            await send(start_message or {"type": "http.response.start", "status": 500, "headers": []})
            await send({"type": "http.response.body", "body": raw_body, "more_body": False})


def api_encrypt(response: bool = False):
    """端点装饰器。

    ``response=True`` 时标记该端点响应体需加密（由 ApiDecryptMiddleware 处理）。
    请求解密由请求头 ``encrypt-key`` 自动触发。
    """

    def decorator(func):
        func._api_encrypt_response = response
        return func

    return decorator
