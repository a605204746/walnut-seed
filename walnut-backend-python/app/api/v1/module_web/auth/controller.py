"""认证端点。

URL 契约：
- POST /auth/login      登录（grant_type=password；请求体加解密由 ApiDecryptMiddleware 处理）
- POST /auth/logout     登出
- POST /auth/register   注册
- GET  /auth/tenant/list 租户下拉（未启用多租户，固定返回关闭）
- GET  /auth/code       图形验证码
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Request
from redis.asyncio.client import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.constant import SystemConstants
from app.common.enums import BusinessType
from app.common.response import SuccessResponse
from app.core.dependencies import db_getter, redis_getter
from app.core.rate_limiter import LimitType, RateLimiter
from app.core.router_class import OperationLogRoute, log
from app.utils.i18n import MessageUtils

from .schema import PasswordLoginBodySchema, RegisterBodySchema
from .service import AuthService

AuthRouter = APIRouter(route_class=OperationLogRoute, prefix="/auth", tags=["认证"])

DbSession = Annotated[AsyncSession, Depends(db_getter)]
RedisDep = Annotated[Redis, Depends(redis_getter)]


async def _load_client(db: AsyncSession, client_id: str):
    from app.api.v1.module_system.client.model import ClientModel

    stmt = select(ClientModel).where(ClientModel.client_id == client_id, ClientModel.del_flag == SystemConstants.NORMAL)
    result = await db.execute(stmt)
    return result.scalars().first()


async def _register_enabled(db: AsyncSession) -> bool:
    """注册开关（读取配置键 sys.account.registerUser）。"""
    from app.api.v1.module_system.config.model import ConfigModel

    stmt = select(ConfigModel.config_value).where(ConfigModel.config_key == "sys.account.registerUser")
    value = (await db.execute(stmt)).scalars().first()
    return str(value).lower() == "true" if value is not None else False


@AuthRouter.post("/login", summary="登录", dependencies=[Depends(RateLimiter(time=60, count=10, limit_type=LimitType.IP))])
@log(title="认证", business_type=BusinessType.OTHER, exclude_param_names=("password",))
async def login(body: PasswordLoginBodySchema, request: Request, db: DbSession, redis: RedisDep) -> SuccessResponse:
    client = await _load_client(db, body.client_id)
    # 查询不到 client 或 client 内不包含 grantType
    if client is None or body.grant_type not in (client.grant_type or ""):
        return SuccessResponse(code=500, msg=MessageUtils.message("auth.grant.type.error"))
    if SystemConstants.NORMAL != client.status:
        return SuccessResponse(code=500, msg=MessageUtils.message("auth.grant.type.blocked"))

    # 目前仅实现密码认证策略（sms/email/social 按需扩展，按授权类型策略分发）
    if body.grant_type != "password":
        return SuccessResponse(code=500, msg="授权类型不正确!")

    service = AuthService(db, redis, request)
    login_resp = await service.login_password(body, client)
    return SuccessResponse(data=login_resp)


@AuthRouter.post("/logout", summary="退出登录")
async def logout(request: Request, db: DbSession, redis: RedisDep) -> SuccessResponse:
    await AuthService(db, redis, request).logout()
    return SuccessResponse(msg="退出成功")


@AuthRouter.post("/register", summary="用户注册")
@log(title="认证", business_type=BusinessType.INSERT, exclude_param_names=("password",))
async def register(body: RegisterBodySchema, request: Request, db: DbSession, redis: RedisDep) -> SuccessResponse:
    if not await _register_enabled(db):
        return SuccessResponse(code=500, msg="当前系统没有开启注册功能！")
    await AuthService(db, redis, request).register(body)
    return SuccessResponse()


@AuthRouter.get("/tenant/list", summary="登录页面租户下拉框（兼容多租户前端）", dependencies=[Depends(RateLimiter(time=60, count=20, limit_type=LimitType.IP))])
async def tenant_list() -> SuccessResponse:
    return SuccessResponse(data={"tenantEnabled": False})


@AuthRouter.get("/code", summary="生成图形验证码", dependencies=[Depends(RateLimiter(time=60, count=30, limit_type=LimitType.IP))])
async def get_code(request: Request, db: DbSession, redis: RedisDep) -> SuccessResponse:
    data = await AuthService(db, redis, request).get_captcha()
    return SuccessResponse(data=data)
