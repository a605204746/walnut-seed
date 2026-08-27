"""order-by 注入防护 escape_order_by_sql 回归测试。

锁定的整改行为：
- 白名单字符集（字母/数字/下划线/空格/逗号/点）内的排序串原样放行；
- 注入尝试（分号、注释符、引号、括号、等号、换行等）一律拒绝并返回 400 业务码；
- 空/None 输入返回空串（不抛错）。
"""

import pytest

from app.common.enums import HttpStatus
from app.core.exceptions import ServiceException
from app.utils.sql_util import escape_order_by_sql


@pytest.mark.parametrize(
    "legal_order_by",
    [
        "create_time",
        "create_time DESC",
        "user_id, create_time DESC",
        "sys_user.create_time",
        "col_1 ASC, col_2 DESC",
    ],
)
def test_legal_order_by_passes_through(legal_order_by):
    assert escape_order_by_sql(legal_order_by) == legal_order_by


@pytest.mark.parametrize(
    "injection",
    [
        "id; DROP TABLE sys_user",
        "id--",
        "id /* comment */",
        "name'",
        'name"',
        "1 OR 1=1",
        "col)",
        "id\nDELETE FROM sys_user",
        "if(1=1,id,sleep(1))",
    ],
)
def test_injection_attempts_rejected(injection):
    with pytest.raises(ServiceException) as exc_info:
        escape_order_by_sql(injection)
    assert exc_info.value.code == HttpStatus.BAD_REQUEST


@pytest.mark.parametrize("empty_input", [None, ""])
def test_empty_input_returns_empty_string(empty_input):
    assert escape_order_by_sql(empty_input) == ""
