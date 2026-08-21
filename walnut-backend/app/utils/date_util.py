"""日期时间工具。"""

from datetime import datetime

from app.common.constant import DATE_DISPLAY_FMT, DATETIME_DISPLAY_FMT

PARSE_PATTERNS = [
    "%Y-%m-%d",
    "%Y-%m-%d %H:%M",
    "%Y-%m-%d %H:%M:%S",
    "%Y/%m/%d",
    "%Y/%m/%d %H:%M",
    "%Y/%m/%d %H:%M:%S",
    "%Y.%m.%d",
    "%Y.%m.%d %H:%M",
    "%Y.%m.%d %H:%M:%S",
    "%Y%m%d",
    "%Y%m%d%H%M%S",
]


def get_now_date() -> datetime:
    return datetime.now()


def get_date() -> str:
    return datetime.now().strftime(DATE_DISPLAY_FMT)


def date_time_now(fmt: str = DATETIME_DISPLAY_FMT) -> str:
    return datetime.now().strftime(fmt)


def format_date(value: datetime) -> str:
    return value.strftime(DATE_DISPLAY_FMT)


def format_date_time(value: datetime) -> str:
    return value.strftime(DATETIME_DISPLAY_FMT)


def parse_date(value: str) -> datetime | None:
    """宽松解析多种日期格式。"""
    if not value:
        return None
    for pattern in PARSE_PATTERNS:
        try:
            return datetime.strptime(value.strip(), pattern)
        except ValueError:
            continue
    return None


def difference_seconds(start: datetime, end: datetime) -> int:
    return abs(int((end - start).total_seconds()))


def get_date_poor(start: datetime, end: datetime) -> str:
    """时间差友好展示（格式：%d天 %d小时 %d分钟）。"""
    delta = abs((end - start).total_seconds())
    days = int(delta // 86400)
    hours = int((delta % 86400) // 3600)
    minutes = int((delta % 3600) // 60)
    return f"{days}天 {hours}小时 {minutes}分钟"
