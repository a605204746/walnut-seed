"""角色业务逻辑。

- 数据权限：``check_role_data_scope`` 通过数据权限可见数量比对进行校验；
- authUser 授权/取消授权对每个目标用户执行「超管不可操作 + 数据权限」双校验；
- 防自我提权：非超管操作者不允许修改自身所属角色（update_role / auth_data_scope）；
- 逻辑删除：删除角色置 del_flag='1'，同时物理清理 sys_role_menu / sys_role_dept；
- 角色变更后踢出在线用户、自定义数据权限缓存清理等会话/缓存横切逻辑，
  不在本服务内实现，由主线统一接入。
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.module_system.role.crud import RoleCrud
from app.api.v1.module_system.role.model import RoleModel
from app.api.v1.module_system.role.schema import (
    AuthUserCancelSchema,
    AuthUserOutSchema,
    AuthUserQueryParam,
    RoleCreateSchema,
    RoleDataScopeSchema,
    RoleOutSchema,
    RoleQueryParam,
    RoleUpdateSchema,
    dump_camel,
)
from app.common.constant import SystemConstants
from app.common.enums import DataScopeType
from app.core.base_schema import AuthSchema
from app.core.exceptions import ServiceException
from app.utils.string_util import is_not_blank


class RoleService:
    """角色服务。"""

    def __init__(self, auth: AuthSchema, db: AsyncSession) -> None:
        self.auth = auth
        self.db = db
        self.crud = RoleCrud(RoleModel, auth, db)

    # ==================== 通用辅助 ====================
    def _current_is_super_admin(self) -> bool:
        user = self.auth.user
        return user.id == SystemConstants.SUPER_ADMIN_ID or bool(user.is_superuser)

    @staticmethod
    def _bool_to_int(value: bool | None) -> int | None:
        """布尔转实体列 1/0（menuCheckStrictly/deptCheckStrictly）。"""
        if value is None:
            return None
        return 1 if value else 0

    # ==================== 校验 ====================
    async def check_role_allowed(self, role_id: int | None, role_key: str | None) -> None:
        """校验角色是否允许操作。"""
        if role_id is not None and role_id == SystemConstants.SUPER_ADMIN_ID:
            raise ServiceException("不允许操作超级管理员角色")
        keys = (SystemConstants.SUPER_ADMIN_ROLE_KEY, SystemConstants.ADMIN_ROLE_KEY)
        # 新增不允许使用管理员标识符
        if role_id is None and role_key in keys:
            raise ServiceException("不允许使用系统内置管理员角色标识符!")
        # 修改不允许修改管理员标识符
        if role_id is not None:
            roles = await self.crud.list_by_ids([role_id])
            sys_role = roles[0] if roles else None
            if sys_role is not None and sys_role.role_key != role_key:
                if sys_role.role_key in keys:
                    raise ServiceException("不允许修改系统内置管理员角色标识符!")
                if role_key in keys:
                    raise ServiceException("不允许使用系统内置管理员角色标识符!")

    async def check_role_data_scope(self, role_ids: list[int] | None) -> None:
        """校验角色是否有数据权限。"""
        if not role_ids or self._current_is_super_admin():
            return
        count = await self.crud.count_visible_roles(role_ids)
        if count != len(role_ids):
            raise ServiceException("没有权限访问部分角色数据！")

    async def check_role_name_unique(self, req: RoleCreateSchema | RoleUpdateSchema) -> bool:
        """校验角色名称是否唯一。"""
        if req.role_name is None:
            raise ServiceException("角色名称不能为空")
        exclude_id = getattr(req, "id", None)
        return not await self.crud.exists_by_name(req.role_name, exclude_id)

    async def check_role_key_unique(self, req: RoleCreateSchema | RoleUpdateSchema) -> bool:
        """校验角色权限字符是否唯一。"""
        if req.role_key is None:
            raise ServiceException("角色权限字符串不能为空")
        exclude_id = getattr(req, "id", None)
        return not await self.crud.exists_by_key(req.role_key, exclude_id)

    async def count_user_role_by_id(self, role_id: int) -> int:
        """角色已分配用户数量。"""
        return await self.crud.count_user_role_by_role_id(role_id)

    async def _current_user_role_ids(self) -> list[int]:
        """当前登录用户已绑定的角色ID列表（防自我提权校验使用）。"""
        from app.api.v1.module_system.user.model import UserRoleModel

        stmt = select(UserRoleModel.role_id).where(UserRoleModel.user_id == self.auth.user.id)
        return list((await self.db.execute(stmt)).scalars().all())

    async def check_role_self_edit(self, role_id: int | None) -> None:
        """防自我提权：非超管操作者不允许编辑自身所属角色。"""
        if role_id is None or self._current_is_super_admin():
            return
        if role_id in await self._current_user_role_ids():
            raise ServiceException("不允许修改自身所属角色，防止自我提权")

    async def check_auth_user_allowed(self, user_ids: list[int]) -> None:
        """授权/取消授权目标用户校验：不可操作超管 + 操作者对目标有数据权限。

        惰性导入 UserService 避免模块间循环依赖。
        """
        from app.api.v1.module_system.user.service import UserService

        user_service = UserService(self.auth, self.db)
        for user_id in user_ids:
            await user_service.check_user_allowed(user_id)
            await user_service.check_user_data_scope(user_id)

    # ==================== 查询条件 ====================
    def _build_conditions(self, req: RoleQueryParam) -> list[Any]:
        conditions: list[Any] = []
        if is_not_blank(req.role_name):
            conditions.append(RoleModel.role_name.like(f"%{req.role_name}%"))
        if is_not_blank(req.status):
            conditions.append(RoleModel.status == req.status)
        if is_not_blank(req.role_key):
            conditions.append(RoleModel.role_key.like(f"%{req.role_key}%"))
        if req.begin_time is not None and req.end_time is not None:
            conditions.append(RoleModel.create_time.between(req.begin_time, req.end_time))
        return conditions

    # ==================== 查询 ====================
    async def page_list(self, req: RoleQueryParam) -> dict:
        """分页查询角色列表。"""
        conditions = self._build_conditions(req)
        result = await self.crud.page_role_list(req, *conditions)
        rows = [dump_camel(RoleOutSchema.model_validate(role)) for role in result["rows"]]
        return {"rows": rows, "total": result["total"]}

    async def select_list(self, req: RoleQueryParam) -> list[RoleModel]:
        """查询角色列表（导出使用，不分页）。"""
        conditions = self._build_conditions(req)
        return await self.crud.list_role(*conditions)

    async def get_by_id(self, role_id: int) -> dict | None:
        """按角色ID查询（含数据权限校验）。"""
        await self.check_role_data_scope([role_id])
        role = await self.crud.get_role_by_id(role_id)
        if role is None:
            return None
        return dump_camel(RoleOutSchema.model_validate(role))

    async def option_select(self, role_ids: list[int] | None) -> list[dict]:
        """角色选择框列表。"""
        roles = await self.crud.list_option_by_ids(role_ids)
        return [dump_camel(RoleOutSchema.model_validate(role)) for role in roles]

    # ==================== 写入 ====================
    def _apply_fields(self, role: RoleModel, req: Any) -> None:
        """仅设置非 None 字段（None 字段不覆盖现值）。"""
        if getattr(req, "role_name", None) is not None:
            role.role_name = req.role_name
        if getattr(req, "role_key", None) is not None:
            role.role_key = req.role_key
        if getattr(req, "role_sort", None) is not None:
            role.role_sort = req.role_sort
        if getattr(req, "data_scope", None) is not None:
            role.data_scope = req.data_scope
        if getattr(req, "menu_check_strictly", None) is not None:
            role.menu_check_strictly = self._bool_to_int(req.menu_check_strictly)
        if getattr(req, "dept_check_strictly", None) is not None:
            role.dept_check_strictly = self._bool_to_int(req.dept_check_strictly)
        if getattr(req, "status", None) is not None:
            role.status = req.status
        if getattr(req, "remark", None) is not None:
            role.remark = req.remark

    async def insert_role(self, req: RoleCreateSchema) -> bool:
        """新增角色（写角色 + 角色菜单关联；自定义数据范围时落角色部门关联）。"""
        data: dict[str, Any] = {
            "role_name": req.role_name,
            "role_key": req.role_key,
            "role_sort": req.role_sort,
            "data_scope": req.data_scope,
            "status": req.status,
            "remark": req.remark,
        }
        if req.menu_check_strictly is not None:
            data["menu_check_strictly"] = self._bool_to_int(req.menu_check_strictly)
        if req.dept_check_strictly is not None:
            data["dept_check_strictly"] = self._bool_to_int(req.dept_check_strictly)
        role = await self.crud.create(RoleModel(**data))
        await self.crud.insert_role_menu(role.id, req.menu_ids or [])
        # 自定义数据范围（data_scope=2）：写入角色-部门授权关联
        if req.data_scope == DataScopeType.CUSTOM.value:
            await self.crud.insert_role_dept(role.id, req.dept_ids or [])
        return True

    async def update_role(self, req: RoleUpdateSchema) -> bool:
        """修改角色（更新角色 + 先删后插角色菜单关联；防自我提权）。"""
        if req.id is None:
            raise ServiceException("角色ID不能为空")
        await self.check_role_self_edit(req.id)
        if req.status == SystemConstants.DISABLE and await self.count_user_role_by_id(req.id) > 0:
            raise ServiceException("角色已分配，不能禁用!")
        role = await self.crud.get_role_by_id(req.id)
        if role is None:
            return False
        self._apply_fields(role, req)
        await self.crud.update(role)
        await self.crud.delete_role_menu(req.id)
        await self.crud.insert_role_menu(req.id, req.menu_ids or [])
        # 自定义数据范围（data_scope=2）：先删后插角色-部门授权关联
        if req.data_scope == DataScopeType.CUSTOM.value:
            await self.crud.delete_role_dept(req.id)
            await self.crud.insert_role_dept(req.id, req.dept_ids or [])
        return True

    async def update_role_status(self, role_id: int, status: str | None) -> bool:
        """修改角色状态。"""
        if status is None:
            raise ServiceException("角色状态不能为空")
        if status == SystemConstants.DISABLE and await self.count_user_role_by_id(role_id) > 0:
            raise ServiceException("角色已分配，不能禁用!")
        role = await self.crud.get_role_by_id(role_id)
        if role is None:
            return False
        role.status = status
        await self.crud.update(role)
        return True

    async def auth_data_scope(self, req: RoleDataScopeSchema) -> bool:
        """修改数据权限（更新 data_scope + 先删后插角色部门关联；防自我提权）。"""
        if req.id is None:
            raise ServiceException("角色ID不能为空")
        await self.check_role_self_edit(req.id)
        role = await self.crud.get_role_by_id(req.id)
        if role is None:
            return False
        self._apply_fields(role, req)
        await self.crud.update(role)
        await self.crud.delete_role_dept(req.id)
        await self.crud.insert_role_dept(req.id, req.dept_ids or [])
        return True

    async def delete_role_by_ids(self, role_ids: list[int]) -> int:
        """批量删除角色（超管/已分配不可删）。"""
        await self.check_role_data_scope(role_ids)
        roles = await self.crud.list_by_ids(role_ids)
        for role in roles:
            await self.check_role_allowed(role.id, role.role_key)
            if await self.count_user_role_by_id(role.id) > 0:
                raise ServiceException(f"{role.role_name}已分配，不能删除!")
        await self.crud.delete_role_menu_batch(role_ids)
        await self.crud.delete_role_dept_batch(role_ids)
        return await self.crud.soft_delete_by_ids(role_ids)

    # ==================== authUser（分配用户） ====================
    def _build_user_conditions(self, req: AuthUserQueryParam) -> list[Any]:
        from app.api.v1.module_system.user.model import UserModel

        conditions: list[Any] = []
        if is_not_blank(req.user_name):
            conditions.append(UserModel.user_name.like(f"%{req.user_name}%"))
        if is_not_blank(req.phonenumber):
            conditions.append(UserModel.phonenumber.like(f"%{req.phonenumber}%"))
        if is_not_blank(req.status):
            conditions.append(UserModel.status == req.status)
        return conditions

    async def _fill_dept_name(self, rows: list[AuthUserOutSchema]) -> None:
        """批量回填部门名。"""
        if not rows:
            return
        from app.api.v1.module_system.dept.model import DeptModel

        dept_ids = sorted({row.dept_id for row in rows if row.dept_id is not None})
        if not dept_ids:
            return
        stmt = select(DeptModel.id, DeptModel.dept_name).where(DeptModel.id.in_(dept_ids), DeptModel.del_flag == SystemConstants.NORMAL)
        result = await self.db.execute(stmt)
        dept_names = {row.id: row.dept_name for row in result.all()}
        for row in rows:
            row.dept_name = dept_names.get(row.dept_id)

    async def allocated_list(self, req: AuthUserQueryParam) -> dict:
        """已分配用户分页。"""
        conditions = self._build_user_conditions(req)
        result = await self.crud.page_allocated_users(req, req.role_id, *conditions)
        rows = [AuthUserOutSchema.model_validate(user) for user in result["rows"]]
        await self._fill_dept_name(rows)
        return {"rows": [dump_camel(row) for row in rows], "total": result["total"]}

    async def unallocated_list(self, req: AuthUserQueryParam) -> dict:
        """未分配用户分页。"""
        conditions = self._build_user_conditions(req)
        result = await self.crud.page_unallocated_users(req, req.role_id, *conditions)
        rows = [AuthUserOutSchema.model_validate(user) for user in result["rows"]]
        await self._fill_dept_name(rows)
        return {"rows": [dump_camel(row) for row in rows], "total": result["total"]}

    async def cancel_auth_user(self, req: AuthUserCancelSchema) -> int:
        """取消授权用户（目标用户校验：不可操作超管 + 数据权限）。"""
        if req.role_id is None:
            raise ServiceException("角色ID不能为空")
        if req.user_id is None:
            raise ServiceException("用户ID不能为空")
        if self.auth.user.id == req.user_id:
            raise ServiceException("不允许修改当前用户角色!")
        await self.check_auth_user_allowed([req.user_id])
        return await self.crud.delete_auth_user(req.role_id, req.user_id)

    async def cancel_auth_users(self, role_id: int, user_ids: list[int]) -> int:
        """批量取消授权用户（目标用户校验：不可操作超管 + 数据权限）。"""
        if self.auth.user.id in user_ids:
            raise ServiceException("不允许修改当前用户角色!")
        await self.check_auth_user_allowed(user_ids)
        return await self.crud.delete_auth_users(role_id, user_ids)

    async def select_auth_users(self, role_id: int, user_ids: list[int]) -> int:
        """批量选择用户授权（含角色数据权限 + 目标用户校验）。"""
        await self.check_role_data_scope([role_id])
        if self.auth.user.id in user_ids:
            raise ServiceException("不允许修改当前用户角色!")
        await self.check_auth_user_allowed(user_ids)
        return await self.crud.insert_auth_users(role_id, user_ids)

    # ==================== deptTree ====================
    async def role_dept_tree(self, role_id: int) -> dict:
        """获取指定角色的部门树列表（返回 checkedKeys + depts）。

        复用部门服务的树构建与角色已选部门查询（dept 模块已实现 deptCheckStrictly 语义）。
        """
        from app.api.v1.module_system.dept.service import DeptService

        dept_service = DeptService(self.auth, self.db)
        checked_keys = await dept_service.select_dept_list_by_role_id(role_id)
        depts = await dept_service.select_dept_tree_list()
        return {"checkedKeys": checked_keys, "depts": depts}
