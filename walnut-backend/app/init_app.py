"""应用装配。

- lifespan: 数据库/Redis 初始化、SSE/WebSocket Redis topic 订阅、优雅关闭；
- validate_security_settings: 启动密钥校验（SECRET_KEY / RSA，服务对外可用前执行）；
- audit_routes_auth: 路由认证审计（白名单外路由必须携带认证依赖）；
- register_middlewares/exceptions/routers/static/docs/frontend。
"""

import asyncio
import base64
import inspect
from collections.abc import AsyncGenerator
from typing import Any

from fastapi import FastAPI
from fastapi.concurrency import asynccontextmanager
from fastapi.openapi.docs import get_redoc_html, get_swagger_ui_html, get_swagger_ui_oauth2_redirect_html
from fastapi.responses import HTMLResponse
from fastapi.routing import APIRoute
from fastapi.staticfiles import StaticFiles
from starlette.routing import Mount

from .config import path_conf
from .config.setting import settings
from .core.exceptions import handle_exception
from .core.logger import logger
from .utils.common_util import import_module

# RuoYi 生态公开的出厂默认 RSA 密钥对前缀（base64 DER）。
# 配置值匹配任一前缀即视为已知坏密钥：生产直接拒绝启动，其余环境强制停用接口加解密。
KNOWN_BAD_RSA_PUBLIC_PREFIX = "MFwwDQYJKoZIhvcNAQEBBQADSwAwSAJBAKoR8mX0rGKLqzcWmOzbfj64K8ZIgOdHnzkXSOVOZbFu"
KNOWN_BAD_RSA_PRIVATE_PREFIX = "MIIBVAIBADANBgkqhkiG9w0BAQEFAASCAT4wggE6AgEAAoEAmc3CuPiGL"

# RSA 密钥最小可接受位数（低于该长度的密钥视为无效）
_RSA_MIN_KEY_SIZE = 1024


def _is_known_bad_rsa(public_key: str, private_key: str) -> bool:
    """配置值是否命中 RuoYi 生态公开的默认密钥前缀。"""
    return public_key.startswith(KNOWN_BAD_RSA_PUBLIC_PREFIX) or private_key.startswith(KNOWN_BAD_RSA_PRIVATE_PREFIX)


def _rsa_keys_loadable(public_key: str, private_key: str) -> bool:
    """两把密钥能否按 base64 DER（公钥 SubjectPublicKeyInfo / 私钥 PKCS8）加载且长度达标。"""
    try:
        from cryptography.hazmat.primitives import serialization

        pub = serialization.load_der_public_key(base64.b64decode(public_key))
        priv = serialization.load_der_private_key(base64.b64decode(private_key), password=None)
        return pub.key_size >= _RSA_MIN_KEY_SIZE and priv.key_size >= _RSA_MIN_KEY_SIZE
    except Exception:
        return False


def validate_security_settings() -> None:
    """启动密钥校验（必须在服务对外可用前执行）。

    - SECRET_KEY：prod 为空/含 change-me/长度 <32 字节 → RuntimeError 拒绝启动；dev 仅告警；
    - RSA 密钥：prod 配置已知坏密钥（RuoYi 出厂密钥对）→ RuntimeError；
      密钥为空或无效（含 dev）→ 将 ``settings.API_DECRYPT_ENABLED`` 置 False 并告警，
      安全降级为明文传输，绝不带着假密钥运行。
    """
    from app.common.enums import EnvironmentEnum

    is_prod = settings.ENVIRONMENT == EnvironmentEnum.PROD

    # ---- JWT 签名密钥 ----
    secret = settings.SECRET_KEY
    secret_weak = not secret or "change-me" in secret or len(secret.encode("utf-8")) < 32
    if secret_weak:
        if is_prod:
            raise RuntimeError("SECRET_KEY 未配置或不安全（为空/含 change-me/长度不足 32 字节），生产环境拒绝启动")
        logger.warning("⚠️ SECRET_KEY 为开发占位值（为空/含 change-me/长度不足 32 字节），生产环境必须更换")

    # ---- 接口加解密 RSA 密钥对 ----
    public_key = settings.API_DECRYPT_PUBLIC_KEY
    private_key = settings.API_DECRYPT_PRIVATE_KEY
    known_bad = _is_known_bad_rsa(public_key, private_key)
    if known_bad and is_prod:
        raise RuntimeError("检测到 RuoYi 生态公开的默认 RSA 密钥，公开密钥严禁用于生产环境，请通过 scripts/gen_rsa_keys.py 重新生成")

    if not settings.API_DECRYPT_ENABLED:
        return
    if not public_key or not private_key:
        settings.API_DECRYPT_ENABLED = False
        logger.warning("⚠️ 接口加解密 RSA 密钥未配置，已自动停用接口加解密（降级为明文）")
        return
    if known_bad or not _rsa_keys_loadable(public_key, private_key):
        settings.API_DECRYPT_ENABLED = False
        logger.warning("⚠️ 接口加解密 RSA 密钥无效（已知坏密钥或无法解析），已自动停用接口加解密（降级为明文）")


