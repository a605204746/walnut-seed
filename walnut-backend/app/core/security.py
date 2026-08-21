from datetime import datetime

import jwt
from fastapi import Request
from fastapi.security import OAuth2PasswordBearer
from fastapi.security.utils import get_authorization_scheme_param

from app.config.setting import settings
from app.core.base_schema import JWTPayloadSchema
from app.core.exceptions import NotLoginException


class CustomOAuth2PasswordBearer(OAuth2PasswordBearer):
    """自定义 OAuth2 Bearer 认证：从 Authorization 头读取 Bearer token，兼容查询参数携带。"""

    def __init__(
        self,
        token_url: str,
        scheme_name: str | None = None,
        scopes: dict[str, str] | None = None,
        description: str | None = None,
        auto_error: bool = True,
    ) -> None:
        super().__init__(tokenUrl=token_url, scheme_name=scheme_name, scopes=scopes, description=description, auto_error=auto_error)

    async def __call__(self, request: Request) -> str | None:
        authorization = request.headers.get(settings.TOKEN_NAME)
        # SSE（EventSource）无法设置自定义请求头，前端将 token 放在查询参数中，
        # 故兼容从查询参数读取 token
        if not authorization:
            authorization = request.query_params.get(settings.TOKEN_NAME)
        scheme, token = get_authorization_scheme_param(authorization)
        if not authorization or scheme.lower() != settings.TOKEN_PREFIX.lower():
            if self.auto_error:
                raise NotLoginException("认证失败，请登录后再试")
            return None
        return token


# OAuth2 认证配置（token_url 指向登录接口）
OAuth2Schema = CustomOAuth2PasswordBearer(token_url="auth/login", description="认证")


def create_access_token(payload: JWTPayloadSchema) -> str:
    """生成 JWT 访问令牌（HS256 签名）。"""
    payload_dict = payload.model_dump(exclude_none=False)
    if isinstance(payload_dict.get("exp"), datetime):
        payload_dict["exp"] = int(payload_dict["exp"].timestamp())
    return jwt.encode(payload=payload_dict, key=settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_access_token(token: str, verify_exp: bool = True) -> JWTPayloadSchema:
    """解析 JWT 访问令牌。

    ``verify_exp=False`` 用于滑动过期场景（由 Redis 会话 TTL 决定实际有效期）。
    """
    if not token:
        raise NotLoginException("认证不存在，请重新登录")
    try:
        options: dict = {}
        if not verify_exp:
            options["verify_exp"] = False
        payload = jwt.decode(jwt=token, key=settings.SECRET_KEY, algorithms=[settings.ALGORITHM], options=options)  # type: ignore[arg-type]
        if not payload.get("sub"):
            raise NotLoginException("无效认证，请重新登录")
        return JWTPayloadSchema(**payload)
    except (jwt.InvalidSignatureError, jwt.DecodeError):
        raise NotLoginException("无效认证，请重新登录")
    except jwt.ExpiredSignatureError:
        raise NotLoginException("认证已过期，请重新登录")
    except jwt.InvalidTokenError:
        raise NotLoginException("token已失效，请重新登录")
