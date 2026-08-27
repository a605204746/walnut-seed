"""角色数据访问。

- sys_role 带 del_flag，查询统一追加 ``del_flag == '0'``，删除为逻辑删除（置 '1'）；
- 列表/详情/计数带数据权限（按 create_dept/create_by 列行级过滤），
  通过 ``app.core.permission.Permission`` 追加过滤条件；
- sys_role_menu / sys_role_dept / sys_user_role 为复合主键关联表，无 del_flag，物理删改。
"""

from __future__ import annotations

from typing import Any, cast

from sqlalchemy import asc, func, select
from sqlalchemy import delete as sa_delete
from sqlalchemy import update as sa_update
from sqlalchemy.engine import CursorResult
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.module_system.role.model import RoleDeptModel, RoleMenuModel, RoleModel
from app.common.constant import SystemConstants
from app.common.request import PageReq
from app.core.base_crud import CRUDBase
from app.core.base_schema import AuthSchema
from app.core.permission import Permission


class RoleCrud(CRUDBase[RoleModel]):
    """角色 CRUD。"""

    def __init__(self, model: type[RoleModel], auth: AuthSchema, db: AsyncSession) -> None:
        super().__init__(model, auth, db)
        self.permission = Permission(model, auth, db)

    # ==================== 角色查询（带 del_flag + 数据权限） ====================
    async def page_role_list(self, page: PageReq, *conditions: Any) -> dict:
        """分页查询角色列表（固定 role_sort、create_time 升序）。"""
        stmt = select(self.model).where(self.model.del_flag == SystemConstants.NORMAL)
        count_stmt = select(func.count()).select_from(self.model).where(self.model.del_flag == SystemConstants.NORMAL)
        if conditions:
            stmt = stmt.where(*conditions)
            count_stmt = count_stmt.where(*conditions)
        stmt = await self.permission.filter_query(stmt)
        count_stmt = await self.permission.filter_query(count_stmt)

        total = (await self.db.execute(count_stmt)).scalar() or 0
        stmt = stmt.order_by(asc(self.model.role_sort), asc(self.model.create_time))
        if page.has_limit():
            stmt = stmt.offset(page.offset).limit(page.page_size)
        rows = list((await self.db.execute(stmt)).scalars().all())
        return {"rows": rows, "total": total}

    async def list_role(self, *conditions: Any) -> list[RoleModel]:
        """查询角色列表（导出使用，不分页，固定排序）。"""
        stmt = select(self.model).where(self.model.del_flag == SystemConstants.NORMAL)
        if conditions:
            stmt = stmt.where(*conditions)
        stmt = await self.permission.filter_query(stmt)
        stmt = stmt.order_by(asc(self.model.role_sort), asc(self.model.create_time))
        return list((await self.db.execute(stmt)).scalars().all())

    async def get_role_by_id(self, role_id: int) -> RoleModel | None:
        """按角色ID查询（del_flag + 数据权限）。"""
        stmt = select(self.model).where(self.model.id == role_id, self.model.del_flag == SystemConstants.NORMAL)
        stmt = await self.permission.filter_query(stmt)
        return (await self.db.execute(stmt)).scalars().first()

    async def list_option_by_ids(self, role_ids: list[int] | None) -> list[RoleModel]:
        """角色选择框列表（status=0 + del_flag + 数据权限）。"""
        stmt = select(self.model).where(self.model.status == SystemConstants.NORMAL, self.model.del_flag == SystemConstants.NORMAL)
        if role_ids:
            stmt = stmt.where(self.model.id.in_(role_ids))
        stmt = await self.permission.filter_query(stmt)
        stmt = stmt.order_by(asc(self.model.role_sort), asc(self.model.create_time))
        return list((await self.db.execute(stmt)).scalars().all())

    async def list_by_ids(self, role_ids: list[int]) -> list[RoleModel]:
        """按ID串查询未删除角色（删除前校验使用，不做数据权限过滤）。"""
        stmt = select(self.model).where(self.model.id.in_(role_ids), self.model.del_flag == SystemConstants.NORMAL)
        return list((await self.db.execute(stmt)).scalars().all())

    async def count_visible_roles(self, role_ids: list[int]) -> int:
        """统计数据权限可见的角色数量（数据权限校验使用）。"""
        stmt = select(func.count()).select_from(self.model).where(self.model.id.in_(role_ids), self.model.del_flag == SystemConstants.NORMAL)
        stmt = await self.permission.filter_query(stmt)
        return (await self.db.execute(stmt)).scalar() or 0

    # ==================== 唯一性 / 使用数量 ====================
    async def exists_by_name(self, role_name: str, exclude_id: int | None = None) -> bool:
        """角色名称是否已存在。"""
        stmt = select(func.count()).select_from(self.model).where(
            self.model.role_name == role_name, self.model.del_flag == SystemConstants.NORMAL
        )
        if exclude_id is not None:
            stmt = stmt.where(self.model.id != exclude_id)
        return ((await self.db.execute(stmt)).scalar() or 0) > 0

    async def exists_by_key(self, role_key: str, exclude_id: int | None = None) -> bool:
        """角色权限字符是否已存在。"""
        stmt = select(func.count()).select_from(self.model).where(
            self.model.role_key == role_key, self.model.del_flag == SystemConstants.NORMAL
        )
        if exclude_id is not None:
            stmt = stmt.where(self.model.id != exclude_id)
        return ((await self.db.execute(stmt)).scalar() or 0) > 0

    async def count_user_role_by_role_id(self, role_id: int) -> int:
        """角色已分配的用户数量。"""
        from app.api.v1.module_system.user.model import UserRoleModel

        stmt = select(func.count()).select_from(UserRoleModel).where(UserRoleModel.role_id == role_id)
        return (await self.db.execute(stmt)).scalar() or 0

    # ==================== 逻辑删除 ====================
    async def soft_delete_by_ids(self, role_ids: list[int]) -> int:
        """逻辑删除角色（置 del_flag='1'）。"""
        stmt = sa_update(self.model).where(self.model.id.in_(role_ids)).values(del_flag=SystemConstants.DISABLE)
        result = await self.db.execute(stmt)
        await self.db.flush()
        return cast("CursorResult", result).rowcount or 0

    # ==================== 角色-菜单关联（sys_role_menu） ====================
    async def delete_role_menu(self, role_id: int) -> None:
        await self.db.execute(sa_delete(RoleMenuModel).where(RoleMenuModel.role_id == role_id))

    async def delete_role_menu_batch(self, role_ids: list[int]) -> None:
        await self.db.execute(sa_delete(RoleMenuModel).where(RoleMenuModel.role_id.in_(role_ids)))

    async def insert_role_menu(self, role_id: int, menu_ids: list[int]) -> int:
        """批量写入角色-菜单关联。"""
        if not menu_ids:
            return 0
        self.db.add_all([RoleMenuModel(role_id=role_id, menu_id=menu_id) for menu_id in menu_ids])
        await self.db.flush()
        return len(menu_ids)

    # ==================== 角色-部门关联（sys_role_dept） ====================
    async def delete_role_dept(self, role_id: int) -> None:
        await self.db.execute(sa_delete(RoleDeptModel).where(RoleDeptModel.role_id == role_id))

    async def delete_role_dept_batch(self, role_ids: list[int]) -> None:
        await self.db.execute(sa_delete(RoleDeptModel).where(RoleDeptModel.role_id.in_(role_ids)))

    async def insert_role_dept(self, role_id: int, dept_ids: list[int]) -> int:
        """批量写入角色-部门关联。"""
        if not dept_ids:
            return 0
        self.db.add_all([RoleDeptModel(role_id=role_id, dept_id=dept_id) for dept_id in dept_ids])
        await self.db.flush()
        return len(dept_ids)

    async def list_dept_ids_by_role_id(self, role_id: int) -> list[int]:
        """角色已授权的部门ID列表（deptTree checkedKeys 使用）。"""
        stmt = select(RoleDeptModel.dept_id).where(RoleDeptModel.role_id == role_id)
        return list((await self.db.execute(stmt)).scalars().all())

    # ==================== 用户-角色关联（sys_user_role，authUser） ====================
    async def delete_auth_user(self, role_id: int, user_id: int) -> int:
        """取消单个用户的角色授权。"""
        from app.api.v1.module_system.user.model import UserRoleModel

        result = await self.db.execute(
            sa_delete(UserRoleModel).where(UserRoleModel.role_id == role_id, UserRoleModel.user_id == user_id)
        )
        await self.db.flush()
        return cast("CursorResult", result).rowcount or 0

    async def delete_auth_users(self, role_id: int, user_ids: list[int]) -> int:
        """批量取消用户的角色授权。"""
        from app.api.v1.module_system.user.model import UserRoleModel

        result = await self.db.execute(
            sa_delete(UserRoleModel).where(UserRoleModel.role_id == role_id, UserRoleModel.user_id.in_(user_ids))
        )
        await self.db.flush()
        return cast("CursorResult", result).rowcount or 0

    async def insert_auth_users(self, role_id: int, user_ids: list[int]) -> int:
        """批量为用户授权角色。"""
        from app.api.v1.module_system.user.model import UserRoleModel

        if not user_ids:
            return 0
        self.db.add_all([UserRoleModel(role_id=role_id, user_id=user_id) for user_id in user_ids])
        await self.db.flush()
        return len(user_ids)

    async def user_ids_by_role_id(self, role_id: int) -> list[int]:
        """角色已分配的用户ID列表。"""
        from app.api.v1.module_system.user.model import UserRoleModel

        stmt = select(UserRoleModel.user_id).where(UserRoleModel.role_id == role_id)
        return list((await self.db.execute(stmt)).scalars().all())

    # ==================== authUser 用户分页查询 ====================
    async def page_allocated_users(self, page: PageReq, role_id: int | None, *conditions: Any) -> dict:
        """已分配该角色的用户分页（del_flag + 数据权限 + u.id 升序）。"""
        from app.api.v1.module_system.user.model import UserModel, UserRoleModel

        # sys_user 数据权限按 RuoYi 契约使用 dept_id 列过滤（与用户列表一致）
        user_perm = Permission(UserModel, self.auth, self.db, dept_column=UserModel.dept_id)
        stmt = (
            select(UserModel)
            .join(UserRoleModel, UserRoleModel.user_id == UserModel.id)
            .where(UserModel.del_flag == SystemConstants.NORMAL)
        )
        count_stmt = (
            select(func.count())
            .select_from(UserModel)
            .join(UserRoleModel, UserRoleModel.user_id == UserModel.id)
            .where(UserModel.del_flag == SystemConstants.NORMAL)
        )
        if role_id is not None:
            stmt = stmt.where(UserRoleModel.role_id == role_id)
            count_stmt = count_stmt.where(UserRoleModel.role_id == role_id)
        if conditions:
            stmt = stmt.where(*conditions)
            count_stmt = count_stmt.where(*conditions)
        stmt = await user_perm.filter_query(stmt)
        count_stmt = await user_perm.filter_query(count_stmt)

        total = (await self.db.execute(count_stmt)).scalar() or 0
        stmt = stmt.order_by(asc(UserModel.id))
        if page.has_limit():
            stmt = stmt.offset(page.offset).limit(page.page_size)
        rows = list((await self.db.execute(stmt)).scalars().all())
        return {"rows": rows, "total": total}

    async def page_unallocated_users(self, page: PageReq, role_id: int | None, *conditions: Any) -> dict:
        """未分配该角色的用户分页（排除已分配用户）。"""
        from app.api.v1.module_system.user.model import UserModel, UserRoleModel

        # sys_user 数据权限按 RuoYi 契约使用 dept_id 列过滤（与用户列表一致）
        user_perm = Permission(UserModel, self.auth, self.db, dept_column=UserModel.dept_id)
        stmt = select(UserModel).where(UserModel.del_flag == SystemConstants.NORMAL)
        count_stmt = select(func.count()).select_from(UserModel).where(UserModel.del_flag == SystemConstants.NORMAL)
        if role_id is not None:
            allocated_sub = select(UserRoleModel.user_id).where(UserRoleModel.role_id == role_id)
            stmt = stmt.where(UserModel.id.not_in(allocated_sub))
            count_stmt = count_stmt.where(UserModel.id.not_in(allocated_sub))
        if conditions:
            stmt = stmt.where(*conditions)
            count_stmt = count_stmt.where(*conditions)
        stmt = await user_perm.filter_query(stmt)
        count_stmt = await user_perm.filter_query(count_stmt)

        total = (await self.db.execute(count_stmt)).scalar() or 0
        stmt = stmt.order_by(asc(UserModel.id))
        if page.has_limit():
            stmt = stmt.offset(page.offset).limit(page.page_size)
        rows = list((await self.db.execute(stmt)).scalars().all())
        return {"rows": rows, "total": total}
