"""路由认证审计 audit_routes_auth 回归测试。

锁定的整改行为：
- 真实应用 create_app() 成功即审计通过（正向，审计在 create_app 内部执行）；
- 白名单外路由未携带认证依赖 -> RuntimeError fail-fast，且报告包含违规路由；
- 白名单路由、AuthPermission 依赖、get_current_user 签名依赖均放行；
- include_router 惰性合并后的业务路由（_EffectiveRouteContext）必须被审计，
  不能静默跳过（回归：曾因 isinstance 只匹配 APIRoute/Mount 而全部漏检）；
- Annotated[X, Depends(...)] 形式的认证依赖必须被识别；
- FastAPI 内置文档路由（/docs、/redoc、/openapi.json）由默认白名单覆盖。
"""

from typing import Annotated

import pytest
from fastapi import APIRouter, Depends, FastAPI

from app.core.base_schema import AuthSchema
from app.core.dependencies import AuthPermission, get_current_user
from app.init_app import audit_routes_auth


def test_real_app_create_succeeds_with_audit_installed():
    """create_app 内部执行 audit_routes_auth，成功创建即全部业务路由通过认证审计。"""
    from main import create_app

    app = create_app()
    audit_routes_auth(app)


def test_bare_fastapi_builtin_docs_are_whitelisted():
    # 默认 FastAPI() 的 /docs、/redoc、/openapi.json 等内置路由均在 WHITE_API_LIST_PATH 内
    audit_routes_auth(FastAPI())


def test_route_without_auth_dependency_fails_fast():
    app = FastAPI()

    @app.get("/internal/secret")
    async def secret():
        return {}

    with pytest.raises(RuntimeError) as exc_info:
        audit_routes_auth(app)
    msg = str(exc_info.value)
    assert "路由认证审计失败" in msg
    assert "/internal/secret" in msg


def test_whitelisted_route_passes_without_auth():
    app = FastAPI()

    @app.get("/auth/login")
    async def login():
        return {}

    audit_routes_auth(app)


def test_whitelist_prefix_match_passes():
    app = FastAPI()

    @app.get("/common/health/anything")
    async def health():
        return {}

    audit_routes_auth(app)


def test_auth_permission_dependency_passes():
    app = FastAPI()

    @app.get("/system/user/list", dependencies=[Depends(AuthPermission(permissions=["system:user:list"]))])
    async def list_users():
        return {}

    audit_routes_auth(app)


def test_current_user_signature_dependency_passes():
    app = FastAPI()

    @app.get("/me")
    # 有意使用「签名默认值 Depends」形式（_has_auth_dependency 显式支持的形态），
    # 与业务代码的 Annotated 形式差异见测试报告，故此处豁免 FAST002。
    async def me(auth: AuthSchema = Depends(get_current_user)):  # noqa: FAST002
        return auth

    audit_routes_auth(app)


def test_violation_report_lists_only_bad_routes():
    app = FastAPI()

    @app.get("/ok/route", dependencies=[Depends(AuthPermission())])
    async def ok():
        return {}

    @app.post("/bad/route")
    async def bad():
        return {}

    with pytest.raises(RuntimeError) as exc_info:
        audit_routes_auth(app)
    msg = str(exc_info.value)
    assert "/bad/route" in msg
    assert "/ok/route" not in msg


def test_unauthenticated_dependency_does_not_count():
    """仅挂非认证依赖（如普通函数依赖）不算携带认证。"""
    app = FastAPI()

    async def some_dep():
        return None

    @app.get("/still/bad", dependencies=[Depends(some_dep)])
    async def still_bad():
        return {}

    with pytest.raises(RuntimeError):
        audit_routes_auth(app)


# ==================== include_router 惰性合并回归（_EffectiveRouteContext） ====================


def test_included_router_unauthenticated_route_fails_fast():
    """回归：include_router 挂载的未认证路由不得被静默跳过。

    FastAPI 0.138 的 include_router 惰性合并使业务路由在 app.routes 中呈
    _EffectiveRouteContext 类型；审计若只匹配 APIRoute/Mount 会全部漏检。
    """
    app = FastAPI()
    router = APIRouter()

    @router.get("/secret/no-auth")
    async def secret():
        return {}

    app.include_router(router)
    with pytest.raises(RuntimeError) as exc_info:
        audit_routes_auth(app)
    msg = str(exc_info.value)
    assert "/secret/no-auth" in msg


def test_included_router_annotated_dependency_passes():
    """Annotated[X, Depends(...)] 是业务代码的主流写法，必须识别为已认证。"""
    app = FastAPI()
    router = APIRouter()

    @router.get("/annotated/protected")
    async def protected(auth: Annotated[AuthSchema, Depends(get_current_user)]):
        return auth

    app.include_router(router)
    audit_routes_auth(app)


def test_included_router_router_level_dependency_passes():
    """router 级 dependencies 会合并进路由上下文，应视为已认证。"""
    app = FastAPI()
    router = APIRouter(dependencies=[Depends(AuthPermission())])

    @router.get("/system/demo/list")
    async def demo():
        return {}

    app.include_router(router)
    audit_routes_auth(app)


def test_included_router_whitelisted_path_passes():
    """include_router 挂载的白名单路径（含路由前缀拼接后）放行。"""
    app = FastAPI()
    router = APIRouter(prefix="/auth")

    @router.post("/login")
    async def login():
        return {}

    app.include_router(router)
    audit_routes_auth(app)
