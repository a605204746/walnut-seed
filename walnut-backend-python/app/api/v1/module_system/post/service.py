"""岗位业务逻辑。"""

from typing import Any

from sqlalchemy import asc, literal, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.module_system.post.crud import PostCrud
from app.api.v1.module_system.post.model import PostModel
from app.api.v1.module_system.post.schema import (
    DeptTreeQueryParam,
    PostCreateSchema,
    PostInfoSchema,
    PostOutSchema,
    PostQueryParam,
    PostUpdateSchema,
)
from app.common.constant import SystemConstants
from app.core.base_schema import AuthSchema
from app.core.exceptions import ServiceException
from app.utils.string_util import is_not_blank


class PostService:
    """岗位服务。"""

    def __init__(self, auth: AuthSchema, db: AsyncSession) -> None:
        self.auth = auth
        self.db = db
        self.crud = PostCrud(PostModel, auth, db)

    # ---------------- 部门辅助（惰性导入 DeptModel） ----------------
    async def _dept_and_child_ids(self, dept_id: int) -> list[int]:
        """查询部门及其所有子部门ID（含自身）。"""
        from app.api.v1.module_system.dept.model import DeptModel

        stmt = select(DeptModel.id).where(
            DeptModel.del_flag == SystemConstants.NORMAL,
            (literal(",") + DeptModel.ancestors + literal(",")).like(f"%,{dept_id},%"),
        )
        result = await self.db.execute(stmt)
        dept_ids = list(result.scalars().all())
        dept_ids.append(dept_id)
        return dept_ids

    async def _dept_name_map(self, dept_ids: list[int]) -> dict[int, str | None]:
        """批量查询部门名。"""
        from app.api.v1.module_system.dept.model import DeptModel

        stmt = select(DeptModel.id, DeptModel.dept_name).where(DeptModel.id.in_(dept_ids), DeptModel.del_flag == SystemConstants.NORMAL)
        result = await self.db.execute(stmt)
        return {row.id: row.dept_name for row in result.all()}

    async def _fill_dept_name(self, rows: list[PostOutSchema]) -> None:
        """批量回填部门名。"""
        if not rows:
            return
        dept_ids = sorted({row.dept_id for row in rows if row.dept_id is not None})
        if not dept_ids:
            return
        dept_names = await self._dept_name_map(dept_ids)
        for row in rows:
            row.dept_name = dept_names.get(row.dept_id) if row.dept_id is not None else None

    # ---------------- 查询条件 ----------------
    async def _build_conditions(self, req: PostQueryParam) -> list[Any]:
        conditions: list[Any] = []
        if is_not_blank(req.post_code):
            conditions.append(PostModel.post_code.like(f"%{req.post_code}%"))
        if is_not_blank(req.post_category):
            conditions.append(PostModel.post_category.like(f"%{req.post_category}%"))
        if is_not_blank(req.post_name):
            conditions.append(PostModel.post_name.like(f"%{req.post_name}%"))
        if is_not_blank(req.status):
            conditions.append(PostModel.status == req.status)
        if req.begin_time is not None and req.end_time is not None:
            conditions.append(PostModel.create_time.between(req.begin_time, req.end_time))
        if req.dept_id is not None:
            # 优先单部门搜索
            conditions.append(PostModel.dept_id == req.dept_id)
        elif req.belong_dept_id is not None:
            # 部门树搜索
            dept_ids = await self._dept_and_child_ids(req.belong_dept_id)
            conditions.append(PostModel.dept_id.in_(dept_ids))
        return conditions

    # ---------------- 查询 ----------------
    async def page_list(self, req: PostQueryParam) -> dict:
        """分页查询岗位列表。"""
        conditions = await self._build_conditions(req)
        result = await self.crud.page(req, *conditions)
        rows = [PostOutSchema.model_validate(post) for post in result["rows"]]
        await self._fill_dept_name(rows)
        return {"rows": [row.model_dump(by_alias=True, mode="json") for row in rows], "total": result["total"]}

    async def select_list(self, req: PostQueryParam) -> list[dict]:
        """查询岗位列表（导出使用）。"""
        conditions = await self._build_conditions(req)
        posts = await self.crud.list_all(*conditions)
        posts.sort(key=lambda p: (p.post_sort is None, p.post_sort))
        rows = [PostOutSchema.model_validate(post) for post in posts]
        await self._fill_dept_name(rows)
        return [row.model_dump(by_alias=True, mode="json") for row in rows]

    async def select_post_all(self) -> list[dict]:
        """查询所有岗位。"""
        posts = await self.crud.list_all()
        rows = [PostOutSchema.model_validate(post) for post in posts]
        await self._fill_dept_name(rows)
        return [row.model_dump(by_alias=True, mode="json") for row in rows]

    async def get_by_id(self, post_id: int) -> dict | None:
        """按岗位ID查询。"""
        post = await self.crud.get(post_id)
        if post is None:
            return None
        row = PostOutSchema.model_validate(post)
        await self._fill_dept_name([row])
        return row.model_dump(by_alias=True, mode="json")

    async def select_post_by_ids(self, post_ids: list[int]) -> list[dict]:
        """按岗位ID串查询正常状态岗位。"""
        posts = await self.crud.list_option_by_ids(post_ids)
        rows = [PostOutSchema.model_validate(post) for post in posts]
        await self._fill_dept_name(rows)
        return [row.model_dump(by_alias=True, mode="json") for row in rows]

    async def option_select(self, post_ids: list[int] | None, dept_id: int | None) -> list[dict]:
        """岗位选择框列表。"""
        if dept_id is not None:
            return await self.select_list(PostQueryParam(dept_id=dept_id))
        if post_ids:
            return await self.select_post_by_ids(post_ids)
        return []

    async def select_posts_by_user_id(self, user_id: int) -> list[dict]:
        """用户所属岗位（供用户模块使用）。"""
        posts = await self.crud.list_by_user_id(user_id)
        return [PostInfoSchema.model_validate(post).model_dump(by_alias=True, mode="json") for post in posts]

    async def select_post_list_by_user_id(self, user_id: int) -> list[int]:
        """用户所属岗位ID列表。"""
        posts = await self.crud.list_by_user_id(user_id)
        return [post.id for post in posts]

    # ---------------- 部门树（GET /post/deptTree） ----------------
    async def dept_tree_list(self, req: DeptTreeQueryParam) -> list[dict]:
        from app.api.v1.module_system.dept.model import DeptModel

        conditions: list[Any] = [DeptModel.del_flag == SystemConstants.NORMAL]
        if req.id is not None:
            conditions.append(DeptModel.id == req.id)
        if req.parent_id is not None:
            conditions.append(DeptModel.parent_id == req.parent_id)
        if is_not_blank(req.dept_name):
            conditions.append(DeptModel.dept_name.like(f"%{req.dept_name}%"))
        if is_not_blank(req.dept_category):
            conditions.append(DeptModel.dept_category.like(f"%{req.dept_category}%"))
        if is_not_blank(req.status):
            conditions.append(DeptModel.status == req.status)
        if req.begin_time is not None and req.end_time is not None:
            conditions.append(DeptModel.create_time.between(req.begin_time, req.end_time))
        if req.belong_dept_id is not None:
            dept_ids = await self._dept_and_child_ids(req.belong_dept_id)
            conditions.append(DeptModel.id.in_(dept_ids))

        stmt = select(DeptModel).where(*conditions).order_by(asc(DeptModel.ancestors), asc(DeptModel.parent_id), asc(DeptModel.order_num), asc(DeptModel.id))
        result = await self.db.execute(stmt)
        depts = list(result.scalars().all())
        return self._build_dept_tree(depts)

    @staticmethod
    def _build_dept_tree(depts: list[Any]) -> list[dict]:
        """构建部门树。"""
        if not depts:
            return []
        nodes = [
            {
                "id": dept.id,
                "parentId": dept.parent_id,
                "label": dept.dept_name,
                "weight": dept.order_num,
                "disabled": dept.status == SystemConstants.DISABLE,
            }
            for dept in depts
        ]
        id_set = {node["id"] for node in nodes}
        children_map: dict[Any, list[dict]] = {}
        for node in nodes:
            children_map.setdefault(node["parentId"], []).append(node)
        for node in nodes:
            children = children_map.get(node["id"])
            if children:
                node["children"] = children
        # 多根：parentId 不在节点ID集合中的即为根
        return [node for node in nodes if node["parentId"] not in id_set]

    # ---------------- 校验 ----------------
    async def check_post_name_unique(self, req: PostCreateSchema | PostUpdateSchema) -> bool:
        """校验岗位名称。"""
        assert req.post_name is not None and req.dept_id is not None  # schema 校验（validate_default）保证非空
        exclude_id = getattr(req, "id", None)
        return not await self.crud.exists_by_name(req.post_name, req.dept_id, exclude_id)

    async def check_post_code_unique(self, req: PostCreateSchema | PostUpdateSchema) -> bool:
        """校验岗位编码。"""
        assert req.post_code is not None  # schema 校验（validate_default）保证非空
        exclude_id = getattr(req, "id", None)
        return not await self.crud.exists_by_code(req.post_code, exclude_id)

    async def count_user_post_by_id(self, post_id: int) -> int:
        """岗位使用数量。"""
        return await self.crud.count_user_post(post_id)

    async def count_post_by_dept_id(self, dept_id: int) -> int:
        """部门下岗位数量（供部门模块使用）。"""
        return await self.crud.count_by_dept_id(dept_id)

    # ---------------- 写入 ----------------
    async def insert_post(self, req: PostCreateSchema) -> bool:
        """新增岗位。"""
        data = req.model_dump(exclude_none=True)
        post = await self.crud.create(PostModel(**data))
        return post.id is not None

    async def update_post(self, req: PostUpdateSchema) -> bool:
        """修改岗位（仅更新非空字段）。"""
        post = await self.crud.get(req.id)
        if post is None:
            return False
        data = req.model_dump(exclude_none=True, exclude={"id"})
        for field, value in data.items():
            setattr(post, field, value)
        await self.crud.update(post)
        return True

    async def delete_post_by_ids(self, post_ids: list[int]) -> int:
        """批量删除岗位（已分配用户不允许删除）。"""
        posts = await self.crud.list_all(PostModel.id.in_(post_ids))
        for post in posts:
            if await self.count_user_post_by_id(post.id) > 0:
                raise ServiceException(f"{post.post_name}已分配，不能删除!")
        return await self.crud.delete_batch([post.id for post in posts])
