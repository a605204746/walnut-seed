"""部门管理服务。

- 数据权限：按 sys_dept 自身 id 列行级过滤，条件在 ``_dept_data_scope_condition``
  内构建（多角色条件 OR 连接）；
- ancestors 维护：移动部门时同步更新自身与所有子孙部门的祖级列表。
"""

from __future__ import annotations

from datetime import datetime
from datetime import time as dtime

from sqlalchemy import false, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

from app.api.v1.module_system.dept.crud import DeptCrud
from app.api.v1.module_system.dept.model import DeptModel
from app.api.v1.module_system.dept.schema import DeptCreateSchema, DeptOutSchema, DeptQueryParam, DeptUpdateSchema
from app.api.v1.module_system.role.model import RoleModel
from app.common.constant import SystemConstants
from app.common.enums import DataScopeType
from app.core.base_schema import AuthSchema
from app.core.exceptions import ServiceException
from app.utils.string_util import SEPARATOR, is_blank, str2list


class DeptService:
    """部门管理服务。"""

    def __init__(self, auth: AuthSchema, db: AsyncSession) -> None:
        self.auth = auth
        self.db = db
        self.crud = DeptCrud(DeptModel, auth, db)

    # ==================== 数据权限 ====================
    async def _dept_data_scope_condition(self) -> ColumnElement | None:
        """构建 sys_dept 行级数据权限条件。

        按部门自身 id 列过滤：
        - 超级管理员 / 任一角色 ALL 范围 / 用户无角色 → 不过滤（返回 None）；
        - 自定义 → id IN (角色授权部门)；本部门 → id = 用户部门；
          本部门及以下(或本人) → id IN (用户部门及子孙)；仅本人 → 恒假（部门表无创建人账号列，走兜底）；
        - 多角色条件以 OR 连接。
        """
        user = self.auth.user
        if not user or not user.id:
            return None
        if user.is_superuser or user.id == SystemConstants.SUPER_ADMIN_ID:
            return None
        role_scopes = await self.crud.list_role_scopes(user.id)
        if not role_scopes:
            # 角色集为空时过滤条件为空 → 不过滤
            return None
        conditions: list[ColumnElement] = []
        for role_id, data_scope in role_scopes:
            scope = DataScopeType.find_code(data_scope)
            if scope is None:
                raise ServiceException(f"角色数据范围异常 => {data_scope}")
            if scope == DataScopeType.ALL:
                return None
            if scope == DataScopeType.CUSTOM:
                conditions.append(DeptModel.id.in_(self.crud.role_custom_dept_subquery(role_id)))
            elif scope == DataScopeType.DEPT:
                conditions.append(DeptModel.id == (user.dept_id if user.dept_id is not None else -1))
            elif scope in (DataScopeType.DEPT_AND_CHILD, DataScopeType.DEPT_AND_CHILD_OR_SELF):
                # DEPT_AND_CHILD_OR_SELF 的按人匹配在部门表不适用，等价于仅部门及以下
                conditions.append(DeptModel.id.in_(await self._dept_and_child_ids(user.dept_id)))
            else:
                # SELF：部门表无创建人账号列，无法按人匹配，恒假兜底
                conditions.append(false())
        return or_(*conditions) if conditions else None

    async def _dept_and_child_ids(self, dept_id: int | None) -> list[int]:
        """部门及其全部子孙部门ID（含自身）。"""
        if dept_id is None:
            return [-1]
        ids = await self.crud.list_descendant_ids(dept_id)
        ids.append(dept_id)
        return ids

    async def check_dept_data_scope(self, dept_id: int | None) -> None:
        """校验是否有该部门的数据权限。"""
        if dept_id is None:
            return
        user = self.auth.user
        if user.is_superuser or user.id == SystemConstants.SUPER_ADMIN_ID:
            return
        conditions: list[ColumnElement] = [DeptModel.id == dept_id]
        scope = await self._dept_data_scope_condition()
        if scope is not None:
            conditions.append(scope)
        if await self.crud.count_dept(*conditions) == 0:
            raise ServiceException("没有权限访问部门数据！")

    # ==================== 查询 ====================
    async def _build_query_conditions(self, param: DeptQueryParam | None) -> list[ColumnElement]:
        """构建列表查询条件。"""
        conditions: list[ColumnElement] = []
        if param is None:
            return conditions
        if param.id is not None:
            conditions.append(DeptModel.id == param.id)
        if param.parent_id is not None:
            conditions.append(DeptModel.parent_id == param.parent_id)
        if not is_blank(param.dept_name):
            conditions.append(DeptModel.dept_name.like(f"%{param.dept_name}%"))
        if not is_blank(param.dept_category):
            conditions.append(DeptModel.dept_category.like(f"%{param.dept_category}%"))
        if not is_blank(param.status):
            conditions.append(DeptModel.status == param.status)
        # begin/end 同时存在才生效
        if param.begin_time is not None and param.end_time is not None:
            conditions.append(DeptModel.create_time >= datetime.combine(param.begin_time, dtime.min))
            conditions.append(DeptModel.create_time <= datetime.combine(param.end_time, dtime.min))
        if param.belong_dept_id is not None:
            # 部门树搜索：归属部门及其全部子孙
            conditions.append(DeptModel.id.in_(await self._dept_and_child_ids(param.belong_dept_id)))
        return conditions

    async def select_dept_list(self, param: DeptQueryParam | None = None) -> list[DeptModel]:
        """部门列表（带数据权限；返回模型供树构建复用）。"""
        conditions = await self._build_query_conditions(param)
        scope = await self._dept_data_scope_condition()
        if scope is not None:
            conditions.append(scope)
        return await self.crud.list_depts(*conditions)

    async def list_dept_out(self, param: DeptQueryParam | None = None) -> list[DeptOutSchema]:
        """部门列表出参（回填 parentName/leaderName）。"""
        return await self._fill_dept_out(await self.select_dept_list(param))

    async def list_dept_out_exclude(self, dept_id: int) -> list[DeptOutSchema]:
        """查询部门列表并排除指定节点及其子孙。"""
        depts = await self.select_dept_list(None)
        target = str(dept_id)
        kept = [dept for dept in depts if dept.id != dept_id and target not in str2list(dept.ancestors)]
        return await self._fill_dept_out(kept)

    async def _fill_dept_out(self, depts: list[DeptModel]) -> list[DeptOutSchema]:
        """批量回填父部门名称与负责人账号。"""
        if not depts:
            return []
        parent_ids = list({dept.parent_id for dept in depts if dept.parent_id is not None})
        leader_ids = list({dept.leader for dept in depts if dept.leader is not None})
        parent_names = await self.crud.map_dept_names(parent_ids)
        leader_names = await self.crud.map_leader_names(leader_ids)
        out: list[DeptOutSchema] = []
        for dept in depts:
            item = DeptOutSchema.model_validate(dept)
            item.parent_name = parent_names.get(dept.parent_id) if dept.parent_id is not None else None
            item.leader_name = leader_names.get(dept.leader) if dept.leader is not None else None
            out.append(item)
        return out

    async def select_dept_by_id(self, dept_id: int) -> DeptOutSchema | None:
        """部门详情。"""
        dept = await self.crud.get_by_id(dept_id)
        if dept is None:
            return None
        return (await self._fill_dept_out([dept]))[0]

    async def select_dept_by_ids(self, dept_ids: list[int] | None) -> list[DeptOutSchema]:
        """部门选择框列表（status='0'，仅输出 id/deptName/leader）。"""
        conditions: list[ColumnElement] = [DeptModel.status == SystemConstants.NORMAL]
        if dept_ids:
            conditions.append(DeptModel.id.in_(dept_ids))
        scope = await self._dept_data_scope_condition()
        if scope is not None:
            conditions.append(scope)
        rows = await self.crud.list_depts(*conditions)
        # 仅回填 id/dept_name/leader 三个字段，其余出参字段为空
        return [DeptOutSchema(id=row.id, dept_name=row.dept_name, leader=row.leader) for row in rows]

    # ==================== 树构建 ====================
    @staticmethod
    def _tree_sort_key(dept: DeptModel) -> tuple[int, int]:
        return (dept.order_num if dept.order_num is not None else 0, dept.id or 0)

    def build_dept_tree_select(self, depts: list[DeptModel]) -> list[dict]:
        """构建下拉树。

        节点字段：id/parentId/label/weight/disabled/children，
        叶子节点无 children 键，子节点按 orderNum 排序。
        """
        if not depts:
            return []
        id_set = {dept.id for dept in depts}
        children_map: dict[int | None, list[DeptModel]] = {}
        for dept in depts:
            children_map.setdefault(dept.parent_id, []).append(dept)

        def build_node(node: DeptModel) -> dict:
            item: dict = {
                "id": node.id,
                "parentId": node.parent_id,
                "label": node.dept_name,
                "weight": node.order_num,
                "disabled": node.status == SystemConstants.DISABLE,
            }
            kids = children_map.get(node.id)
            if kids:
                item["children"] = [build_node(kid) for kid in sorted(kids, key=self._tree_sort_key)]
            return item

        roots = [dept for dept in depts if dept.parent_id not in id_set]
        return [build_node(root) for root in sorted(roots, key=self._tree_sort_key)]

    async def select_dept_tree_list(self, param: DeptQueryParam | None = None) -> list[dict]:
        """部门树列表（带数据权限）。"""
        return self.build_dept_tree_select(await self.select_dept_list(param))

    async def select_dept_list_by_role_id(self, role_id: int) -> list[int]:
        """角色已授权的部门ID（deptCheckStrictly 时排除父部门）。"""
        stmt = select(RoleModel).where(RoleModel.id == role_id, RoleModel.del_flag == SystemConstants.NORMAL)
        role = (await self.db.execute(stmt)).scalars().first()
        if role is None:
            # 角色不存在时给出明确业务异常
            raise ServiceException("角色不存在")
        return await self.crud.list_dept_ids_by_role_id(role_id, bool(role.dept_check_strictly or 0))

    # ==================== 校验 ====================
    async def select_normal_children_dept_by_id(self, dept_id: int) -> int:
        """正常状态的子孙部门数。"""
        return await self.crud.count_normal_children(dept_id)

    async def has_child_by_dept_id(self, dept_id: int) -> bool:
        """是否存在子部门。"""
        return await self.crud.exists_dept(DeptModel.parent_id == dept_id)

    async def check_dept_exist_user(self, dept_id: int) -> bool:
        """部门下是否存在用户。"""
        return (await self.crud.count_user_in_dept(dept_id)) > 0

    async def count_post_by_dept_id(self, dept_id: int) -> int:
        """部门下岗位数。"""
        return await self.crud.count_post_in_dept(dept_id)

    async def check_dept_name_unique(self, req: DeptCreateSchema | DeptUpdateSchema) -> bool:
        """同父级下部门名称唯一性校验。"""
        conditions: list[ColumnElement] = [DeptModel.dept_name == req.dept_name, DeptModel.parent_id == req.parent_id]
        dept_id = getattr(req, "id", None)
        if dept_id is not None:
            conditions.append(DeptModel.id != dept_id)
        return not await self.crud.exists_dept(*conditions)

    # ==================== 写操作 ====================
    async def insert_dept(self, req: DeptCreateSchema) -> int:
        """新增部门。"""
        parent = await self.crud.get_by_id(req.parent_id)
        if parent is None:
            # 上级部门不存在时给出明确业务异常
            raise ServiceException("上级部门不存在，无法新增")
        # 如果父节点不为正常状态,则不允许新增子节点
        if parent.status != SystemConstants.NORMAL:
            raise ServiceException("部门停用，不允许新增")
        data = req.model_dump(exclude_none=True)
        data["ancestors"] = f"{parent.ancestors}{SEPARATOR}{req.parent_id}"
        dept = DeptModel(**data)
        await self.crud.create(dept)
        return 1

    async def update_dept(self, req: DeptUpdateSchema) -> int:
        """修改部门（含子孙部门 ancestors 维护）。"""
        old_dept = await self.crud.get_by_id(req.id)
        if old_dept is None:
            raise ServiceException("部门不存在，无法修改")
        # None 字段不更新
        update_fields = req.model_dump(exclude_none=True)
        update_fields.pop("id", None)
        if old_dept.parent_id != req.parent_id:
            # 如果是新父部门 则校验是否具有新父部门权限 避免越权
            await self.check_dept_data_scope(req.parent_id)
            new_parent = await self.crud.get_by_id(req.parent_id)
            if new_parent is not None:
                new_ancestors = f"{new_parent.ancestors}{SEPARATOR}{new_parent.id}"
                update_fields["ancestors"] = new_ancestors
                await self._update_dept_children(req.id, new_ancestors, old_dept.ancestors or "")
        for field, value in update_fields.items():
            setattr(old_dept, field, value)
        await self.crud.update(old_dept)
        # 如果部门是启用状态且存在上级部门，则启用该部门的所有上级部门
        if old_dept.status == SystemConstants.NORMAL and old_dept.ancestors and old_dept.ancestors != SystemConstants.ROOT_DEPT_ANCESTORS:
            ancestor_ids = [int(item) for item in str2list(old_dept.ancestors)]
            await self.crud.update_status_normal(ancestor_ids)
        return 1

    async def _update_dept_children(self, dept_id: int, new_ancestors: str, old_ancestors: str) -> None:
        """移动部门时同步更新所有子孙部门的 ancestors。"""
        children = await self.crud.list_descendants(dept_id)
        for child in children:
            child_ancestors = child.ancestors or ""
            # 仅替换首次出现的旧祖级列表
            child.ancestors = child_ancestors.replace(old_ancestors, new_ancestors, 1)
            await self.crud.update(child)

    async def delete_dept_by_id(self, dept_id: int) -> int:
        """删除部门（逻辑删除）。"""
        return await self.crud.logical_delete(dept_id)
