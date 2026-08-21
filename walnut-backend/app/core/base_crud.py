"""通用 CRUD 基类。

- 审计字段自动填充：写入时从认证上下文取用户ID/部门ID，未登录取默认值 -1；
- 分页与排序：orderByColumn 转 snake_case 并做 SQL 注入防护；分页结果返回
  ``{rows, total}``。
"""

from collections.abc import Callable
from datetime import datetime
from typing import Any, Protocol, cast

from sqlalchemy import asc, desc, func, select
from sqlalchemy.engine import CursorResult
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.request import PageReq
from app.core.base_schema import AuthSchema
from app.utils.common_util import to_under_score_case
from app.utils.snowflake import IdGeneratorUtil
from app.utils.sql_util import escape_order_by_sql
from app.utils.string_util import is_blank, str2list

# 未登录时的默认填充值
DEFAULT_USER_ID = -1


class _ModelWithId(Protocol):
    """带主键 id 的模型最小协议（日志等部分表不继承 BaseEntity）。"""

    id: Any


class CRUDBase[ModelType: _ModelWithId]:
    """通用异步 CRUD 基类。"""

    def __init__(self, model: type[ModelType], auth: AuthSchema, db: AsyncSession) -> None:
        self.model = model
        self.auth = auth
        self.db = db

    # ---------------- 审计填充 ----------------
    def _current_user_id(self) -> int:
        user = getattr(self.auth, "user", None)
        return getattr(user, "id", None) or DEFAULT_USER_ID

    def _current_dept_id(self) -> int | None:
        user = getattr(self.auth, "user", None)
        return getattr(user, "dept_id", None)

    def _fill_create(self, instance: ModelType) -> None:
        now = datetime.now()
        if getattr(instance, "id", None) in (None, 0):
            instance.id = IdGeneratorUtil.next_long_id()
        if hasattr(instance, "create_by") and getattr(instance, "create_by", None) is None:
            instance.create_by = self._current_user_id()
        if hasattr(instance, "update_by") and getattr(instance, "update_by", None) is None:
            instance.update_by = self._current_user_id()
        if hasattr(instance, "create_dept") and getattr(instance, "create_dept", None) is None:
            instance.create_dept = self._current_dept_id()
        if hasattr(instance, "create_time") and getattr(instance, "create_time", None) is None:
            instance.create_time = now
        if hasattr(instance, "update_time"):
            instance.update_time = now

    def _fill_update(self, instance: ModelType) -> None:
        if hasattr(instance, "update_by"):
            instance.update_by = self._current_user_id()
        if hasattr(instance, "update_time"):
            instance.update_time = datetime.now()

    # ---------------- 排序 ----------------
    def _apply_order(self, stmt: Any, page: PageReq | None) -> Any:
        if page is None or is_blank(page.order_by_column):
            return stmt
        # SQL 注入防护
        escape_order_by_sql(page.order_by_column)
        columns = str2list(page.order_by_column)
        directions = str2list(page.is_asc) if page.is_asc else ["asc"]
        if len(directions) == 1 and len(columns) > 1:
            directions = directions * len(columns)
        if len(columns) != len(directions):
            from app.common.enums import HttpStatus
            from app.core.exceptions import ServiceException

            raise ServiceException("排序参数有误", code=HttpStatus.BAD_REQUEST)
        for col, direction in zip(columns, directions, strict=False):
            attr_name = to_under_score_case(col.strip())
            column = getattr(self.model, attr_name, None)
            if column is None:
                continue
            direction = direction.strip().lower()
            if direction in ("ascending", "asc"):
                stmt = stmt.order_by(asc(column))
            elif direction in ("descending", "desc"):
                stmt = stmt.order_by(desc(column))
        return stmt

    # ---------------- CRUD ----------------
    async def create(self, instance: ModelType) -> ModelType:
        self._fill_create(instance)
        self.db.add(instance)
        await self.db.flush()
        return instance

    async def get(self, instance_id: Any) -> ModelType | None:
        stmt = select(self.model).where(self.model.id == instance_id)
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def get_by(self, **filters: Any) -> ModelType | None:
        stmt = select(self.model).filter_by(**filters)
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def list_all(self, *conditions: Any) -> list[ModelType]:
        stmt = select(self.model)
        if conditions:
            stmt = stmt.where(*conditions)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def page(self, page: PageReq, *conditions: Any) -> dict:
        """分页查询，返回 ``{"rows": [...], "total": N}``。"""
        stmt = select(self.model)
        count_stmt = select(func.count()).select_from(self.model)
        if conditions:
            stmt = stmt.where(*conditions)
            count_stmt = count_stmt.where(*conditions)

        total_result = await self.db.execute(count_stmt)
        total = total_result.scalar() or 0

        stmt = self._apply_order(stmt, page)
        if page.has_limit():
            stmt = stmt.offset(page.offset).limit(page.page_size)
        result = await self.db.execute(stmt)
        rows = list(result.scalars().all())
        return {"rows": rows, "total": total}

    async def update(self, instance: ModelType) -> ModelType:
        self._fill_update(instance)
        merged = await self.db.merge(instance)
        await self.db.flush()
        return merged

    async def delete(self, instance_id: Any) -> bool:
        instance = await self.get(instance_id)
        if instance is None:
            return False
        await self.db.delete(instance)
        await self.db.flush()
        return True

    async def delete_batch(self, ids: "list[Any]") -> Callable[[], int] | int:
        if not ids:
            return 0
        from sqlalchemy import delete as sa_delete

        stmt = sa_delete(self.model).where(self.model.id.in_(ids))
        result = await self.db.execute(stmt)
        return cast("CursorResult", result).rowcount or 0
