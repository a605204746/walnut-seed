import re
from datetime import date, datetime, time
from decimal import Decimal
from typing import Any

from fastapi import FastAPI
from redis import exceptions
from redis.asyncio import Redis
from sqlalchemy import Engine, create_engine, event
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.config.setting import settings
from app.core.logger import logger

# ================================================= #
# ********* 完整 SQL 日志 ********* #
# ================================================= #


def _render_sql_literal(value: Any) -> str:
    """将参数值渲染为 SQL 字面量（仅开发调试用途）。"""
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, (int, float, Decimal)):
        return str(value)
    if isinstance(value, (bytes, bytearray, memoryview)):
        return f"X'{bytes(value).hex()}'"
    if isinstance(value, datetime):
        return f"'{value:%Y-%m-%d %H:%M:%S}'"
    if isinstance(value, date):
        return f"'{value:%Y-%m-%d}'"
    if isinstance(value, time):
        return f"'{value:%H:%M:%S}'"
    return "'{}'".format(str(value).replace("'", "''"))


def _interpolate_sql(statement: str, parameters: Any, executemany: bool) -> str:
    """将参数填充进占位符生成完整 SQL（驱动不支持 mogrify 时的兜底）。"""
    try:
        if executemany:
            return f"{statement}  -- [executemany, {len(parameters)} 行]"
        if isinstance(parameters, dict):
            # pyformat（%(name)s）与 named（:name）两种风格
            return re.sub(
                r"%\(([A-Za-z_][A-Za-z0-9_]*)\)s|:([A-Za-z_][A-Za-z0-9_]*)",
                lambda m: _render_sql_literal(parameters.get(m.group(1) or m.group(2))),
                statement,
            )
        if isinstance(parameters, (list, tuple)):
            # MySQL 方言为 format 风格（%s），(?<!%) 避开转义的 %%
            it = iter(parameters)
            return re.sub(r"(?<!%)%s", lambda _m: _render_sql_literal(next(it)), statement)
        return f"{statement}  -- params: {parameters!r}"
    except Exception:
        return f"{statement}  -- params: {parameters!r}"


def _register_sql_logging(sync_engine: Engine) -> None:
    """注册完整 SQL 日志监听：一条日志输出参数填充后的完整 SQL。

    支持 cursor.mogrify 的驱动（aiomysql/pymysql）直接渲染完整 SQL；
    不支持的驱动回退为手动填充占位符（仅开发调试用途）。
    """

    @event.listens_for(sync_engine, "before_cursor_execute")
    def _before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        complete_sql = ""
        mogrify = getattr(cursor, "mogrify", None)
        if callable(mogrify):
            try:
                rendered = mogrify(statement, parameters)
                complete_sql = rendered.decode("utf-8", errors="replace") if isinstance(rendered, bytes) else str(rendered)
            except Exception:
                complete_sql = ""
        if not complete_sql:
            complete_sql = _interpolate_sql(statement, parameters, executemany)
        logger.info("📝 执行 SQL: {}", complete_sql)


def _native_echo() -> bool | str:
    """SQLAlchemy 原生 echo：仅 debug 模式开启（True 模式由完整 SQL 监听输出，避免重复）。"""
    return "debug" if settings.DATABASE_ECHO == "debug" else False


def create_engine_and_session(db_url: str = settings.DB_URI) -> tuple[Engine, sessionmaker]:
    """创建同步数据库引擎和会话工厂（供 alembic 迁移使用）。"""
    try:
        engine: Engine = create_engine(
            url=db_url,
            echo=_native_echo(),
            pool_pre_ping=settings.POOL_PRE_PING,
            pool_recycle=settings.POOL_RECYCLE,
        )
    except Exception as e:
        logger.error(f"❌ 数据库连接失败 {e}")
        raise
    else:
        if settings.DATABASE_ECHO:
            _register_sql_logging(engine)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        return engine, SessionLocal


def create_async_engine_and_session(db_url: str = settings.ASYNC_DB_URI) -> tuple[AsyncEngine, async_sessionmaker[AsyncSession]]:
    """创建异步数据库引擎和会话工厂。"""
    try:
        async_engine = create_async_engine(
            url=db_url,
            echo=_native_echo(),
            echo_pool=settings.ECHO_POOL,
            pool_pre_ping=settings.POOL_PRE_PING,
            pool_recycle=settings.POOL_RECYCLE,
            pool_size=settings.POOL_SIZE,
            max_overflow=settings.MAX_OVERFLOW,
            pool_timeout=settings.POOL_TIMEOUT,
            pool_use_lifo=True,
        )
    except Exception as e:
        logger.error(f"❌ 数据库连接失败 {e}")
        raise
    else:
        if settings.DATABASE_ECHO:
            _register_sql_logging(async_engine.sync_engine)
        AsyncSessionLocal = async_sessionmaker[AsyncSession](
            bind=async_engine,
            autocommit=settings.AUTOCOMMIT,
            autoflush=settings.AUTOFLUSH,
            expire_on_commit=settings.EXPIRE_ON_COMMIT,
            class_=AsyncSession,
        )
        return async_engine, AsyncSessionLocal


engine, db_session = create_engine_and_session()
async_engine, async_db_session = create_async_engine_and_session()


async def redis_connect(app: FastAPI, status: bool) -> Redis | None:
    """创建或关闭 Redis 连接（启动时创建连接，关闭时释放）。

    连接失败时不中断启动（返回 None），认证/缓存等依赖 Redis 的能力将不可用，
    但健康检查等接口仍可访问。
    """
    if status:
        try:
            rd = await Redis.from_url(
                url=settings.REDIS_URI,
                encoding="utf-8",
                decode_responses=True,
                health_check_interval=settings.REDIS_HEALTH_CHECK_INTERVAL,
                max_connections=settings.POOL_SIZE,
                socket_timeout=settings.POOL_TIMEOUT,
            )
            if await rd.ping():  # pyright: ignore[reportGeneralTypeIssues]
                app.state.redis = rd
                return rd
            return None
        except exceptions.AuthenticationError as e:
            logger.error(f"❌ Redis 认证失败: {e}")
            return None
        except exceptions.TimeoutError as e:
            logger.error(f"❌ Redis 连接超时: {e}")
            return None
        except exceptions.ConnectionError as e:
            logger.warning(f"⚠️ Redis 连接失败（应用继续运行，认证/缓存不可用）: {e}")
            return None
        except exceptions.RedisError as e:
            logger.error(f"❌ Redis 连接错误: {e}")
            return None
    else:
        rd = getattr(app.state, "redis", None)
        if rd is not None:
            close_fn = getattr(rd, "aclose", None) or rd.close
            await close_fn()
            logger.info("✅️ Redis 连接已关闭")
        return None
