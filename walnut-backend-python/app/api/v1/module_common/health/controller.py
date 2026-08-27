import asyncio
import shutil
import time
from datetime import datetime

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.common.response import ErrorResponse, SuccessResponse
from app.config.setting import settings
from app.core.database import async_db_session
from app.core.logger import logger
from app.core.router_class import OperationLogRoute

from .schema import DependencyStatus, HealthOut, ReadinessOut

HealthRouter = APIRouter(route_class=OperationLogRoute, prefix="/health", tags=["健康检查"])

_start_time = datetime.now()


async def _check_database() -> DependencyStatus:
    try:
        start = time.perf_counter()
        async with async_db_session() as session:
            await session.execute(text("SELECT 1"))
        latency = (time.perf_counter() - start) * 1000
        return DependencyStatus(status=1, latency_ms=round(latency, 2))
    except Exception as e:
        logger.warning(f"数据库健康检查失败: {e}")
        return DependencyStatus(status=0)


async def _check_redis(request: Request) -> DependencyStatus:
    try:
        redis = getattr(request.app.state, "redis", None)
        if not redis:
            return DependencyStatus(status=0)
        start = time.perf_counter()
        await redis.ping()
        latency = (time.perf_counter() - start) * 1000
        return DependencyStatus(status=1, latency_ms=round(latency, 2))
    except Exception as e:
        logger.warning(f"Redis 健康检查失败: {e}")
        return DependencyStatus(status=0)


def _get_disk_usage() -> float:
    try:
        usage = shutil.disk_usage("/")
        return round(usage.used / usage.total * 100, 1)
    except Exception:
        return -1.0


def _base_payload() -> dict:
    return {
        "timestamp": datetime.now().isoformat(),
        "version": settings.VERSION,
        "uptime_seconds": (datetime.now() - _start_time).total_seconds(),
    }


@HealthRouter.get("/check", summary="健康检查")
async def health_check() -> JSONResponse:
    return SuccessResponse(data=HealthOut(status=1, **_base_payload()), msg="系统健康")


@HealthRouter.get("/live", summary="存活探针")
async def liveness_check() -> JSONResponse:
    return SuccessResponse(data=HealthOut(status=1, **_base_payload()), msg="进程存活")


@HealthRouter.get("/ready", summary="就绪探针")
async def readiness_check(request: Request) -> JSONResponse:
    db_status, redis_status = await asyncio.gather(_check_database(), _check_redis(request))
    dependencies = {"database": db_status, "redis": redis_status}
    all_ok = all(d.status == 1 for d in dependencies.values())
    payload = ReadinessOut(status=1 if all_ok else 0, dependencies=dependencies, disk_usage=_get_disk_usage(), **_base_payload())
    if all_ok:
        return SuccessResponse(data=payload, msg="依赖就绪")
    return ErrorResponse(data=payload, msg="依赖未就绪", code=503, status_code=503)
