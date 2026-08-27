"""Redis 工具类：缓存、分布式锁、限流、发布订阅。

基于 ``redis.asyncio`` 封装：KV、SETNX、TTL、分布式锁（Lua 原子释放）、按模式删除、
发布订阅等。缓存约定：不使用注解缓存，统一显式 cache-aside（读 getOrLoad、写后 delete）。

所有 key / pattern / channel 在本类统一叠加根前缀 ``settings.REDIS_KEY_PREFIX``
（等价于 Java Redisson 的 NameMapper/KeyPrefixHandler 机制）：共用同一 Redis 实例时，
与 Java 后端（walnut-seed-java）天然隔离；业务侧一律使用不带根前缀的逻辑键。
"""

import uuid
from collections.abc import Awaitable, Callable
from typing import Any, cast

from redis.asyncio.client import Redis

from app.config.setting import settings
from app.core.logger import logger


def full_key(key: str) -> str:
    """为 key / pattern / channel 叠加根前缀（``settings.REDIS_KEY_PREFIX``），前缀为空则原样返回。"""
    prefix = settings.REDIS_KEY_PREFIX
    return f"{prefix}:{key}" if prefix else key


class RedisUtils:
    """缓存工具类。"""

    def __init__(self, redis: Redis) -> None:
        self.redis = redis

    # ---------------- KV ----------------
    async def get(self, key: str) -> Any:
        try:
            return await self.redis.get(full_key(key))
        except Exception as e:
            logger.error(f"获取缓存失败: {e!s}")
            return None

    async def set(self, key: str, value: Any, expire: int | None = None) -> bool:
        """设置缓存；``expire`` 为秒，None 表示永不过期。"""
        try:
            if expire:
                await self.redis.set(name=full_key(key), value=value, ex=expire)
            else:
                await self.redis.set(name=full_key(key), value=value)
            return True
        except Exception as e:
            logger.error(f"设置缓存失败: {e!s}")
            return False

    async def set_if_absent(self, key: str, value: Any, expire: int | None = None) -> bool:
        """SETNX，用于防重/分布式锁。"""
        try:
            result = await self.redis.set(name=full_key(key), value=value, ex=expire, nx=True)
            return result is not None and result is not False
        except Exception as e:
            logger.error(f"SETNX 失败: {e!s}")
            return False

    async def get_or_load(self, key: str, loader: Callable[[], Awaitable[Any]], expire: int | None = None) -> Any:
        """cache-aside：命中返回，未命中调用 loader 并回填。"""
        value = await self.get(key)
        if value is not None:
            return value
        value = await loader()
        if value is not None:
            await self.set(key, value, expire)
        return value

    async def delete(self, *keys: str) -> bool:
        try:
            await self.redis.delete(*(full_key(k) for k in keys))
            return True
        except Exception as e:
            logger.error(f"删除缓存失败: {e!s}")
            return False

    async def delete_by_pattern(self, pattern: str) -> int:
        try:
            count = 0
            async for key in self.redis.scan_iter(match=full_key(pattern), count=100):
                # scan 返回的已是带根前缀的物理键，直接裸删，勿再经 delete() 二次加前缀
                if await self.redis.delete(key):
                    count += 1
            return count
        except Exception as e:
            logger.error(f"按模式删除缓存失败: pattern={pattern}, err={e!s}")
            return 0

    async def exists(self, key: str) -> bool:
        try:
            return bool(await self.redis.exists(full_key(key)))
        except Exception as e:
            logger.error(f"判断缓存存在失败: {e!s}")
            return False

    has_key = exists

    async def expire(self, key: str, expire: int) -> bool:
        try:
            return bool(await self.redis.expire(name=full_key(key), time=expire))
        except Exception as e:
            logger.error(f"设置过期时间失败: {e!s}")
            return False

    async def ttl(self, key: str) -> int:
        try:
            return await self.redis.ttl(full_key(key))
        except Exception as e:
            logger.error(f"获取过期时间失败: {e!s}")
            return -1

    async def keys(self, pattern: str = "*") -> list:
        """获取逻辑键名（SCAN 实现，不阻塞；返回值已剥离根前缀）。"""
        try:
            prefix = settings.REDIS_KEY_PREFIX
            keys: list = []
            async for key in self.redis.scan_iter(match=full_key(pattern), count=1000):
                keys.append(key.removeprefix(f"{prefix}:") if prefix else key)
            return keys
        except Exception as e:
            logger.error(f"扫描缓存键名失败: {e!s}")
            return []

    async def mget(self, keys: list) -> list:
        try:
            return await self.redis.mget(*[full_key(str(k)) for k in keys])
        except Exception as e:
            logger.error(f"批量获取缓存失败: {e!s}")
            return []

    # ---------------- 分布式锁 ----------------
    async def lock(self, key: str, expire: int = 30, value: str | None = None) -> tuple[bool, str]:
        """获取分布式锁，返回 (是否成功, 锁值)。"""
        try:
            lock_value = value or str(uuid.uuid4())
            result = await self.redis.set(name=full_key(key), value=lock_value, ex=expire, nx=True)
            return (result is not None and result is not False, lock_value)
        except Exception as e:
            logger.error(f"获取分布式锁失败: {e!s}")
            return (False, "")

    async def unlock(self, key: str, value: str) -> bool:
        """释放分布式锁（Lua 原子校验锁值后删除）。"""
        try:
            script = "if redis.call('get', KEYS[1]) == ARGV[1] then return redis.call('del', KEYS[1]) else return 0 end"
            result = await cast("Awaitable[int]", self.redis.eval(script, 1, full_key(key), value))
            return result == 1
        except Exception as e:
            logger.error(f"释放分布式锁失败: {e!s}")
            return False

    async def renew_lock(self, key: str, expire: int, value: str) -> bool:
        try:
            script = "if redis.call('get', KEYS[1]) == ARGV[1] then return redis.call('expire', KEYS[1], ARGV[2]) else return 0 end"
            result = await cast("Awaitable[int]", self.redis.eval(script, 1, full_key(key), value, str(expire)))
            return result == 1
        except Exception as e:
            logger.error(f"续约分布式锁失败: {e!s}")
            return False

    # ---------------- Hash ----------------
    async def hash_set(self, name: str, key: str, value: Any) -> bool:
        try:
            await cast("Awaitable[int]", self.redis.hset(name=full_key(name), key=key, value=value))
            return True
        except Exception as e:
            logger.error(f"设置哈希缓存失败: {e!s}")
            return False

    async def hash_get(self, name: str, keys: list[str]) -> list[Any]:
        try:
            return await cast("Awaitable[list[Any]]", self.redis.hmget(name=full_key(name), keys=keys))
        except Exception as e:
            logger.error(f"获取哈希缓存失败: {e!s}")
            return []

    # ---------------- 发布订阅 ----------------
    async def publish(self, channel: str, message: str) -> int:
        try:
            return await self.redis.publish(full_key(channel), message)
        except Exception as e:
            logger.error(f"Redis 发布消息失败: channel={channel}, err={e!s}")
            return 0

    async def subscribe(self, channel: str, consumer: Callable[[str], Awaitable[None]]) -> None:
        """订阅频道并持续消费（阻塞循环，需在后台任务中运行）。

        socket_timeout 会导致 listen() 在无消息时超时，此处自动重连避免退出。
        """
        import asyncio

        from redis import exceptions as redis_exc

        channel = full_key(channel)
        retry_delay = 1  # 初始重试间隔（秒），指数退避上限 30s
        while True:
            pubsub = self.redis.pubsub()
            try:
                await pubsub.subscribe(channel)
                retry_delay = 1  # 订阅成功，重置退避
                async for message in pubsub.listen():
                    if message.get("type") != "message":
                        continue
                    data = message.get("data")
                    if data is None:
                        continue
                    try:
                        await consumer(data if isinstance(data, str) else data.decode("utf-8"))
                    except Exception:
                        logger.exception("Redis 订阅消费异常: channel={}", channel)
            except asyncio.CancelledError:
                logger.info("Redis 订阅任务已取消: channel={}", channel)
                break
            except redis_exc.TimeoutError:
                logger.debug("Redis 订阅超时（无消息），自动重新订阅: channel={}", channel)
                continue
            except redis_exc.RedisError as e:
                logger.warning("Redis 订阅异常，{:.0f}s 后重试: channel={}, err={}", retry_delay, channel, e)
                await asyncio.sleep(retry_delay)
                retry_delay = min(retry_delay * 2, 30)
            except Exception as e:
                logger.error("Redis 订阅未知错误，{:.0f}s 后重试: channel={}, err={}", retry_delay, channel, e)
                await asyncio.sleep(retry_delay)
                retry_delay = min(retry_delay * 2, 30)
            finally:
                try:
                    await pubsub.unsubscribe(channel)
                except Exception:
                    pass
                close_fn = getattr(pubsub, "aclose", None) or pubsub.close
                try:
                    await close_fn()
                except Exception:
                    pass

    # ---------------- 信息 ----------------
    async def info(self) -> dict:
        try:
            return await self.redis.info()
        except Exception as e:
            logger.error(f"获取缓存信息失败: {e!s}")
            return {}

    async def db_size(self) -> int:
        try:
            return await self.redis.dbsize()
        except Exception as e:
            logger.error(f"获取数据库大小失败: {e!s}")
            return 0
