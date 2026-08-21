import re
from datetime import date, datetime, time
from typing import Annotated

from pydantic import AfterValidator, PlainSerializer, WithJsonSchema

from app.common.constant import DATE_DISPLAY_FMT, DATETIME_DISPLAY_FMT, TIME_DISPLAY_FMT, RegexConstants
from app.common.enums import HttpStatus
from app.core.exceptions import ServiceException

# 自定义日期时间字符串类型（yyyy-MM-dd HH:mm:ss）
DateTimeStr = Annotated[
    datetime,
    AfterValidator(lambda x: datetime_validator(x)),
    PlainSerializer(
        lambda x: x.strftime(DATETIME_DISPLAY_FMT) if isinstance(x, datetime) else str(x),
        return_type=str,
        when_used="json",
    ),
    WithJsonSchema({"type": "string"}, mode="serialization"),
]

DateStr = Annotated[
    date,
    AfterValidator(lambda x: date_validator(x)),
    PlainSerializer(
        lambda x: x.strftime(DATE_DISPLAY_FMT) if isinstance(x, date) else str(x),
        return_type=str,
        when_used="json",
    ),
    WithJsonSchema({"type": "string"}, mode="serialization"),
]

TimeStr = Annotated[
    time,
    AfterValidator(lambda x: time_validator(x)),
    PlainSerializer(
        lambda x: x.strftime(TIME_DISPLAY_FMT) if isinstance(x, time) else str(x),
        return_type=str,
        when_used="json",
    ),
    WithJsonSchema({"type": "string"}, mode="serialization"),
]

Telephone = Annotated[
    str,
    AfterValidator(lambda x: mobile_validator(x)),
    PlainSerializer(lambda x: x, return_type=str),
    WithJsonSchema({"type": "string"}, mode="serialization"),
]

Email = Annotated[
    str,
    AfterValidator(lambda x: email_validator(x)),
    PlainSerializer(lambda x: x, return_type=str),
    WithJsonSchema({"type": "string"}, mode="serialization"),
]


def datetime_validator(value: str | datetime) -> datetime:
    try:
        if isinstance(value, str):
            return datetime.strptime(value, DATETIME_DISPLAY_FMT)
        if isinstance(value, datetime):
            return value
    except Exception:
        raise ServiceException("无效的日期格式", code=HttpStatus.BAD_REQUEST)
    raise ServiceException("无效的日期格式", code=HttpStatus.BAD_REQUEST)


def date_validator(value: str | date) -> date:
    try:
        if isinstance(value, str):
            return datetime.strptime(value, DATE_DISPLAY_FMT).date()
        if isinstance(value, date):
            return value
    except Exception:
        raise ServiceException("无效的日期格式", code=HttpStatus.BAD_REQUEST)
    raise ServiceException("无效的日期格式", code=HttpStatus.BAD_REQUEST)


def time_validator(value: str | time) -> time:
    try:
        if isinstance(value, str):
            return datetime.strptime(value, TIME_DISPLAY_FMT).time()
        if isinstance(value, time):
            return value
    except Exception:
        raise ServiceException("无效的时间格式", code=HttpStatus.BAD_REQUEST)
    raise ServiceException("无效的时间格式", code=HttpStatus.BAD_REQUEST)


def email_validator(value: str) -> str:
    if not value:
        raise ServiceException("邮箱地址不能为空", code=HttpStatus.BAD_REQUEST)
    if not re.match(RegexConstants.EMAIL, value):
        raise ServiceException("邮箱地址格式不正确", code=HttpStatus.BAD_REQUEST)
    return value


def mobile_validator(value: str | None) -> str | None:
    if not value:
        return value
    if not re.match(RegexConstants.MOBILE, value):
        raise ServiceException("手机号格式不正确", code=HttpStatus.BAD_REQUEST)
    return value
