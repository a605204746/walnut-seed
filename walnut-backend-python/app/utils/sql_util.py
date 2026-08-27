"""SQL 工具：order-by 注入防护。"""

import re

from app.common.enums import HttpStatus
from app.core.exceptions import ServiceException

# 允许排序列的字符集
SQL_ORDER_PATTERN = re.compile(r"^[a-zA-Z0-9_\ ,\.]+$")


def escape_order_by_sql(order_by: str | None) -> str:
    """校验排序列，非法则抛异常。"""
    if not order_by:
        return ""
    if not SQL_ORDER_PATTERN.match(order_by):
        raise ServiceException("参数不符合规范，不能进行查询", code=HttpStatus.BAD_REQUEST)
    return order_by
