"""防重提交 RepeatSubmit 回归测试（fakeredis，依赖函数级直调）。

锁定的整改行为：
- key 指纹由 path + token 头 + 参数串（body+query）md5 组成；
- 同一指纹窗口内第二次请求被拒，不同 body/token/query 视为不同指纹放行；
- SETNX 带过期时间（interval 毫秒向上取整秒），窗口过期后允许再次提交；
- interval 下限保护（<1000ms 直接拒绝）。
"""

import pytest

from app.common.enums import CacheNames
from app.core.exceptions import ServiceException
from app.core.idempotent import RepeatSubmit
from app.core.redis_crud import full_key

PATH = "/order/add"
HEADERS = {"Authorization": "Bearer token-a"}
BODY = b'{"amount": 1}'


def _key_prefix() -> str:
    return full_key(f"{CacheNames.REPEAT_SUBMIT_KEY}{PATH}")


async def _all_keys(fake_redis) -> list[str]:
    return await fake_redis.keys(f"{_key_prefix()}*")


async def test_second_submit_with_same_fingerprint_rejected(fake_redis, make_request):
    dep = RepeatSubmit(interval=5000)
    await dep(make_request(path=PATH, headers=HEADERS, body=BODY), redis=fake_redis)

    with pytest.raises(ServiceException) as exc_info:
        await dep(make_request(path=PATH, headers=HEADERS, body=BODY), redis=fake_redis)
    assert "重复提交" in str(exc_info.value)

    # 窗口内防重键存在且带 TTL（5000ms -> 5s）
    keys = await _all_keys(fake_redis)
    assert len(keys) == 1
    assert 1 <= await fake_redis.ttl(keys[0]) <= 5


async def test_custom_message(fake_redis, make_request):
    dep = RepeatSubmit(interval=5000, message="请勿重复提交")
    await dep(make_request(path=PATH, headers=HEADERS, body=BODY), redis=fake_redis)
    with pytest.raises(ServiceException) as exc_info:
        await dep(make_request(path=PATH, headers=HEADERS, body=BODY), redis=fake_redis)
    assert str(exc_info.value) == "请勿重复提交"


async def test_different_body_is_distinct_fingerprint(fake_redis, make_request):
    dep = RepeatSubmit(interval=5000)
    await dep(make_request(path=PATH, headers=HEADERS, body=b'{"amount": 1}'), redis=fake_redis)
    # body 不同 -> 指纹不同 -> 放行
    await dep(make_request(path=PATH, headers=HEADERS, body=b'{"amount": 2}'), redis=fake_redis)
    assert len(await _all_keys(fake_redis)) == 2


async def test_different_token_is_distinct_fingerprint(fake_redis, make_request):
    dep = RepeatSubmit(interval=5000)
    await dep(make_request(path=PATH, headers={"Authorization": "Bearer token-a"}, body=BODY), redis=fake_redis)
    # token 头不同 -> 指纹不同 -> 放行
    await dep(make_request(path=PATH, headers={"Authorization": "Bearer token-b"}, body=BODY), redis=fake_redis)
    assert len(await _all_keys(fake_redis)) == 2


async def test_missing_token_header_fingerprint(fake_redis, make_request):
    """无 token 头也可防重（token 按空串参与指纹），第二次同参数仍被拒。"""
    dep = RepeatSubmit(interval=5000)
    await dep(make_request(path=PATH, body=BODY), redis=fake_redis)
    with pytest.raises(ServiceException):
        await dep(make_request(path=PATH, body=BODY), redis=fake_redis)


async def test_different_query_is_distinct_fingerprint(fake_redis, make_request):
    dep = RepeatSubmit(interval=5000)
    await dep(make_request(path=PATH, headers=HEADERS, query=b"id=1"), redis=fake_redis)
    await dep(make_request(path=PATH, headers=HEADERS, query=b"id=2"), redis=fake_redis)
    assert len(await _all_keys(fake_redis)) == 2


async def test_window_expired_allows_resubmit(fake_redis, make_request):
    dep = RepeatSubmit(interval=1000)  # 1s 窗口 -> TTL 1s
    await dep(make_request(path=PATH, headers=HEADERS, body=BODY), redis=fake_redis)

    keys = await _all_keys(fake_redis)
    assert len(keys) == 1
    # 模拟窗口过期（TTL 到期键消失）
    await fake_redis.delete(keys[0])

    # 过期后同指纹可再次提交
    await dep(make_request(path=PATH, headers=HEADERS, body=BODY), redis=fake_redis)
    assert len(await _all_keys(fake_redis)) == 1


async def test_interval_below_minimum_rejected(fake_redis, make_request):
    dep = RepeatSubmit(interval=999)
    with pytest.raises(ServiceException) as exc_info:
        await dep(make_request(path=PATH, headers=HEADERS, body=BODY), redis=fake_redis)
    assert "间隔时间" in str(exc_info.value)
    # 校验失败不应留下防重键
    assert await _all_keys(fake_redis) == []


async def test_distinct_paths_have_distinct_fingerprints(fake_redis, make_request):
    dep = RepeatSubmit(interval=5000)
    await dep(make_request(path="/order/add", headers=HEADERS, body=BODY), redis=fake_redis)
    # path 参与 key 组成：不同接口互不影响
    await dep(make_request(path="/order/update", headers=HEADERS, body=BODY), redis=fake_redis)
    assert len(await fake_redis.keys(f"{full_key(CacheNames.REPEAT_SUBMIT_KEY)}*")) == 2
