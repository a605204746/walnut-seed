"""字典类型与字典数据的数据访问层。"""

from __future__ import annotations

import builtins
from typing import Any

from sqlalchemy import asc, func, select

from app.api.v1.module_system.dict.model import DictDataModel, DictTypeModel
from app.common.request import PageReq
from app.core.base_crud import CRUDBase


class DictTypeCrud(CRUDBase[DictTypeModel]):
    """字典类型数据访问（默认排序 id 升序）。"""

    def _apply_order(self, stmt: Any, page: PageReq | None) -> Any:
        stmt = super()._apply_order(stmt, page)
        return stmt.order_by(asc(DictTypeModel.id))

    async def list(self, *conditions: Any) -> list[DictTypeModel]:
        stmt = select(self.model)
        if conditions:
            stmt = stmt.where(*conditions)
        stmt = self._apply_order(stmt, None)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def exists_by_dict_type(self, dict_type: str, exclude_id: int | None = None) -> bool:
        """判断字典类型是否已存在（exists 查询）。"""
        stmt = select(func.count()).select_from(DictTypeModel).where(DictTypeModel.dict_type == dict_type)
        if exclude_id is not None:
            stmt = stmt.where(DictTypeModel.id != exclude_id)
        result = await self.db.execute(stmt)
        return (result.scalar() or 0) > 0


class DictDataCrud(CRUDBase[DictDataModel]):
    """字典数据数据访问（默认排序 dict_sort、id 升序）。"""

    def _apply_order(self, stmt: Any, page: PageReq | None) -> Any:
        stmt = super()._apply_order(stmt, page)
        return stmt.order_by(asc(DictDataModel.dict_sort), asc(DictDataModel.id))

    async def list(self, *conditions: Any) -> list[DictDataModel]:
        stmt = select(self.model)
        if conditions:
            stmt = stmt.where(*conditions)
        stmt = self._apply_order(stmt, None)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def list_by_type(self, dict_type: str) -> builtins.list[DictDataModel]:
        """根据字典类型查询字典数据列表。"""
        return await self.list_all(DictDataModel.dict_type == dict_type)

    async def exists_by_type(self, dict_type: str) -> bool:
        """判断字典类型下是否存在字典数据（删除字典类型前的占用检查）。"""
        stmt = select(func.count()).select_from(DictDataModel).where(DictDataModel.dict_type == dict_type)
        result = await self.db.execute(stmt)
        return (result.scalar() or 0) > 0

    async def exists_by_type_and_value(self, dict_type: str, dict_value: str, exclude_id: int | None = None) -> bool:
        """判断字典类型+键值是否已存在（exists 查询）。"""
        stmt = select(func.count()).select_from(DictDataModel).where(DictDataModel.dict_type == dict_type, DictDataModel.dict_value == dict_value)
        if exclude_id is not None:
            stmt = stmt.where(DictDataModel.id != exclude_id)
        result = await self.db.execute(stmt)
        return (result.scalar() or 0) > 0
