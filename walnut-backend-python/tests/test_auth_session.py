"""认证会话契约测试：dependencies._authenticate 的 Redis 会话加载与滑动续期（fakeredis）。

锁定的整改行为：
- 会话加载：JWT 解析后从 Redis ``user_session:<会话ID>`` 读取登录信息，缺失/损坏/停用均拒绝；
- 刷新令牌（is_refresh）不得当作访问令牌使用；
- 滑动续期：启用 TOKEN_SLIDING_EXPIRE 时，会话键 TTL 过半程即续期会话键与令牌键
  （两者保持同生命周期）；未过半程或停用滑动过期时不续期。
"""

import json
from datetime import UTC, datetime, timedelta

import pytest

from app.common.enums import CacheNames, RedisInitKeyConfig
from app.config.setting import settings
from app.core.base_schema import JWTPayloadSchema
from app.core.dependencies import _authenticate
from app.core.exceptions import NotLoginException
from app.core.redis_crud import full_key
from app.core.security import create_access_token

SESSION_ID = "sess-001"
SESSION_KEY = full_key(f"{RedisInitKeyConfig.USER_SESSION.key}:{SESSION_ID}")
ACCESS_KEY = full_key(f"{RedisInitKeyConfig.ACCESS_TOKEN.key}:{SESSION_ID}")
ACTIVE_TIMEOUT = 1800


def _issue_token(**overrides) -> str:
    payload_data = {
        "sub": SESSION_ID,
        "user_id": 2,
        "user_name": "tester",
        "exp": datetime.now(UTC) + timedelta(days=1),
    }
    payload_data.update(overrides)
    payload = JWTPayloadSchema(
        **payload_data,
    )
    return create_access_token(payload)


def _session_json(**overrides) -> str:
    data = {
        "user_id": 2,
        "user_name": "tester",
        "nickname": "T",
        "user_status": "0",
        "menu_permission": ["system:user:list"],
        "role_permission": ["admin"],
        "menu_ids": [1],
        "_active_timeout": ACTIVE_TIMEOUT,
    }
    data.update(overrides)
    return json.dumps(data)


async def _seed_session(fake_redis, ttl: int) -> None:
    await fake_redis.set(SESSION_KEY, _session_json(), ex=ttl)
    await fake_redis.set(ACCESS_KEY, "token-meta", ex=ttl)


# ---------- 会话加载 ----------


async def test_authenticate_loads_session(fake_redis, make_request):
    await _seed_session(fake_redis, ttl=3600)
    auth = await _authenticate(make_request(path="/me"), _issue_token(), fake_redis)
    assert auth.user.id == 2
    assert auth.user.username == "tester"
    assert auth.permissions == ["system:user:list"]
    assert auth.roles == ["admin"]
    # 挂载到 request.state 供后续链路使用
    request = make_request(path="/me")
    await _authenticate(request, _issue_token(), fake_redis)
    assert request.state.login_user["user_name"] == "tester"


async def test_missing_session_rejected(fake_redis, make_request):
    with pytest.raises(NotLoginException):
        await _authenticate(make_request(path="/me"), _issue_token(), fake_redis)


async def test_corrupt_session_rejected(fake_redis, make_request):
    await fake_redis.set(SESSION_KEY, "{not-json", ex=3600)
    with pytest.raises(NotLoginException):
        await _authenticate(make_request(path="/me"), _issue_token(), fake_redis)


async def test_refresh_token_rejected_as_access_token(fake_redis, make_request):
    await _seed_session(fake_redis, ttl=3600)
    with pytest.raises(NotLoginException):
        await _authenticate(make_request(path="/me"), _issue_token(is_refresh=True), fake_redis)


async def test_disabled_user_rejected(fake_redis, make_request):
    await fake_redis.set(SESSION_KEY, _session_json(user_status="1"), ex=3600)
    with pytest.raises(NotLoginException):
        await _authenticate(make_request(path="/me"), _issue_token(), fake_redis)


async def test_empty_token_rejected(fake_redis, make_request):
    with pytest.raises(NotLoginException):
        await _authenticate(make_request(path="/me"), "", fake_redis)


# ---------- 滑动续期 ----------


async def test_sliding_refresh_when_ttl_past_halfway(fake_redis, make_request, monkeypatch):
    monkeypatch.setattr(settings, "TOKEN_SLIDING_EXPIRE", True)
    await _seed_session(fake_redis, ttl=600)  # 远低于 active_timeout 的半程
    token = _issue_token()
    online_key = full_key(f"{CacheNames.ONLINE_TOKEN_KEY}{token}")
    await fake_redis.set(online_key, "online-meta", ex=600)

    await _authenticate(make_request(path="/me"), token, fake_redis)

    # 会话键与令牌键同时续期回 active_timeout，而不是全局默认值
    assert await fake_redis.ttl(SESSION_KEY) >= ACTIVE_TIMEOUT - 5
    assert await fake_redis.ttl(ACCESS_KEY) >= ACTIVE_TIMEOUT - 5
    # 在线用户缓存也必须保持相同生命周期
    assert await fake_redis.ttl(online_key) >= ACTIVE_TIMEOUT - 5


async def test_no_refresh_before_halfway(fake_redis, make_request, monkeypatch):
    monkeypatch.setattr(settings, "TOKEN_SLIDING_EXPIRE", True)
    seeded = ACTIVE_TIMEOUT - 600  # 未过半程
    await _seed_session(fake_redis, ttl=seeded)

    await _authenticate(make_request(path="/me"), _issue_token(), fake_redis)

    ttl = await fake_redis.ttl(SESSION_KEY)
    assert ttl <= seeded  # 未续期（允许少量自然流逝）
    assert ttl > seeded - 60


async def test_no_refresh_when_sliding_disabled(fake_redis, make_request, monkeypatch):
    monkeypatch.setattr(settings, "TOKEN_SLIDING_EXPIRE", False)
    await _seed_session(fake_redis, ttl=3600)

    await _authenticate(make_request(path="/me"), _issue_token(), fake_redis)

    assert await fake_redis.ttl(SESSION_KEY) <= 3600  # 未续期
    assert await fake_redis.ttl(ACCESS_KEY) <= 3600


async def test_sliding_refresh_never_exceeds_jwt_hard_expiry(fake_redis, make_request, monkeypatch):
    monkeypatch.setattr(settings, "TOKEN_SLIDING_EXPIRE", True)
    hard_expire_seconds = 30
    await _seed_session(fake_redis, ttl=5)
    token = _issue_token(exp=datetime.now(UTC) + timedelta(seconds=hard_expire_seconds))

    await _authenticate(make_request(path="/me"), token, fake_redis)

    # 续期不能超过 JWT 的固定 exp，即使 active_timeout 更长。
    ttl = await fake_redis.ttl(SESSION_KEY)
    assert 0 < ttl <= hard_expire_seconds


async def test_expired_jwt_rejected_when_sliding_enabled(fake_redis, make_request, monkeypatch):
    monkeypatch.setattr(settings, "TOKEN_SLIDING_EXPIRE", True)
    await _seed_session(fake_redis, ttl=ACTIVE_TIMEOUT)
    token = _issue_token(exp=datetime.now(UTC) - timedelta(seconds=1))

    with pytest.raises(NotLoginException):
        await _authenticate(make_request(path="/me"), token, fake_redis)
