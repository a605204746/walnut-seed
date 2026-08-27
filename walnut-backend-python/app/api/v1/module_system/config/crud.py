"""参数设置的数据访问层。"""

from __future__ import annotations

from typing import Any

from sqlalchemy import asc, func, select

from app.api.v1.module_system.config.model import ConfigModel
from app.common.request import PageReq
from app.core.base_crud import CRUDBase


class ConfigCrud(CRUDBase[ConfigModel]):
    """参数配置数据访问（默认排序 id 升序）。"""

    def _apply_order(self, stmt: Any, page: PageReq | None) -> Any:
        stmt = super()._apply_order(stmt, page)
        return stmt.order_by(asc(ConfigModel.id))

    async def list(self, *conditions: Any) -> list[ConfigModel]:
        stmt = select(self.model)
        if conditions:
            stmt = stmt.where(*conditions)
        stmt = self._apply_order(stmt, None)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def exists_by_config_key(self, config_key: str, exclude_id: int | None = None) -> bool:
        """判断参数键名是否已存在（exists 查询）。"""
        stmt = select(func.count()).select_from(ConfigModel).where(ConfigModel.config_key == config_key)
        if exclude_id is not None:
            stmt = stmt.where(ConfigModel.id != exclude_id)
        result = await self.db.execute(stmt)
        return (result.scalar() or 0) > 0
