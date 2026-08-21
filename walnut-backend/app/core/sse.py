"""SSE 管理器。

每连接一个 asyncio.Queue + 异步生成器：
- 每个用户可多连接（按 token 区分）；
- 空闲 60 秒发送 heartbeat 事件；
- 通过 Redis pub/sub（topic ``global:sse``）跨实例分发。
"""

import asyncio
import json
from collections.abc import AsyncIterator

from app.common.dataclasses import SseMessageDto
from app.common.enums import CacheNames
from app.core.logger import logger

_HEARTBEAT_INTERVAL = 60  # 秒


class SseEmitterManager:
    """SSE 连接管理器。"""

    SSE_TOPIC = CacheNames.SSE_TOPIC

    def __init__(self) -> None:
        # userId -> {token -> asyncio.Queue}
        self._user_queues: dict[int, dict[str, asyncio.Queue]] = {}

    def connect(self, user_id: int, token: str) -> AsyncIterator:
        """建立 SSE 连接，返回事件异步生成器。"""
        queue: asyncio.Queue = asyncio.Queue()
        self._user_queues.setdefault(user_id, {})[token] = queue
        logger.info("SSE 连接建立: userId={}", user_id)

        async def event_stream():
            try:
                # 初始连接事件
                yield {"event": "connected", "data": ""}
                while True:
                    try:
                        message = await asyncio.wait_for(queue.get(), timeout=_HEARTBEAT_INTERVAL)
                        yield {"event": "message", "data": message}
                    except TimeoutError:
                        # 心跳
                        yield {"event": "heartbeat", "data": ""}
            except asyncio.CancelledError:
                raise
            finally:
                self._remove(user_id, token)

        return event_stream()

    def _remove(self, user_id: int, token: str) -> None:
        tokens = self._user_queues.get(user_id)
        if tokens and token in tokens:
            del tokens[token]
            if not tokens:
                self._user_queues.pop(user_id, None)

    def disconnect(self, user_id: int, token: str) -> None:
        """断开连接。"""
        self._remove(user_id, token)
        logger.info("SSE 连接断开: userId={}", user_id)

    def send_message(self, user_id: int, message: str) -> None:
        """向指定用户的所有连接推送。"""
        for queue in self._user_queues.get(user_id, {}).values():
            queue.put_nowait(message)

    def broadcast(self, message: str) -> None:
        """向本实例所有连接广播。"""
        for user_id in list(self._user_queues):
            self.send_message(user_id, message)

    async def publish_message(self, redis, dto: SseMessageDto) -> None:
        """发布消息到 Redis topic（跨实例）。"""
        from app.core.redis_crud import RedisUtils

        payload = json.dumps({"user_ids": dto.user_ids, "message": dto.message}, ensure_ascii=False)
        await RedisUtils(redis).publish(self.SSE_TOPIC, payload)

    async def publish_all(self, redis, message: str) -> None:
        """广播。"""
        await self.publish_message(redis, SseMessageDto(user_ids=[], message=message))

    async def on_topic_message(self, raw: str) -> None:
        """Redis topic 消费回调。"""
        try:
            data = json.loads(raw)
            dto = SseMessageDto(user_ids=data.get("user_ids", []), message=data.get("message", ""))
        except Exception:
            logger.warning("SSE topic 消息解析失败: {}", raw)
            return
        if dto.user_ids:
            for uid in dto.user_ids:
                self.send_message(uid, dto.message)
        else:
            self.broadcast(dto.message)


# 全局单例（由 lifespan 初始化订阅）
sse_manager = SseEmitterManager()