def _white_listed(path: str) -> bool:
    """路径是否命中公开白名单（``WHITE_API_LIST_PATH``，支持 * 结尾前缀匹配）。"""
    for item in settings.WHITE_API_LIST_PATH:
        if item.endswith("*"):
            if path.startswith(item[:-1]):
                return True
        elif path == item:
            return True
    return False


def _has_auth_dependency(route: Any) -> bool:
    """路由是否携带认证依赖（AuthPermission 或 get_current_user）。

    检查三处来源：
    1. 路由级 dependencies（router 级依赖已由 FastAPI 合并进路由上下文）；
    2. 端点签名参数的默认值 ``param: X = Depends(...)``；
    3. Annotated 形式 ``param: Annotated[X, Depends(...)]``（FastAPI 推荐写法，
       参数的 default 为空，须经 get_type_hints(include_extras=True) 提取）。
    """
    import typing

    from fastapi import params as fastapi_params

    from app.core.dependencies import AuthPermission, get_current_user

    candidates: list[Any] = [dep.dependency for dep in (getattr(route, "dependencies", None) or [])]
    endpoint = getattr(route, "endpoint", None)
    if endpoint is not None:
        try:
            for param in inspect.signature(endpoint).parameters.values():
                if isinstance(param.default, fastapi_params.Depends):
                    candidates.append(param.default.dependency)
        except (TypeError, ValueError):
            pass
        try:
            hints = typing.get_type_hints(endpoint, include_extras=True)
        except Exception:
            hints = {}
        for hint in hints.values():
            if typing.get_origin(hint) is typing.Annotated:
                candidates.extend(meta.dependency for meta in typing.get_args(hint)[1:] if isinstance(meta, fastapi_params.Depends))
    return any(isinstance(dep, AuthPermission) or dep is get_current_user for dep in candidates)


def audit_routes_auth(app: FastAPI) -> None:
    """启动路由认证审计：白名单外的路由必须携带认证依赖，违规直接启动失败。

    FastAPI 新版本 include_router 为惰性合并（app.routes 中出现 _IncludedRouter），
    需递归展开 effective_candidates；展开结果是 _EffectiveRouteContext（既非
    APIRoute 也非 Mount 子类，携带合并后的 path/dependencies/endpoint），
    必须显式识别，否则全部业务路由会被静默跳过。
    未携带认证依赖属于编程错误，dev/prod 一律 fail-fast。
    """
    try:
        from fastapi.routing import _IncludedRouter
    except ImportError:  # 旧版本无惰性合并机制
        _IncludedRouter = ()  # type: ignore[assignment]
    try:
        from fastapi.routing import _EffectiveRouteContext
    except ImportError:
        _EffectiveRouteContext = ()  # type: ignore[assignment]

    violations: list[str] = []

    def check_route(path: str, methods: Any, route: Any) -> None:
        if not _white_listed(path) and not _has_auth_dependency(route):
            violations.append(f"{sorted(methods or [])} {path}")

    def walk(routes: Any) -> None:
        for route in routes:
            if _IncludedRouter and isinstance(route, _IncludedRouter):
                walk(route.effective_candidates())
                walk(route.effective_low_priority_routes())
                continue
            if _EffectiveRouteContext and isinstance(route, _EffectiveRouteContext):
                # include_router 惰性合并后的最终路由上下文（含 router 级依赖）
                if getattr(route, "endpoint", None) is not None:
                    check_route(route.path, route.methods, route)
                continue
            if isinstance(route, APIRoute):
                check_route(route.path, route.methods, route)
            elif isinstance(route, Mount):
                # 静态托管挂载（/static、/web 等）：路径须命中白名单前缀
                if not _white_listed(route.path):
                    violations.append(f"MOUNT {route.path}")

    walk(app.routes)
    if violations:
        raise RuntimeError("路由认证审计失败：以下路由未携带认证依赖且不在公开白名单（WHITE_API_LIST_PATH）内：" + "; ".join(violations))
    logger.info("✅ 路由认证审计通过（{} 白名单路径生效）", len(settings.WHITE_API_LIST_PATH))


