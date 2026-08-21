"""用户域数据访问。

说明：
- sys_user 带 del_flag，查询统一追加 ``del_flag == '0'``，删除为逻辑删除（置 '1'）；
- 列表/导出/计数/更新的行级数据权限条件由 service 构建
  ``_user_data_scope_condition`` 后作为条件传入；
- 按ID / 按用户账号 / 按部门列表查询不做数据权限过滤；
- sys_user_role / sys_user_post 为复合主键关联表，无 del_flag，物理删改。
"""

from __future__ import annotations

from typing import Any, cast

from sqlalchemy import asc, func, select
from sqlalchemy import delete as sa_delete
from sqlalchemy import update as sa_update
from sqlalchemy.engine import CursorResult
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased
from sqlalchemy.sql.elements import ColumnElement

from app.api.v1.module_system.dept.crud import DeptCrud
from app.api.v1.module_system.dept.model import DeptModel
from app.api.v1.module_system.user.model import UserModel, UserPostModel, UserRoleModel
from app.common.constant import SystemConstants
from app.common.request import PageReq
from app.core.base_crud import CRUDBase
from app.core.base_schema import AuthSchema


class UserCrud(CRUDBase[UserModel]):
    """用户 CRUD。"""

    def __init__(self, model: type[UserModel], auth: AuthSchema, db: AsyncSession) -> None:
        super().__init__(model, auth, db)
        # 复用部门数据访问：角色数据范围、自定义授权部门子查询、部门及以下ID
        self.dept_crud = DeptCrud(DeptModel, auth, db)

    # ==================== 数据权限辅助 ====================
    async def list_role_scopes(self, user_id: int) -> list[tuple[int, str | None]]:
        """用户角色的 (role_id, data_scope) 列表（复用 DeptCrud.list_role_scopes）。"""
        return await self.dept_crud.list_role_scopes(user_id)

    def role_custom_dept_subquery(self, role_id: int):
        """角色自定义数据权限授予的部门子查询。"""
        return self.dept_crud.role_custom_dept_subquery(role_id)

    async def dept_and_child_ids(self, dept_id: int | None) -> list[int]:
        """部门及其全部子孙部门ID（含自身；dept_id 为 None 时返回 [-1]）。"""
        if dept_id is None:
            return [-1]
        ids = await self.dept_crud.list_descendant_ids(dept_id)
        ids.append(dept_id)
        return ids

    # ==================== 查询（无数据权限） ====================
    async def get_user_by_id(self, user_id: int) -> UserModel | None:
        """按ID查询未删除用户（不带数据权限）。"""
        return await self.get_by(id=user_id, del_flag=SystemConstants.NORMAL)

    async def get_user_by_user_name(self, user_name: str) -> UserModel | None:
        """按用户账号查询未删除用户。"""
        return await self.get_by(user_name=user_name, del_flag=SystemConstants.NORMAL)

    async def list_users(self, *conditions: Any) -> list[UserModel]:
        """用户列表（del_flag + 传入条件，id 升序，不做数据权限，供部门下用户等查询使用）。"""
        stmt = select(UserModel).where(UserModel.del_flag == SystemConstants.NORMAL, *conditions).order_by(asc(UserModel.id))
        return list((await self.db.execute(stmt)).scalars().all())

    async def list_option(self, user_ids: list[int] | None, dept_id: int | None) -> list[UserModel]:
        """用户选择框列表（status=0 + 可选 deptId/userIds）。"""
        conditions: list[ColumnElement] = [UserModel.status == SystemConstants.NORMAL]
        if dept_id is not None:
            conditions.append(UserModel.dept_id == dept_id)
        if user_ids:
            conditions.append(UserModel.id.in_(user_ids))
        return await self.list_users(*conditions)

    # ==================== 查询（带数据权限：list / export / count） ====================
    async def page_user_list(self, page: PageReq, conditions: list[ColumnElement]) -> dict:
        """分页查询用户列表（del_flag + 数据权限 + id 升序）。

        ``conditions`` 已含数据权限条件（由 service 追加）。
        """
        stmt = select(UserModel).where(UserModel.del_flag == SystemConstants.NORMAL)
        count_stmt = select(func.count()).select_from(UserModel).where(UserModel.del_flag == SystemConstants.NORMAL)
        if conditions:
            stmt = stmt.where(*conditions)
            count_stmt = count_stmt.where(*conditions)
        total = (await self.db.execute(count_stmt)).scalar() or 0
        stmt = stmt.order_by(asc(UserModel.id))
        if page.has_limit():
            stmt = stmt.offset(page.offset).limit(page.page_size)
        rows = list((await self.db.execute(stmt)).scalars().all())
        return {"rows": rows, "total": total}

    async def count_user_by_id(self, user_id: int, scope: ColumnElement | None) -> int:
        """统计指定用户（带数据权限，数据权限校验使用）。"""
        conditions: list[ColumnElement] = [UserModel.del_flag == SystemConstants.NORMAL, UserModel.id == user_id]
        if scope is not None:
            conditions.append(scope)
        stmt = select(func.count()).select_from(UserModel).where(*conditions)
        return (await self.db.execute(stmt)).scalar() or 0

    async def list_export_rows(self, conditions: list[ColumnElement]) -> list[tuple[UserModel, str | None, str | None]]:
        """导出查询（left join sys_dept + sys_user(负责人)，id 升序）。

        返回 (user, dept_name, leader_name) 元组列表。``conditions`` 已含数据权限条件。
        """
        leader = aliased(UserModel)
        stmt = (
            select(UserModel, DeptModel.dept_name, leader.user_name)
            .outerjoin(DeptModel, UserModel.dept_id == DeptModel.id)
            .outerjoin(leader, leader.id == DeptModel.leader)
            .where(UserModel.del_flag == SystemConstants.NORMAL)
        )
        if conditions:
            stmt = stmt.where(*conditions)
        stmt = stmt.order_by(asc(UserModel.id))
        result = await self.db.execute(stmt)
        return [(row[0], row[1], row[2]) for row in result.all()]

    # ==================== 唯一性校验 ====================
    async def exists_by(self, *conditions: Any) -> bool:
        stmt = select(func.count()).select_from(UserModel).where(UserModel.del_flag == SystemConstants.NORMAL, *conditions)
        return ((await self.db.execute(stmt)).scalar() or 0) > 0

    # ==================== 部门名批量回填 ====================
    async def map_dept_names(self, dept_ids: list[int]) -> dict[int, str]:
        if not dept_ids:
            return {}
        stmt = select(DeptModel.id, DeptModel.dept_name).where(DeptModel.del_flag == SystemConstants.NORMAL, DeptModel.id.in_(dept_ids))
        return {row[0]: row[1] for row in (await self.db.execute(stmt)).all()}

    # ==================== 用户-角色 / 用户-岗位 关联 ====================
    async def delete_user_roles(self, user_ids: list[int]) -> None:
        await self.db.execute(sa_delete(UserRoleModel).where(UserRoleModel.user_id.in_(user_ids)))

    async def insert_user_roles(self, user_id: int, role_ids: list[int]) -> int:
        if not role_ids:
            return 0
        self.db.add_all([UserRoleModel(user_id=user_id, role_id=role_id) for role_id in role_ids])
        await self.db.flush()
        return len(role_ids)

    async def delete_user_posts(self, user_ids: list[int]) -> None:
        await self.db.execute(sa_delete(UserPostModel).where(UserPostModel.user_id.in_(user_ids)))

    async def insert_user_posts(self, user_id: int, post_ids: list[int]) -> int:
        if not post_ids:
            return 0
        self.db.add_all([UserPostModel(user_id=user_id, post_id=post_id) for post_id in post_ids])
        await self.db.flush()
        return len(post_ids)

    async def list_role_ids_by_user_id(self, user_id: int) -> list[int]:
        """用户已绑定的角色ID。"""
        stmt = select(UserRoleModel.role_id).where(UserRoleModel.user_id == user_id)
        return list((await self.db.execute(stmt)).scalars().all())

    async def count_visible_posts(self, post_ids: list[int]) -> int:
        """统计数据权限可见的岗位数量（按 dept_id/create_by 行级过滤）。"""
        from app.api.v1.module_system.post.model import PostModel
        from app.core.permission import Permission

        stmt = select(func.count()).select_from(PostModel).where(PostModel.id.in_(post_ids))
        stmt = await Permission(PostModel, self.auth, self.db).filter_query(stmt)
        return (await self.db.execute(stmt)).scalar() or 0

    async def count_visible_roles(self, role_ids: list[int]) -> int:
        """统计数据权限可见的角色数量（按 create_dept/create_by 行级过滤）。"""
        from app.api.v1.module_system.role.model import RoleModel
        from app.core.permission import Permission

        stmt = select(func.count()).select_from(RoleModel).where(
            RoleModel.id.in_(role_ids), RoleModel.del_flag == SystemConstants.NORMAL
        )
        stmt = await Permission(RoleModel, self.auth, self.db).filter_query(stmt)
        return (await self.db.execute(stmt)).scalar() or 0

    # ==================== 写操作 ====================
    async def update_password(self, user_id: int, password: str) -> int:
        """重置密码。"""
        stmt = sa_update(UserModel).where(UserModel.id == user_id).values(password=password)
        result = await self.db.execute(stmt)
        await self.db.flush()
        return cast("CursorResult", result).rowcount or 0

    async def update_status(self, user_id: int, status: str) -> int:
        """修改状态。"""
        stmt = sa_update(UserModel).where(UserModel.id == user_id).values(status=status)
        result = await self.db.execute(stmt)
        await self.db.flush()
        return cast("CursorResult", result).rowcount or 0

    async def update_avatar(self, user_id: int, avatar: str) -> int:
        """修改头像。"""
        stmt = sa_update(UserModel).where(UserModel.id == user_id).values(avatar=avatar)
        result = await self.db.execute(stmt)
        await self.db.flush()
        return cast("CursorResult", result).rowcount or 0

    async def update_profile(self, user_id: int, values: dict[str, Any]) -> int:
        """修改个人基本资料。"""
        if not values:
            return 0
        stmt = sa_update(UserModel).where(UserModel.id == user_id).values(**values)
        result = await self.db.execute(stmt)
        await self.db.flush()
        return cast("CursorResult", result).rowcount or 0

    # ==================== 逻辑删除 ====================
    async def soft_delete_by_ids(self, user_ids: list[int]) -> int:
        """逻辑删除用户（置 del_flag='1'）。"""
        stmt = sa_update(UserModel).where(UserModel.id.in_(user_ids), UserModel.del_flag == SystemConstants.NORMAL).values(
            del_flag=SystemConstants.DISABLE
        )
        result = await self.db.execute(stmt)
        await self.db.flush()
        return cast("CursorResult", result).rowcount or 0
