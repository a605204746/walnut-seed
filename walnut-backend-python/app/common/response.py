"""统一响应封装。

响应契约：
- 响应体固定为 ``{"code": int, "msg": str, "data": T | None}``；
- 业务成功 code=200、失败 code=500、警告 code=601；
- 业务异常几乎都返回 HTTP 200（真实结果在 body.code 中），前端据此判断；
- 分页载荷为 ``{"rows": [...], "total": N}``；
- JSON 序列化规则：日期时间 ``yyyy-MM-dd HH:mm:ss``、
  超出 JS 安全整数范围的大整数转为字符串、Decimal 转字符串。
"""

from collections.abc import Mapping
from datetime import date, datetime, time
from decimal import Decimal
from typing import Any, ClassVar

from fastapi import status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse, RedirectResponse, StreamingResponse
from pydantic import BaseModel, Field
from starlette.background import BackgroundTask

from app.common.constant import DATE_DISPLAY_FMT, DATETIME_DISPLAY_FMT, TIME_DISPLAY_FMT

# JS 安全整数范围（超出则序列化为字符串）
_JS_SAFE_MAX = 9007199254740991
_JS_SAFE_MIN = -9007199254740991


def _encode_int(value: int) -> int | str:
    return value if _JS_SAFE_MIN < value < _JS_SAFE_MAX else str(value)


# 裸 datetime/date/time/Decimal/大整数（未走 Pydantic 的 dict 等）的 JSON 输出规则
_JSON_CUSTOM_ENCODER: dict[type[Any], Any] = {
    bool: lambda v: v,  # bool 是 int 子类，需优先匹配，避免被 int 规则转字符串
    int: _encode_int,
    Decimal: str,
    datetime: lambda d: d.strftime(DATETIME_DISPLAY_FMT),
    date: lambda d: d.strftime(DATE_DISPLAY_FMT),
    time: lambda t: t.strftime(TIME_DISPLAY_FMT),
}


def jsonable_response_content(content: Any) -> Any:
    return jsonable_encoder(content, custom_encoder=_JSON_CUSTOM_ENCODER)


class ApiResponse[T](BaseModel):
    """统一响应模型。"""

    code: int = Field(default=200, description="业务状态码")
    msg: str = Field(default="操作成功", description="响应消息")
    data: T | None = Field(default=None, description="响应数据")

    SUCCESS: ClassVar[int] = 200
    FAIL: ClassVar[int] = 500
    WARN: ClassVar[int] = 601


class PageResult[T](BaseModel):
    """分页结果模型（序列化为 {rows, total}）。"""

    rows: list[T] = Field(default_factory=list, description="数据列表")
    total: int = Field(default=0, ge=0, description="总记录数")

    @classmethod
    def of(cls, rows: list[T], total: int) -> "PageResult[T]":
        return cls(rows=rows, total=total)


class EnvelopeResponse(JSONResponse):
    """业务信封响应基类（body 统一为 ``{"code", "msg", "data"}``）。

    handler 返回注解可使用本基类，涵盖成功/警告/失败三类信封响应。
    """


class SuccessResponse(EnvelopeResponse):
    """成功响应（HTTP 200，body code=200）。"""

    def __init__(
        self,
        data: Any | None = None,
        msg: str = "操作成功",
        code: int = ApiResponse.SUCCESS,
        status_code: int = status.HTTP_200_OK,
    ) -> None:
        content = ApiResponse(code=code, msg=msg, data=data).model_dump()
        super().__init__(content=jsonable_response_content(content), status_code=status_code)
        self.headers["Content-Type"] = "application/json; charset=utf-8"


class ErrorResponse(EnvelopeResponse):
    """业务错误响应。

    默认 HTTP 传输状态码为 200，真实错误码写入 body.code。
    特殊场景（如健康探针 503）可通过 ``status_code`` 覆盖。
    """

    def __init__(
        self,
        msg: str = "操作失败",
        code: int = ApiResponse.FAIL,
        data: Any | None = None,
        status_code: int = status.HTTP_200_OK,
    ) -> None:
        content = ApiResponse(code=code, msg=msg, data=data).model_dump()
        super().__init__(content=jsonable_response_content(content), status_code=status_code)
        self.headers["Content-Type"] = "application/json; charset=utf-8"


class WarnResponse(ErrorResponse):
    """警告响应（code=601）。"""

    def __init__(self, msg: str = "操作警告", data: Any | None = None, status_code: int = status.HTTP_200_OK) -> None:
        super().__init__(msg=msg, code=ApiResponse.WARN, data=data, status_code=status_code)


class StreamResponse(StreamingResponse):
    """流式响应。"""

    def __init__(
        self,
        data: Any = None,
        status_code: int = status.HTTP_200_OK,
        headers: Mapping[str, str] | None = None,
        media_type: str | None = None,
        background: BackgroundTask | None = None,
    ) -> None:
        super().__init__(content=data, status_code=status_code, media_type=media_type, headers=headers, background=background)


class PlainTextContentResponse(PlainTextResponse):
    """纯文本响应。"""

    def __init__(self, content: str, status_code: int = status.HTTP_200_OK, headers: Mapping[str, str] | None = None) -> None:
        super().__init__(content=content, status_code=status_code, headers=headers)


class RedirectContentResponse(RedirectResponse):
    """重定向响应。"""

    def __init__(self, url: str, status_code: int = status.HTTP_302_FOUND, headers: Mapping[str, str] | None = None) -> None:
        super().__init__(url=url, status_code=status_code, headers=headers)


class UploadFileResponse(FileResponse):
    """文件下载响应。"""

    def __init__(
        self,
        file_path: str,
        filename: str,
        media_type: str = "application/octet-stream",
        headers: Mapping[str, str] | None = None,
        background: BackgroundTask | None = None,
        status_code: int = 200,
    ) -> None:
        super().__init__(
            path=file_path,
            status_code=status_code,
            headers=headers,
            media_type=media_type,
            background=background,
            filename=filename,
            stat_result=None,
            content_disposition_type="attachment",
        )
