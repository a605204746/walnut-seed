"""岗位及关联数据（部门、用户岗位关系）的数据访问层。

sys_post 无 del_flag，删除为物理删除。
"""

from typing import Any

from sqlalchemy import asc, func, select

from app.api.v1.module_system.post.model import PostModel
from app.common.request import PageReq
from app.core.base_crud import CRUDBase


class PostCrud(CRUDBase[PostModel]):
    """岗位 CRUD。"""

    async def page(self, page: PageReq, *conditions: Any) -> dict:
        """分页查询（默认按 post_sort 升序）。"""
        stmt = select(self.model)
        count_stmt = select(func.count()).select_from(self.model)
        if conditions:
            stmt = stmt.where(*conditions)
            count_stmt = count_stmt.where(*conditions)

        total_result = await self.db.execute(count_stmt)
        total = total_result.scalar() or 0

        stmt = stmt.order_by(asc(self.model.post_sort))
        stmt = self._apply_order(stmt, page)
        if page.has_limit():
            stmt = stmt.offset(page.offset).limit(page.page_size)
        result = await self.db.execute(stmt)
        rows = list(result.scalars().all())
        return {"rows": rows, "total": total}

    async def exists_by_name(self, post_name: str, dept_id: int, exclude_id: int | None = None) -> bool:
        """同部门下岗位名称是否已存在（exists 查询）。"""
        stmt = select(func.count()).select_from(self.model).where(self.model.post_name == post_name, self.model.dept_id == dept_id)
        if exclude_id is not None:
            stmt = stmt.where(self.model.id != exclude_id)
        result = await self.db.execute(stmt)
        return (result.scalar() or 0) > 0

    async def exists_by_code(self, post_code: str, exclude_id: int | None = None) -> bool:
        """岗位编码是否已存在（exists 查询）。"""
        stmt = select(func.count()).select_from(self.model).where(self.model.post_code == post_code)
        if exclude_id is not None:
            stmt = stmt.where(self.model.id != exclude_id)
        result = await self.db.execute(stmt)
        return (result.scalar() or 0) > 0

    async def count_user_post(self, post_id: int) -> int:
        """岗位已分配的用户数量。"""
        from app.api.v1.module_system.user.model import UserPostModel

        stmt = select(func.count()).select_from(UserPostModel).where(UserPostModel.post_id == post_id)
        result = await self.db.execute(stmt)
        return result.scalar() or 0

    async def count_by_dept_id(self, dept_id: int) -> int:
        """部门下的岗位数量。"""
        stmt = select(func.count()).select_from(self.model).where(self.model.dept_id == dept_id)
        result = await self.db.execute(stmt)
        return result.scalar() or 0

    async def list_option_by_ids(self, post_ids: list[int]) -> list[PostModel]:
        """按岗位ID串查询正常状态岗位（status=0）。"""
        stmt = select(self.model).where(self.model.status == "0")
        if post_ids:
            stmt = stmt.where(self.model.id.in_(post_ids))
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def list_by_user_id(self, user_id: int) -> list[PostModel]:
        """用户所属岗位（经用户岗位关系表 IN 子查询）。"""
        from app.api.v1.module_system.user.model import UserPostModel

        stmt = select(self.model).where(self.model.id.in_(select(UserPostModel.post_id).where(UserPostModel.user_id == user_id)))
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
