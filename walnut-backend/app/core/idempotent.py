"""防重提交。

以路由依赖形式使用：
    @router.post("/add", dependencies=[Depends(RepeatSubmit(interval=5000))])

Key 组成：``global:repeat_submit:{请求URI}{md5(token头 + ":" + 参数串)}``，
SETNX 成功放行，窗口内重复请求返回 i18n 提示。
"""

import hashlib
import math

from fastapi import Depends, Request

from app.common.enums import CacheNames
from app.config.setting import settings
from app.core.dependencies import redis_getter
from app.core.exceptions import ServiceException
from app.core.logger import logger
from app.core.redis_crud import RedisUtils
from app.utils.i18n import MessageUtils


class RepeatSubmit:
    """防重提交依赖。

    - ``interval``：防重窗口（毫秒），默认 5000，最小 1000；
    - ``message``：自定义提示，缺省使用 i18n ``repeat.submit.message``。
    """

    def __init__(self, interval: int = 5000, message: str | None = None) -> None:
        self.interval = interval
        self.message = message

    async def __call__(self, request: Request, redis=Depends(redis_getter)) -> None:
        if self.interval < 1000:
            raise ServiceException("重复提交间隔时间不能小于'1'秒")

        token_header = (request.headers.get(settings.TOKEN_NAME) or "").strip()
        try:
            body = (await request.body()).decode("utf-8", "ignore")
        except Exception:
            body = ""
        args_string = body + str(sorted(request.query_params.items()))
        submit_key = hashlib.md5(f"{token_header}:{args_string}".encode()).hexdigest()
        key = f"{CacheNames.REPEAT_SUBMIT_KEY}{request.url.path}{submit_key}"

        expire_seconds = max(1, math.ceil(self.interval / 1000))
        acquired = await RedisUtils(redis).set_if_absent(key, "", expire=expire_seconds)
        if not acquired:
            msg = self.message or MessageUtils.message("repeat.submit.message")
            logger.warning("重复提交拦截: {} {}", request.method, request.url.path)
            raise ServiceException(msg)
