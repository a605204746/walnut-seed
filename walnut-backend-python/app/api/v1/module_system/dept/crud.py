"""部门域数据访问。

说明：
- sys_dept 带 del_flag，各查询显式追加 ``del_flag == '0'``，删除为逻辑删除（置 '1'）；
- ``find_in_set`` 使用数据库函数实现逗号分隔列的包含判断；
- 数据权限的行级条件由 service 构建后作为条件传入。
"""

from __future__ import annotations

from typing import Any, cast

from sqlalchemy import func, select
from sqlalchemy import update as sa_update
from sqlalchemy.engine import CursorResult
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

from app.api.v1.module_system.dept.model import DeptModel
from app.api.v1.module_system.post.model import PostModel
from app.api.v1.module_system.role.model import RoleDeptModel, RoleModel
from app.api.v1.module_system.user.model import UserModel, UserRoleModel
from app.common.constant import SystemConstants
from app.core.base_crud import CRUDBase
from app.core.base_schema import AuthSchema


class DeptCrud(CRUDBase[DeptModel]):
    """部门数据访问。"""

    def __init__(self, model: type[DeptModel], auth: AuthSchema, db: AsyncSession) -> None:
        super().__init__(model, auth, db)

    # ---------------- FIND_IN_SET ----------------
    def find_in_set(self, value: int | str, column: Any) -> ColumnElement:
        """判断逗号分隔列中是否包含指定值（仅接受整数ID，天然防注入）。"""
        v = str(int(value))
        # MySQL 方言：find_in_set('100', ancestors) <> 0
        return func.find_in_set(v, column) != 0

    # ---------------- 基础查询 ----------------
    async def get_by_id(self, dept_id: int) -> DeptModel | None:
        """按ID查询（含逻辑删除过滤）。"""
        return await self.get_by(id=dept_id, del_flag=SystemConstants.NORMAL)

    async def list_depts(self, *conditions: Any) -> list[DeptModel]:
        """部门列表（del_flag='0' + ancestors/parent/order/id 排序）。"""
        stmt = (
            select(DeptModel)
            .where(DeptModel.del_flag == SystemConstants.NORMAL, *conditions)
            .order_by(DeptModel.ancestors, DeptModel.parent_id, DeptModel.order_num, DeptModel.id)
        )
        return list((await self.db.execute(stmt)).scalars().all())

    async def exists_dept(self, *conditions: Any) -> bool:
        stmt = select(func.count()).select_from(DeptModel).where(DeptModel.del_flag == SystemConstants.NORMAL, *conditions)
        return ((await self.db.execute(stmt)).scalar() or 0) > 0

    async def count_dept(self, *conditions: Any) -> int:
        stmt = select(func.count()).select_from(DeptModel).where(DeptModel.del_flag == SystemConstants.NORMAL, *conditions)
        return (await self.db.execute(stmt)).scalar() or 0

    # ---------------- 树/子孙查询 ----------------
    async def list_descendants(self, dept_id: int) -> list[DeptModel]:
        """所有子孙部门（ancestors 包含 deptId，含逻辑删除过滤）。"""
        stmt = select(DeptModel).where(DeptModel.del_flag == SystemConstants.NORMAL, self.find_in_set(dept_id, DeptModel.ancestors))
        return list((await self.db.execute(stmt)).scalars().all())

    async def list_descendant_ids(self, dept_id: int) -> list[int]:
        """所有子孙部门ID。"""
        stmt = select(DeptModel.id).where(DeptModel.del_flag == SystemConstants.NORMAL, self.find_in_set(dept_id, DeptModel.ancestors))
        return list((await self.db.execute(stmt)).scalars().all())

    async def count_normal_children(self, dept_id: int) -> int:
        """正常状态的子孙部门数。"""
        stmt = (
            select(func.count())
            .select_from(DeptModel)
            .where(
                DeptModel.del_flag == SystemConstants.NORMAL,
                DeptModel.status == SystemConstants.NORMAL,
                self.find_in_set(dept_id, DeptModel.ancestors),
            )
        )
        return (await self.db.execute(stmt)).scalar() or 0

    # ---------------- 关联校验查询 ----------------
    async def count_user_in_dept(self, dept_id: int) -> int:
        """部门下用户数。"""
        stmt = select(func.count()).select_from(UserModel).where(UserModel.del_flag == SystemConstants.NORMAL, UserModel.dept_id == dept_id)
        return (await self.db.execute(stmt)).scalar() or 0

    async def count_post_in_dept(self, dept_id: int) -> int:
        """部门下岗位数。"""
        stmt = select(func.count()).select_from(PostModel).where(PostModel.dept_id == dept_id)
        return (await self.db.execute(stmt)).scalar() or 0

    # ---------------- 翻译回填 ----------------
    async def map_dept_names(self, dept_ids: list[int]) -> dict[int, str]:
        """批量取部门名称（回填 parentName）。"""
        if not dept_ids:
            return {}
        stmt = select(DeptModel.id, DeptModel.dept_name).where(DeptModel.del_flag == SystemConstants.NORMAL, DeptModel.id.in_(dept_ids))
        return {row[0]: row[1] for row in (await self.db.execute(stmt)).all()}

    async def map_leader_names(self, user_ids: list[int]) -> dict[int, str]:
        """批量取负责人账号（回填 leaderName，取用户账号）。"""
        if not user_ids:
            return {}
        stmt = select(UserModel.id, UserModel.user_name).where(UserModel.del_flag == SystemConstants.NORMAL, UserModel.id.in_(user_ids))
        return {row[0]: row[1] for row in (await self.db.execute(stmt)).all()}

    # ---------------- 数据权限辅助 ----------------
    async def list_role_scopes(self, user_id: int) -> list[tuple[int, str | None]]:
        """用户的角色 (id, data_scope) 列表（仅计 del_flag='0' 的角色）。"""
        stmt = (
            select(RoleModel.id, RoleModel.data_scope)
            .join(UserRoleModel, UserRoleModel.role_id == RoleModel.id)
            .where(UserRoleModel.user_id == user_id, RoleModel.del_flag == SystemConstants.NORMAL)
        )
        return [(row[0], row[1]) for row in (await self.db.execute(stmt)).all()]

    def role_custom_dept_subquery(self, role_id: int):
        """角色自定义数据权限授予的部门子查询。"""
        return select(RoleDeptModel.dept_id).where(RoleDeptModel.role_id == role_id)

    # ---------------- 角色授权部门 ----------------
    async def list_dept_ids_by_role_id(self, role_id: int, dept_check_strictly: bool) -> list[int]:
        """角色已授权的部门ID列表（按 parent_id/order_num 排序）。"""
        # 仅统计角色状态正常的授权（left join sys_role + sr.status='0'）
        grant_subq = (
            select(RoleDeptModel.dept_id)
            .select_from(RoleDeptModel)
            .outerjoin(RoleModel, RoleModel.id == RoleDeptModel.role_id)
            .where(RoleDeptModel.role_id == role_id, RoleModel.status == SystemConstants.NORMAL)
            .scalar_subquery()
        )
        stmt = (
            select(DeptModel.id)
            .where(DeptModel.del_flag == SystemConstants.NORMAL, DeptModel.id.in_(grant_subq))
            .order_by(DeptModel.parent_id, DeptModel.order_num)
        )
        if dept_check_strictly:
            # 排除授权部门的父部门（子查询内不加 del_flag 过滤）
            parent_subq = select(DeptModel.parent_id).where(DeptModel.id.in_(grant_subq)).scalar_subquery()
            stmt = stmt.where(DeptModel.id.not_in(parent_subq))
        return list((await self.db.execute(stmt)).scalars().all())

    # ---------------- 写操作 ----------------
    async def update_status_normal(self, dept_ids: list[int]) -> int:
        """批量启用部门（不填充审计字段）。"""
        if not dept_ids:
            return 0
        stmt = sa_update(DeptModel).where(DeptModel.del_flag == SystemConstants.NORMAL, DeptModel.id.in_(dept_ids)).values(status=SystemConstants.NORMAL)
        result = await self.db.execute(stmt)
        await self.db.flush()
        return cast("CursorResult", result).rowcount or 0

    async def logical_delete(self, dept_id: int) -> int:
        """逻辑删除（置 del_flag='1'，不填充审计字段）。"""
        stmt = sa_update(DeptModel).where(DeptModel.id == dept_id, DeptModel.del_flag == SystemConstants.NORMAL).values(del_flag="1")
        result = await self.db.execute(stmt)
        await self.db.flush()
        return cast("CursorResult", result).rowcount or 0
