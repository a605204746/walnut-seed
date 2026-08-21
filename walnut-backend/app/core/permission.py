"""数据权限过滤。

在查询构建阶段追加过滤条件实现行级数据权限。依赖业务模型（role/dept/user），
采用惰性导入，核心架构阶段可独立导入；导入失败直接抛错（fail-closed：
权限组件失败必须拒绝而非放行）。

DataScopeType（code 即角色表 data_scope 字段取值），多角色条件以 OR 连接：
- 1 全部、2 自定义（create_dept IN 角色授权部门）、3 本部门、
  4 本部门及以下（create_dept IN 本部门及 ancestors 含本部门的子孙部门）、
  5 仅本人、6 本部门及以下或本人。
无角色的用户仅可见本人创建的数据（fail-closed）。
"""

from typing import Any

from sqlalchemy import false, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

from app.common.enums import DataScopeType
from app.core.base_schema import AuthSchema


class Permission:
    """为业务模型提供数据权限过滤（按角色 data_scope 追加行级条件）。

    ``dept_column`` 可覆盖过滤使用的部门列（默认取模型 ``create_dept``），
    如 sys_user 列表按 RuoYi 契约使用 ``dept_id``。
    """

    def __init__(self, model: Any, auth: AuthSchema, db: AsyncSession, dept_column: Any = None) -> None:
        self.model = model
        self.auth = auth
        self.db = db
        self.dept_column = dept_column if dept_column is not None else getattr(model, "create_dept", None)

    async def filter_query(self, query: Any) -> Any:
        condition = await self.build_condition()
        return query.where(condition) if condition is not None else query

    async def build_condition(self) -> ColumnElement | None:
        """构建行级数据权限条件（None 表示不过滤：超级管理员）。"""
        user = self.auth.user
        if not user or not user.id:
            return None
        # 超级管理员不过滤
        if user.is_superuser:
            return None
        return await self._filter_by_data_scope()

    async def _filter_by_data_scope(self) -> ColumnElement | None:
        # fail-closed：业务模型缺失时抛错，绝不静默放行
        try:
            from app.api.v1.module_system.dept.model import DeptModel
            from app.api.v1.module_system.role.model import RoleDeptModel, RoleModel
            from app.api.v1.module_system.user.model import UserRoleModel
        except Exception as exc:
            raise RuntimeError("数据权限组件初始化失败：业务模型（role/dept/user）缺失，拒绝执行查询") from exc

        from app.common.constant import SystemConstants
        from app.core.exceptions import ServiceException

        user = self.auth.user
        # 无 create_by 字段的模型不做数据权限过滤
        if not hasattr(self.model, "create_by"):
            return None

        # 取当前用户角色的数据范围集合（仅计未删除角色）
        stmt = (
            select(RoleModel.id, RoleModel.data_scope)
            .join(UserRoleModel, UserRoleModel.role_id == RoleModel.id)
            .where(UserRoleModel.user_id == user.id, RoleModel.del_flag == SystemConstants.NORMAL)
        )
        result = await self.db.execute(stmt)
        role_scopes = [(row[0], row[1]) for row in result.all()]

        # 无角色 → 仅本人数据（fail-closed）
        if not role_scopes:
            return self.model.create_by == user.id

        conditions: list[ColumnElement] = []
        for role_id, data_scope in role_scopes:
            scope = DataScopeType.find_code(data_scope)
            if scope is None:
                raise ServiceException(f"角色数据范围异常 => {data_scope}")
            if scope == DataScopeType.ALL:
                # 任一角色为全部数据权限 → 不过滤
                return None
            if scope == DataScopeType.CUSTOM:
                # 自定义：部门列 IN 该角色授权部门（sys_role_dept）
                if self.dept_column is not None:
                    conditions.append(self.dept_column.in_(select(RoleDeptModel.dept_id).where(RoleDeptModel.role_id == role_id)))
            elif scope == DataScopeType.DEPT:
                if self.dept_column is not None:
                    conditions.append(self.dept_column == (user.dept_id if user.dept_id is not None else -1))
            elif scope in (DataScopeType.DEPT_AND_CHILD, DataScopeType.DEPT_AND_CHILD_OR_SELF):
                dept_cond: ColumnElement = false()
                if self.dept_column is not None and user.dept_id is not None:
                    dept_cond = self.dept_column.in_(_dept_and_child_subquery(DeptModel, user.dept_id))
                if scope == DataScopeType.DEPT_AND_CHILD:
                    conditions.append(dept_cond)
                else:
                    conditions.append(dept_cond | (self.model.create_by == user.id))
            elif scope == DataScopeType.SELF:
                conditions.append(self.model.create_by == user.id)

        # 兜底：无有效部门/本人条件时仅本人（fail-closed）
        return or_(*conditions) if conditions else self.model.create_by == user.id


def _dept_and_child_subquery(dept_model: Any, dept_id: int):
    """本部门 + 所有 ancestors 包含本部门 ID 的子孙部门子查询（含逻辑删除过滤）。"""
    from app.common.constant import SystemConstants

    return select(dept_model.id).where(
        dept_model.del_flag == SystemConstants.NORMAL,
        or_(dept_model.id == dept_id, func.find_in_set(str(int(dept_id)), dept_model.ancestors) != 0),
    )
