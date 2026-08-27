"""通知公告的业务层。"""

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.module_system.notice.crud import NoticeCrud
from app.api.v1.module_system.notice.model import NoticeModel
from app.api.v1.module_system.notice.schema import NoticeCreateSchema, NoticeOutSchema, NoticeQueryParam, NoticeUpdateSchema
from app.common.constant import SystemConstants
from app.core.base_schema import AuthSchema
from app.utils.string_util import is_not_blank


class NoticeService:
    """通知公告服务。"""

    def __init__(self, auth: AuthSchema, db: AsyncSession) -> None:
        self.auth = auth
        self.db = db
        self.crud = NoticeCrud(NoticeModel, auth, db)

    # ---------------- 创建人翻译（惰性导入 UserModel） ----------------
    async def _user_name_map(self, user_ids: list[int]) -> dict[int, str | None]:
        from app.api.v1.module_system.user.model import UserModel

        stmt = select(UserModel.id, UserModel.user_name).where(UserModel.id.in_(user_ids), UserModel.del_flag == SystemConstants.NORMAL)
        result = await self.db.execute(stmt)
        return {row.id: row.user_name for row in result.all()}

    async def _fill_create_by_name(self, rows: list[NoticeOutSchema]) -> None:
        """批量回填创建人账号。"""
        if not rows:
            return
        user_ids = sorted({row.create_by for row in rows if row.create_by is not None})
        if not user_ids:
            return
        user_names = await self._user_name_map(user_ids)
        for row in rows:
            row.create_by_name = user_names.get(row.create_by) if row.create_by is not None else None

    async def _find_user_id_by_name(self, user_name: str) -> int | None:
        """按用户账号查用户ID。"""
        from app.api.v1.module_system.user.model import UserModel

        stmt = select(UserModel.id).where(UserModel.user_name == user_name, UserModel.del_flag == SystemConstants.NORMAL)
        result = await self.db.execute(stmt)
        return result.scalars().first()

    # ---------------- 查询 ----------------
    async def _build_conditions(self, req: NoticeQueryParam) -> list[Any]:
        conditions: list[Any] = []
        if is_not_blank(req.notice_title):
            conditions.append(NoticeModel.notice_title.like(f"%{req.notice_title}%"))
        if is_not_blank(req.notice_type):
            conditions.append(NoticeModel.notice_type == req.notice_type)
        if req.create_by_name is not None and is_not_blank(req.create_by_name):
            user_id = await self._find_user_id_by_name(req.create_by_name)
            # 用户不存在时查不到任何公告
            conditions.append(NoticeModel.create_by == user_id if user_id is not None else NoticeModel.create_by.is_(None))
        return conditions

    async def page_list(self, req: NoticeQueryParam) -> dict:
        """分页查询通知公告列表。"""
        conditions = await self._build_conditions(req)
        result = await self.crud.page(req, *conditions)
        rows = [NoticeOutSchema.model_validate(notice) for notice in result["rows"]]
        await self._fill_create_by_name(rows)
        return {"rows": [row.model_dump(by_alias=True, mode="json") for row in rows], "total": result["total"]}

    async def get_by_id(self, notice_id: int) -> dict | None:
        """按公告ID查询。"""
        notice = await self.crud.get(notice_id)
        if notice is None:
            return None
        row = NoticeOutSchema.model_validate(notice)
        await self._fill_create_by_name([row])
        return row.model_dump(by_alias=True, mode="json")

    # ---------------- 写入 ----------------
    @staticmethod
    def _encode_content(content: str | None) -> bytes | None:
        """公告内容字符串转 UTF-8 字节入库（BLOB 列）。"""
        return content.encode("utf-8") if content is not None else None

    async def insert_notice(self, req: NoticeCreateSchema) -> bool:
        """新增公告。"""
        data = req.model_dump(exclude_none=True)
        data["notice_content"] = self._encode_content(data.get("notice_content"))
        notice = await self.crud.create(NoticeModel(**data))
        return notice.id is not None

    async def update_notice(self, req: NoticeUpdateSchema) -> bool:
        """修改公告（仅更新非空字段）。"""
        notice = await self.crud.get(req.id)
        if notice is None:
            return False
        data = req.model_dump(exclude_none=True, exclude={"id"})
        if "notice_content" in data:
            data["notice_content"] = self._encode_content(data["notice_content"])
        for field, value in data.items():
            setattr(notice, field, value)
        await self.crud.update(notice)
        return True

    async def delete_notice_by_ids(self, notice_ids: list[int]) -> int:
        """批量删除公告。"""
        return await self.crud.delete_batch(notice_ids)

    # ---------------- 字典辅助（供新增公告 SSE 通知取类型标签） ----------------
    async def get_notice_type_label(self, notice_type: str | None) -> str:
        """公告类型字典标签（直查字典表，未找到时返回原值）。"""
        if not notice_type:
            return ""
        from app.api.v1.module_system.dict.model import DictDataModel

        stmt = select(DictDataModel.dict_label).where(
            DictDataModel.dict_type == "sys_notice_type",
            DictDataModel.dict_value == notice_type,
        )
        result = await self.db.execute(stmt)
        return result.scalars().first() or notice_type
