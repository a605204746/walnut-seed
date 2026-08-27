"""通知公告的数据访问层。

sys_notice 无 del_flag，删除为物理删除。
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import asc, func, select

from app.api.v1.module_system.notice.model import NoticeModel
from app.common.request import PageReq
from app.core.base_crud import CRUDBase


class NoticeCrud(CRUDBase[NoticeModel]):
    """通知公告 CRUD。"""

    async def page(self, page: PageReq, *conditions: Any) -> dict:
        """分页查询（默认按 id 升序）。"""
        stmt = select(self.model)
        count_stmt = select(func.count()).select_from(self.model)
        if conditions:
            stmt = stmt.where(*conditions)
            count_stmt = count_stmt.where(*conditions)

        total_result = await self.db.execute(count_stmt)
        total = total_result.scalar() or 0

        stmt = stmt.order_by(asc(self.model.id))
        stmt = self._apply_order(stmt, page)
        if page.has_limit():
            stmt = stmt.offset(page.offset).limit(page.page_size)
        result = await self.db.execute(stmt)
        rows = list(result.scalars().all())
        return {"rows": rows, "total": total}

    async def list(self, *conditions: Any) -> list[NoticeModel]:
        """列表查询（默认按 id 升序）。"""
        stmt = select(self.model)
        if conditions:
            stmt = stmt.where(*conditions)
        stmt = stmt.order_by(asc(self.model.id))
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