async def _subscribe_topics(app: FastAPI) -> None:
    """启动 SSE / WebSocket 的 Redis topic 订阅后台任务。"""
    redis = getattr(app.state, "redis", None)
    if redis is None:
        logger.warning("⚠️ Redis 不可用，跳过 SSE/WebSocket topic 订阅")
        return

    from app.core.redis_crud import RedisUtils
    from app.core.sse import SseEmitterManager, sse_manager
    from app.core.websocket import WEB_SOCKET_TOPIC, WebSocketUtils

    if settings.SSE_ENABLED:
        app.state.sse_sub_task = asyncio.create_task(RedisUtils(redis).subscribe(SseEmitterManager.SSE_TOPIC, sse_manager.on_topic_message))
        logger.info("✅ SSE topic 订阅已启动 ({})", SseEmitterManager.SSE_TOPIC)
    if settings.WEBSOCKET_ENABLED:
        app.state.ws_sub_task = asyncio.create_task(RedisUtils(redis).subscribe(WEB_SOCKET_TOPIC, WebSocketUtils.on_topic_message))
        logger.info("✅ WebSocket topic 订阅已启动 ({})", WEB_SOCKET_TOPIC)


async def _cancel_task(task: asyncio.Task | None) -> None:
    if task and not task.done():
        task.cancel()
        try:
            await task
        except (asyncio.CancelledError, Exception):
            pass


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[Any, Any]:
    from app.core.logger import setup_logger

    # uvicorn 启动时可能替换 sys.stdout，导致 loguru 的控制台 sink 写入旧引用；
    # 在此处重新初始化日志（使用 sys.__stdout__），确保控制台输出正常。
    setup_logger()

    # 显式接线操作日志消费者（OperationLogRoute 写方法异步落库 sys_oper_log）
    from app.api.v1.module_system.log.service import consume_oper_log
    from app.core.router_class import set_oper_log_consumer

    set_oper_log_consumer(consume_oper_log)

    from app.core.database import async_engine, redis_connect

    # 数据库：按 Alembic 迁移对齐结构（dev 自动执行；prod 由 docker-entrypoint
    # 在应用启动前显式执行，此处 DATABASE_AUTO_MIGRATE=False 跳过），随后写入种子数据（幂等）
    try:
        # 先导入全部业务模型注册到 metadata（模型按需惰性导入的兜底）
        from app.core.base_model import MappedBase
        from app.utils.import_util import ImportUtil

        ImportUtil.find_models(MappedBase)
        if settings.DATABASE_AUTO_MIGRATE:
            from app.core.migrate import upgrade_to_head

            await upgrade_to_head()
            logger.info("✅ Alembic 迁移已应用到 head")
        from app.seed.initialize import InitializeData

        await InitializeData().init_db()
    except Exception as e:
        logger.warning("⚠️ 数据库初始化跳过/失败: {}", e)

    # Redis
    redis = await redis_connect(app, status=True)
    if redis is not None:
        logger.info("✅ Redis 连接初始化完成")
    else:
        logger.warning("⚠️ Redis 未连接（认证/缓存/SSE 订阅将不可用）")

    # OSS（S3，默认 SeaweedFS）：桶自举——失败仅告警不阻断启动，首次上传时会惰性自建重试
    if settings.OSS_TYPE == "s3":
        from app.core.file_storage import get_file_storage

        try:
            await asyncio.to_thread(get_file_storage().ensure_bucket)
            logger.info("✅ OSS 桶已就绪 ({})", settings.OSS_S3_BUCKET_NAME)
        except Exception as e:
            logger.warning("⚠️ OSS 桶初始化失败（上传时将惰性重试自建）: {}", e)

    # SSE / WebSocket topic 订阅
    await _subscribe_topics(app)

    logger.info("🎉 WalnutSeed 后端已启动: http://{}:{}", settings.SERVER_HOST, settings.SERVER_PORT)

    yield

    # ---- 关闭 ----
    try:
        await _cancel_task(getattr(app.state, "sse_sub_task", None))
        await _cancel_task(getattr(app.state, "ws_sub_task", None))
        from app.core.database import redis_connect as _rc

        await _rc(app, status=False)
        await async_engine.dispose()
        logger.info("✅ 应用已优雅关闭")
    except Exception as e:
        logger.error("❌ 应用关闭过程中发生错误: {}", e)


