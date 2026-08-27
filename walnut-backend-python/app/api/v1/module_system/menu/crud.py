"""菜单域数据访问。

菜单表 sys_menu 无 del_flag，查询无需追加逻辑删除条件。
"""

from __future__ import annotations

from typing import cast

from sqlalchemy import delete as sa_delete
from sqlalchemy import func, or_, select
from sqlalchemy.engine import CursorResult

from app.api.v1.module_system.menu.model import MenuModel
from app.api.v1.module_system.role.model import RoleMenuModel, RoleModel
from app.common.constant import SystemConstants
from app.core.base_crud import CRUDBase
from app.utils.string_util import is_not_blank


class MenuCrud(CRUDBase[MenuModel]):
    """菜单数据访问。"""

    # ---------------- 权限辅助 ----------------
    def _is_super_admin(self) -> bool:
        return self.auth.user.id == SystemConstants.SUPER_ADMIN_ID

    # ---------------- 列表 / 树查询 ----------------
    async def select_menu_list(self, query) -> list[MenuModel]:
        """按条件查询菜单列表，非超管仅返回其被授权的菜单。"""
        conditions = []
        if not self._is_super_admin():
            conditions.append(MenuModel.id.in_(self.auth.menu_ids or []))
        if is_not_blank(query.menu_name):
            conditions.append(MenuModel.menu_name.like(f"%{query.menu_name}%"))
        if is_not_blank(query.visible):
            conditions.append(MenuModel.visible == query.visible)
        if is_not_blank(query.status):
            conditions.append(MenuModel.status == query.status)
        if is_not_blank(query.menu_type):
            conditions.append(MenuModel.menu_type == query.menu_type)
        if query.parent_id is not None:
            conditions.append(MenuModel.parent_id == query.parent_id)
        stmt = select(MenuModel).where(*conditions).order_by(MenuModel.parent_id, MenuModel.order_num)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def select_menu_tree_by_user_id(self) -> list[MenuModel]:
        """查询构建路由所需的菜单（M/C 且状态正常）。"""
        conditions = [
            MenuModel.menu_type.in_([SystemConstants.TYPE_DIR, SystemConstants.TYPE_MENU]),
            MenuModel.status == SystemConstants.NORMAL,
        ]
        if not self._is_super_admin():
            conditions.append(MenuModel.id.in_(self.auth.menu_ids or []))
        stmt = select(MenuModel).where(*conditions).order_by(MenuModel.parent_id, MenuModel.order_num)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def select_menu_by_id(self, menu_id: int) -> MenuModel | None:
        return await self.get(menu_id)

    # ---------------- 删除前置校验 ----------------
    async def has_child_by_menu_id(self, menu_id: int) -> bool:
        stmt = select(func.count()).select_from(MenuModel).where(MenuModel.parent_id == menu_id)
        return ((await self.db.execute(stmt)).scalar() or 0) > 0

    async def has_child_by_menu_ids(self, menu_ids: list[int]) -> bool:
        if not menu_ids:
            return False
        stmt = (
            select(func.count())
            .select_from(MenuModel)
            .where(MenuModel.parent_id.in_(menu_ids), MenuModel.id.not_in(menu_ids))
        )
        return ((await self.db.execute(stmt)).scalar() or 0) > 0

    async def check_menu_exist_role(self, menu_id: int) -> bool:
        stmt = select(func.count()).select_from(RoleMenuModel).where(RoleMenuModel.menu_id == menu_id)
        return ((await self.db.execute(stmt)).scalar() or 0) > 0

    # ---------------- 角色菜单 ----------------
    async def select_menu_list_by_role_id(self, role_id: int) -> list[int]:
        """查询角色已授权菜单ID（含 menuCheckStrictly 父子联动处理）。"""
        role = await self.db.get(RoleModel, role_id)
        menu_check_strictly = bool(role.menu_check_strictly) if role is not None else False

        # 角色已授权菜单（仅角色状态正常时计入）
        assigned_subq = (
            select(RoleMenuModel.menu_id)
            .join(RoleModel, RoleModel.id == RoleMenuModel.role_id, isouter=True)
            .where(RoleMenuModel.role_id == role_id, RoleModel.status == SystemConstants.NORMAL)
            .scalar_subquery()
        )
        stmt = (
            select(MenuModel.id)
            .where(MenuModel.id.in_(assigned_subq))
            .order_by(MenuModel.parent_id, MenuModel.order_num)
        )
        if menu_check_strictly:
            # 过滤掉作为父节点的菜单，仅保留实际勾选的末级菜单
            parent_subq = select(MenuModel.parent_id).where(MenuModel.id.in_(assigned_subq)).scalar_subquery()
            stmt = stmt.where(MenuModel.id.not_in(parent_subq))
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    # ---------------- 唯一性校验数据访问 ----------------
    async def exists_menu_name(self, menu_name: str, parent_id: int | None, exclude_id: int | None) -> bool:
        """同级下是否已存在同名菜单。"""
        conditions = [MenuModel.menu_name == menu_name, MenuModel.parent_id == parent_id]
        if exclude_id is not None:
            conditions.append(MenuModel.id != exclude_id)
        stmt = select(func.count()).select_from(MenuModel).where(*conditions)
        return ((await self.db.execute(stmt)).scalar() or 0) > 0

    async def select_route_conflict_candidates(self, path: str | None, route_name: str | None) -> list[MenuModel]:
        """查询路由冲突候选菜单（M/C 类型且 path 命中 path 或 routeName）。"""
        stmt = select(MenuModel).where(
            MenuModel.menu_type.in_([SystemConstants.TYPE_DIR, SystemConstants.TYPE_MENU]),
            or_(MenuModel.path == path, MenuModel.path == route_name),
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    # ---------------- 角色菜单关联清理 ----------------
    async def delete_role_menu_by_menu_ids(self, menu_ids: list[int]) -> int:
        if not menu_ids:
            return 0
        stmt = sa_delete(RoleMenuModel).where(RoleMenuModel.menu_id.in_(menu_ids))
        result = await self.db.execute(stmt)
        return cast("CursorResult", result).rowcount or 0
