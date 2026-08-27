"""WebSocket 会话管理与工具。

FastAPI 侧每个 WebSocket 连接由路由处理函数持有；此处维护 userId -> WebSocket
的会话表，并通过 Redis pub/sub（topic ``global:websocket``）跨实例分发消息。
"""

import json

from fastapi import WebSocket

from app.common.dataclasses import WebSocketMessageDto
from app.common.enums import CacheNames
from app.core.logger import logger

LOGIN_USER_KEY = "loginUser"
WEB_SOCKET_TOPIC = CacheNames.WEB_SOCKET_TOPIC
PING = "ping"
PONG = "pong"


class WebSocketSessionHolder:
    """会话持有器（一用户一会话）。"""

    _sessions: dict[int, WebSocket] = {}

    @classmethod
    def add_session(cls, key: int, session: WebSocket) -> None:
        old = cls._sessions.get(key)
        if old is not None:
            try:
                # 新连接替换旧连接
                pass
            except Exception:
                pass
        cls._sessions[key] = session

    @classmethod
    def remove_session(cls, key: int) -> None:
        cls._sessions.pop(key, None)

    @classmethod
    def get_session(cls, key: int) -> WebSocket | None:
        return cls._sessions.get(key)

    @classmethod
    def get_sessions_all(cls) -> list[int]:
        return list(cls._sessions)

    @classmethod
    def exist_session(cls, key: int) -> bool:
        return key in cls._sessions


class WebSocketUtils:
    """WebSocket 工具。"""

    @staticmethod
    async def send_message(session_key: int, message: str) -> None:
        session = WebSocketSessionHolder.get_session(session_key)
        if session is None:
            return
        try:
            await session.send_text(message)
        except Exception as e:
            logger.warning("[send] WebSocket 发送失败/会话已关闭: {}", e)

    @staticmethod
    async def publish_message(redis, dto: WebSocketMessageDto) -> None:
        """本地存在的会话直接发送，其余发布到 Redis topic。"""
        local_keys = [k for k in dto.session_keys if WebSocketSessionHolder.exist_session(k)]
        remote_keys = [k for k in dto.session_keys if not WebSocketSessionHolder.exist_session(k)]
        for key in local_keys:
            await WebSocketUtils.send_message(key, dto.message)
        if remote_keys or not dto.session_keys:
            from app.core.redis_crud import RedisUtils

            payload = json.dumps({"session_keys": remote_keys, "message": dto.message}, ensure_ascii=False)
            await RedisUtils(redis).publish(WEB_SOCKET_TOPIC, payload)

    @staticmethod
    async def publish_all(redis, message: str) -> None:
        await WebSocketUtils.publish_message(redis, WebSocketMessageDto(session_keys=[], message=message))

    @staticmethod
    async def on_topic_message(raw: str) -> None:
        """Redis topic 消费回调。"""
        try:
            data = json.loads(raw)
            dto = WebSocketMessageDto(session_keys=data.get("session_keys", []), message=data.get("message", ""))
        except Exception:
            logger.warning("WebSocket topic 消息解析失败: {}", raw)
            return
        if dto.session_keys:
            for key in dto.session_keys:
                if WebSocketSessionHolder.exist_session(key):
                    await WebSocketUtils.send_message(key, dto.message)
        else:
            for key in WebSocketSessionHolder.get_sessions_all():
                await WebSocketUtils.send_message(key, dto.message)