def register_middlewares(app: FastAPI) -> None:
    for middleware in settings.MIDDLEWARE_LIST[::-1]:
        if not middleware:
            continue
        middleware_cls = import_module(middleware, desc="中间件")
        app.add_middleware(middleware_cls)


def register_exceptions(app: FastAPI) -> None:
    handle_exception(app)


def register_routers(app: FastAPI) -> None:
    from app.api.v1.router import common_router, monitor_router, resource_router, social_router, system_router, upload_router, web_router

    app.include_router(common_router)
    app.include_router(system_router)
    app.include_router(social_router)  # 自带 /system/social 前缀
    app.include_router(monitor_router)  # 自带 /monitor/* 前缀
    app.include_router(web_router)
    # SSE 默认启用；WebSocket 按配置启用（路径始终注册，未启用时连接会因订阅未启动而仅本地回显）
    app.include_router(resource_router)
    # /upload/{key} 内联访问上传文件（对象存储流式返回）
    app.include_router(upload_router)


def register_static(app: FastAPI) -> None:
    """注册静态文件路由。"""
    path_conf.STATIC_DIR.mkdir(parents=True, exist_ok=True)
    app.mount(path=settings.STATIC_URL, app=StaticFiles(directory=path_conf.STATIC_DIR), name=path_conf.STATIC_DIR.name)


def register_docs(app: FastAPI) -> None:
    """注册 Swagger / ReDoc 文档路由。"""
    swagger_ui_redirect_url = str(app.swagger_ui_oauth2_redirect_url)
    root_openapi_url = str(app.root_path) + str(app.openapi_url)

    @app.get(swagger_ui_redirect_url, include_in_schema=False)
    async def swagger_ui_redirect():
        return get_swagger_ui_oauth2_redirect_html()

    @app.get(settings.DOCS_URL, include_in_schema=False)
    async def custom_swagger_ui_html() -> HTMLResponse:
        return get_swagger_ui_html(
            openapi_url=root_openapi_url,
            title=app.title + " - Swagger UI",
            oauth2_redirect_url=app.swagger_ui_oauth2_redirect_url,
            swagger_js_url=settings.SWAGGER_JS_URL,
            swagger_css_url=settings.SWAGGER_CSS_URL,
            swagger_favicon_url=settings.FAVICON_URL,
        )

    @app.get(settings.REDOC_URL, include_in_schema=False)
    async def custom_redoc_html():
        return get_redoc_html(
            openapi_url=root_openapi_url,
            title=app.title + " - ReDoc",
            redoc_js_url=settings.REDOC_JS_URL,
            redoc_favicon_url=settings.FAVICON_URL,
        )


def register_frontend(app: FastAPI) -> None:
    if path_conf.FRONTEND_DIST_DIR.exists():
        app.mount("/web", StaticFiles(directory=str(path_conf.FRONTEND_DIST_DIR), html=True), name="frontend")
