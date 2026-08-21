"""接口限流。

以路由依赖形式使用：
    @router.get("/list", dependencies=[Depends(RateLimiter(time=60, count=100))])

Key 组成：``global:rate_limit:{请求URI}[:{ip}|:{instance}]:{key}``。
采用固定窗口计数：INCR + TTL 通过单条 Lua 脚本原子执行
（首次计数设置 TTL；TTL 缺失的历史键补设 TTL），
消除 INCR 与 EXPIRE 之间崩溃导致 key 永久无 TTL 的竞态。
"""

import uuid
from enum import Enum

from fastapi import Depends, Request

from app.common.enums import CacheNames
from app.core.dependencies import redis_getter
from app.core.exceptions import ServiceException
from app.core.logger import logger
from app.core.redis_crud import RedisUtils
from app.utils.common_util import get_client_ip
from app.utils.i18n import MessageUtils

# 实例ID（CLUSTER 限流用）
_INSTANCE_ID = uuid.uuid4().hex[:8]

# 原子计数脚本：INCR 后若为首次计数则设置 TTL；若键存在但无 TTL（历史竞态遗留）则补设
_RATE_LIMIT_LUA = """
local current = redis.call('INCR', KEYS[1])
if current == 1 or redis.call('TTL', KEYS[1]) == -1 then
    redis.call('EXPIRE', KEYS[1], ARGV[1])
end
return current
"""


class LimitType(str, Enum):
    """限流类型。"""

    DEFAULT = "DEFAULT"  # 全局
    IP = "IP"  # 按请求IP
    CLUSTER = "CLUSTER"  # 按后端实例


class RateLimiter:
    """限流依赖。

    - ``key``：附加键（可用路径参数/表达式结果，缺省为空）；
    - ``time``：时间窗口（秒），默认 60；
    - ``count``：窗口内最大请求数，默认 100；
    - ``limit_type``：DEFAULT/IP/CLUSTER；
    - ``message``：自定义提示，缺省使用 i18n ``rate.limiter.message``。
    """

    def __init__(
        self,
        key: str = "",
        time: int = 60,
        count: int = 100,
        limit_type: LimitType = LimitType.DEFAULT,
        message: str | None = None,
    ) -> None:
        self.key = key
        self.time = time
        self.count = count
        self.limit_type = limit_type
        self.message = message

    def _combine_key(self, request: Request) -> str:
        parts = [CacheNames.RATE_LIMIT_KEY, request.url.path]
        if self.limit_type == LimitType.IP:
            parts.append(f"{get_client_ip(request)}:")
        elif self.limit_type == LimitType.CLUSTER:
            parts.append(f"{_INSTANCE_ID}:")
        if self.key:
            parts.append(self.key)
        return "".join(parts)

    async def __call__(self, request: Request, redis=Depends(redis_getter)) -> None:
        combine_key = self._combine_key(request)
        r = RedisUtils(redis)
        try:
            current = await r.redis.eval(_RATE_LIMIT_LUA, 1, combine_key, self.time)
        except Exception as e:
            # Redis 故障时 fail-closed：拒绝请求而非放行
            logger.error("限流器异常: {}", e)
            raise ServiceException("服务器限流异常，请稍候再试")

        if current > self.count:
            msg = self.message or MessageUtils.message("rate.limiter.message")
            logger.warning("限流拦截: {} {} | key={}", request.method, request.url.path, combine_key)
            raise ServiceException(msg)
        logger.debug("限制令牌 => {}, 剩余令牌 => {}, 缓存key => '{}'", self.count, self.count - current, combine_key)
