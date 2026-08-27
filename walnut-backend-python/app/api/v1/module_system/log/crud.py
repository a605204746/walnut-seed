"""操作日志与登录日志的数据访问层。

两张日志表无审计字段、无 del_flag，模型直接继承 MappedBase；
未指定排序列时默认按 id 倒序。
"""

from typing import Any

from sqlalchemy import delete as sa_delete
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.module_system.log.model import LogininforModel, OperLogModel
from app.common.request import PageReq
from app.core.base_crud import CRUDBase
from app.core.base_schema import AuthSchema
from app.utils.string_util import is_blank


class OperLogCrud(CRUDBase[OperLogModel]):
    """sys_oper_log 数据访问。"""

    def __init__(self, model: type[OperLogModel], auth: AuthSchema, db: AsyncSession) -> None:
        super().__init__(model, auth, db)

    def _apply_order(self, stmt: Any, page: PageReq | None) -> Any:
        """默认排序：未指定 orderByColumn 时按 id 倒序。"""
        stmt = super()._apply_order(stmt, page)
        if page is None or is_blank(page.order_by_column):
            stmt = stmt.order_by(desc(OperLogModel.id))
        return stmt

    async def list_all(self, *conditions: Any) -> list[OperLogModel]:
        """全量查询（导出用），按 id 倒序。"""
        stmt = select(self.model)
        if conditions:
            stmt = stmt.where(*conditions)
        stmt = stmt.order_by(desc(OperLogModel.id))
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def clean(self) -> None:
        """清空操作日志。"""
        await self.db.execute(sa_delete(self.model))


class LogininforCrud(CRUDBase[LogininforModel]):
    """sys_logininfor 数据访问。"""

    def __init__(self, model: type[LogininforModel], auth: AuthSchema, db: AsyncSession) -> None:
        super().__init__(model, auth, db)

    def _apply_order(self, stmt: Any, page: PageReq | None) -> Any:
        """默认排序：未指定 orderByColumn 时按 id 倒序。"""
        stmt = super()._apply_order(stmt, page)
        if page is None or is_blank(page.order_by_column):
            stmt = stmt.order_by(desc(LogininforModel.id))
        return stmt

    async def list_all(self, *conditions: Any) -> list[LogininforModel]:
        """全量查询（导出用），按 id 倒序。"""
        stmt = select(self.model)
        if conditions:
            stmt = stmt.where(*conditions)
        stmt = stmt.order_by(desc(LogininforModel.id))
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def clean(self) -> None:
        """清空登录日志。"""
        await self.db.execute(sa_delete(self.model))
