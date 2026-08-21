"""资源模块：SSE 与 WebSocket 实时通道。

路径：``/resource/sse``、``/resource/sse/close``、``/resource/websocket``。
"""

import json
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, WebSocket, WebSocketDisconnect
from fastapi.sse import EventSourceResponse, ServerSentEvent

from app.common.dataclasses import WebSocketMessageDto
from app.common.response import SuccessResponse
from app.config.setting import settings
from app.core.base_schema import AuthSchema
from app.core.dependencies import get_current_user
from app.core.logger import logger
from app.core.redis_crud import RedisUtils
from app.core.security import OAuth2Schema, decode_access_token
from app.core.sse import sse_manager
from app.core.websocket import PING, PONG, WebSocketSessionHolder, WebSocketUtils

ResourceRouter = APIRouter(prefix="/resource", tags=["资源(SSE/WebSocket)"])


# ==================== SSE ====================


@ResourceRouter.get("/sse", summary="SSE 连接（需登录）", response_class=EventSourceResponse)
async def sse_connect(
    request: Request,
    auth: Annotated[AuthSchema, Depends(get_current_user)],
    token: Annotated[str, Depends(OAuth2Schema)],
):
    """建立 SSE 连接。

    生成器端点：yield 的 ``ServerSentEvent`` 由路由层编码为 text/event-stream，
    空闲时路由层自动发送 keep-alive 注释。
    """
    user_id = auth.user.id

    async for evt in sse_manager.connect(user_id, token):
        if await request.is_disconnected():
            break
        # 推送的是原始文本字符串，用 raw_data 原样下发，避免被 JSON 引号包裹
        yield ServerSentEvent(raw_data=evt.get("data", ""), event=evt.get("event", "message"))


@ResourceRouter.get("/sse/close", summary="SSE 断开")
async def sse_close(
    request: Request,
    user_id: Annotated[int | None, Query()] = None,
    token: Annotated[str | None, Query()] = None,
) -> SuccessResponse:
    """断开 SSE 连接（无需登录）。

    优先使用查询参数；未传时从 Authorization 请求头提取 token 和 user_id。
    """
    if not token or not user_id:
        auth_header = request.headers.get(settings.TOKEN_NAME, "")
        raw_token = auth_header.split(" ", 1)[1].strip() if auth_header.startswith(settings.TOKEN_PREFIX) else ""
        if raw_token:
            try:
                payload = decode_access_token(raw_token, verify_exp=False)
                token = token or raw_token
                user_id = user_id or payload.user_id
            except Exception:
                pass
    if user_id is not None and token:
        sse_manager.disconnect(user_id, token)
    return SuccessResponse(msg="SSE 连接已断开")


# ==================== WebSocket ====================


@ResourceRouter.websocket("/websocket")
async def websocket_endpoint(websocket: WebSocket) -> None:
    """WebSocket 连接。

    认证：从查询参数或请求头读取 token，解码并校验 clientid，通过后注册会话。
    """
    token = websocket.query_params.get("token") or websocket.headers.get(settings.TOKEN_NAME, "")
    if token.startswith(settings.TOKEN_PREFIX):
        token = token.split(" ", 1)[1].strip()

    # 认证
    try:
        payload = decode_access_token(token, verify_exp=not settings.TOKEN_SLIDING_EXPIRE)
        raw = await RedisUtils(websocket.app.state.redis).get(f"user_session:{payload.sub}")
        if not raw:
            raise ValueError("认证已失效")
        session_info = json.loads(raw)
        # clientid 校验
        if payload.clientid is not None:
            request_client = websocket.query_params.get(settings.CLIENT_ID_HEADER) or websocket.headers.get(settings.CLIENT_ID_HEADER)
            if request_client != payload.clientid:
                raise ValueError("客户端ID与Token不匹配")
        user_id = session_info.get("user_id") or payload.user_id
        if not user_id:
            raise ValueError("认证已失效")
    except Exception as e:
        logger.warning("WebSocket 认证失败'{}'，无法访问系统资源", e)
        await websocket.close(code=4401)
        return

    await websocket.accept()
    WebSocketSessionHolder.add_session(user_id, websocket)
    logger.info("WebSocket 连接建立: userId={}", user_id)
    try:
        while True:
            data = await websocket.receive_text()
            if data == PING:
                await websocket.send_text(PONG)
                continue
            # 入站消息通过 pub/sub 管道回显
            dto = WebSocketMessageDto(session_keys=[user_id], message=data)
            await WebSocketUtils.publish_message(websocket.app.state.redis, dto)
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.warning("WebSocket 异常: {}", e)
    finally:
        WebSocketSessionHolder.remove_session(user_id)
        logger.info("WebSocket 连接关闭: userId={}", user_id)
