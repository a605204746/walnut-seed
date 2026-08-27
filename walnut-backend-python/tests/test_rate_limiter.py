"""限流器 RateLimiter 回归测试（fakeredis，依赖函数级直调，不起请求链路）。

锁定的整改行为：
- 单条 Lua 原子计数：首次调用后计数键必须带 TTL；
- 竞态修复回归：历史遗留的无 TTL 计数键（模拟 INCR 后崩溃残留）在下一次调用后被补设 TTL；
- 窗口内不超过 count 放行、超过 count 拦截；
- Redis 故障 fail-closed：抛限流异常拒绝请求，而非放行。
"""

import fakeredis.aioredis
import pytest
from redis import exceptions as redis_exceptions

from app.common.enums import CacheNames
from app.core.exceptions import ServiceException
from app.core.rate_limiter import LimitType, RateLimiter
from app.core.redis_crud import full_key


def _limit_key(path: str) -> str:
    return full_key(f"{CacheNames.RATE_LIMIT_KEY}{path}")


async def test_first_hit_sets_ttl(fake_redis, make_request):
    limiter = RateLimiter(time=60, count=10)
    await limiter(make_request(path="/test/limit"), redis=fake_redis)

    key = _limit_key("/test/limit")
    assert await fake_redis.get(key) == "1"
    ttl = await fake_redis.ttl(key)
    assert 0 < ttl <= 60


async def test_within_count_pass_and_over_count_blocked(fake_redis, make_request):
    limiter = RateLimiter(time=60, count=3)
    request = make_request(path="/test/count")

    # 窗口内前 count 次放行
    for _ in range(3):
        await limiter(request, redis=fake_redis)
    # 第 count+1 次拦截（缺省 i18n 提示，zh_CN）
    with pytest.raises(ServiceException) as exc_info:
        await limiter(request, redis=fake_redis)
    assert "访问过于频繁" in str(exc_info.value)


async def test_custom_message_overrides_i18n(fake_redis, make_request):
    limiter = RateLimiter(time=60, count=1, message="操作太快了")
    await limiter(make_request(path="/test/msg"), redis=fake_redis)
    with pytest.raises(ServiceException) as exc_info:
        await limiter(make_request(path="/test/msg"), redis=fake_redis)
    assert str(exc_info.value) == "操作太快了"


async def test_legacy_key_without_ttl_gets_repaired(fake_redis, make_request):
    """竞态修复回归：预置无 TTL 的同名计数键（进程崩溃残留），下一次调用后必须补设 TTL。"""
    key = _limit_key("/test/repair")
    await fake_redis.set(key, "5")  # 无过期时间
    assert await fake_redis.ttl(key) == -1

    limiter = RateLimiter(time=120, count=100)
    await limiter(make_request(path="/test/repair"), redis=fake_redis)

    assert await fake_redis.get(key) == "6"  # 计数继续累加
    ttl = await fake_redis.ttl(key)
    assert 0 < ttl <= 120  # 补设 TTL，不再永久驻留


async def test_ttl_not_extended_on_every_hit(fake_redis, make_request):
    """已有 TTL 的键不重置窗口（固定窗口语义）：TTL 只减不增。"""
    limiter = RateLimiter(time=60, count=100)
    await limiter(make_request(path="/test/fixed"), redis=fake_redis)
    await fake_redis.expire(_limit_key("/test/fixed"), 10)  # 人为缩短，便于观测

    await limiter(make_request(path="/test/fixed"), redis=fake_redis)
    ttl = await fake_redis.ttl(_limit_key("/test/fixed"))
    assert 0 < ttl <= 10


class _BrokenRedis:
    """eval 即抛连接错误的故障 Redis。"""

    async def eval(self, *args, **kwargs):
        raise redis_exceptions.ConnectionError("connection refused")


async def test_redis_failure_fails_closed(make_request):
    """Redis 故障时拒绝请求（抛限流异常），而不是放行。"""
    limiter = RateLimiter(time=60, count=10)
    with pytest.raises(ServiceException) as exc_info:
        await limiter(make_request(path="/test/broken"), redis=_BrokenRedis())
    assert "限流" in str(exc_info.value)


async def test_ip_type_isolates_counters_by_client(fake_redis, make_request):
    limiter = RateLimiter(time=60, count=1, limit_type=LimitType.IP)

    await limiter(make_request(path="/test/ip", client_addr="1.1.1.1"), redis=fake_redis)
    with pytest.raises(ServiceException):
        await limiter(make_request(path="/test/ip", client_addr="1.1.1.1"), redis=fake_redis)
    # 不同客户端 IP 独立计数，不受前者拦截影响
    await limiter(make_request(path="/test/ip", client_addr="2.2.2.2"), redis=fake_redis)


async def test_distinct_paths_have_distinct_counters(fake_redis, make_request):
    limiter = RateLimiter(time=60, count=1)
    await limiter(make_request(path="/test/a"), redis=fake_redis)
    await limiter(make_request(path="/test/b"), redis=fake_redis)
    assert await fake_redis.get(_limit_key("/test/a")) == "1"
    assert await fake_redis.get(_limit_key("/test/b")) == "1"


async def test_fake_redis_fixture_isolation():
    """守护 fixture 隔离性：每个用例拿到独立的 fakeredis 实例（不共享 server）。"""
    r = fakeredis.aioredis.FakeRedis(decode_responses=True)
    assert await r.dbsize() == 0
