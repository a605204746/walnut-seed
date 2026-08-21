"""客户端的数据访问层。

sys_client 含 del_flag：所有查询显式过滤 del_flag='0'，删除为逻辑删除。
"""

from __future__ import annotations

import builtins
from datetime import datetime
from typing import Any, cast

from sqlalchemy import asc, func, select
from sqlalchemy import update as sa_update
from sqlalchemy.engine import CursorResult

from app.api.v1.module_system.client.model import ClientModel
from app.common.constant import SystemConstants
from app.common.request import PageReq
from app.core.base_crud import CRUDBase


class ClientCrud(CRUDBase[ClientModel]):
    """客户端 CRUD（逻辑删除）。"""

    async def get(self, instance_id: Any) -> ClientModel | None:
        stmt = select(self.model).where(self.model.id == instance_id, self.model.del_flag == SystemConstants.NORMAL)
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def list(self, *conditions: Any) -> list[ClientModel]:
        """列表查询（默认按 id 升序，自动追加 del_flag 过滤）。"""
        stmt = select(self.model).where(self.model.del_flag == SystemConstants.NORMAL)
        if conditions:
            stmt = stmt.where(*conditions)
        stmt = stmt.order_by(asc(self.model.id))
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def page(self, page: PageReq, *conditions: Any) -> dict:
        """分页查询（默认按 id 升序，自动追加 del_flag 过滤）。"""
        all_conditions = [self.model.del_flag == SystemConstants.NORMAL, *conditions]
        stmt = select(self.model).where(*all_conditions)
        count_stmt = select(func.count()).select_from(self.model).where(*all_conditions)

        total_result = await self.db.execute(count_stmt)
        total = total_result.scalar() or 0

        stmt = stmt.order_by(asc(self.model.id))
        stmt = self._apply_order(stmt, page)
        if page.has_limit():
            stmt = stmt.offset(page.offset).limit(page.page_size)
        result = await self.db.execute(stmt)
        rows = list(result.scalars().all())
        return {"rows": rows, "total": total}

    async def get_by_client_key(self, client_key: str) -> ClientModel | None:
        """按客户端key查询（供认证使用）。"""
        stmt = select(self.model).where(self.model.client_key == client_key, self.model.del_flag == SystemConstants.NORMAL)
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def get_by_client_id(self, client_id: str) -> ClientModel | None:
        """按客户端id查询。"""
        stmt = select(self.model).where(self.model.client_id == client_id, self.model.del_flag == SystemConstants.NORMAL)
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def exists_by_key(self, client_key: str, exclude_id: int | None = None) -> bool:
        """客户端key是否已存在（exists 查询）。"""
        stmt = (
            select(func.count())
            .select_from(self.model)
            .where(
                self.model.client_key == client_key,
                self.model.del_flag == SystemConstants.NORMAL,
            )
        )
        if exclude_id is not None:
            stmt = stmt.where(self.model.id != exclude_id)
        result = await self.db.execute(stmt)
        return (result.scalar() or 0) > 0

    async def update_status_by_client_id(self, client_id: str, status: str) -> int:
        """按客户端id修改状态。"""
        stmt = (
            sa_update(self.model)
            .where(self.model.client_id == client_id, self.model.del_flag == SystemConstants.NORMAL)
            .values(status=status, update_by=self._current_user_id(), update_time=datetime.now())
        )
        result = await self.db.execute(stmt)
        return cast("CursorResult", result).rowcount or 0

    async def delete_batch(self, ids: builtins.list[Any]) -> int:
        """批量逻辑删除（update del_flag='1'）。"""
        if not ids:
            return 0
        stmt = sa_update(self.model).where(self.model.id.in_(ids), self.model.del_flag == SystemConstants.NORMAL).values(del_flag="1", update_by=self._current_user_id(), update_time=datetime.now())
        result = await self.db.execute(stmt)
        return cast("CursorResult", result).rowcount or 0
