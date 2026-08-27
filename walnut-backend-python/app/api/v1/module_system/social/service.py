"""社交登录绑定关系的业务层。"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.module_system.social.crud import SocialCrud
from app.api.v1.module_system.social.model import SocialModel
from app.api.v1.module_system.social.schema import SocialCreateSchema, SocialOutSchema, SocialUpdateSchema
from app.core.base_schema import AuthSchema


class SocialService:
    """社会化关系服务。"""

    def __init__(self, auth: AuthSchema, db: AsyncSession) -> None:
        self.auth = auth
        self.db = db
        self.crud = SocialCrud(SocialModel, auth, db)

    async def query_by_id(self, social_id: int) -> SocialOutSchema | None:
        """查询社会化关系。"""
        instance = await self.crud.get_by_id(social_id)
        return SocialOutSchema.model_validate(instance) if instance else None

    async def query_list(self, user_id: int | None = None, auth_id: str | None = None, source: str | None = None) -> list[SocialOutSchema]:
        """条件查询社会化关系列表。"""
        rows = await self.crud.query_list(user_id=user_id, auth_id=auth_id, source=source)
        return [SocialOutSchema.model_validate(row) for row in rows]

    async def query_list_by_user_id(self, user_id: int) -> list[SocialOutSchema]:
        """按用户ID查询社会化关系列表。"""
        rows = await self.crud.list_by_user_id(user_id)
        return [SocialOutSchema.model_validate(row) for row in rows]

    async def insert_by_bo(self, req: SocialCreateSchema) -> SocialModel:
        """新增授权关系（返回含主键的实体）。"""
        instance = SocialModel(**req.model_dump())
        await self.crud.create(instance)
        return instance

    async def update_by_bo(self, req: SocialUpdateSchema) -> bool:
        """更新社会化关系（仅更新非空字段）。"""
        instance = await self.crud.get_by_id(req.id)
        if instance is None:
            return False
        for field, value in req.model_dump(exclude_none=True).items():
            if field == "id":
                continue
            setattr(instance, field, value)
        await self.crud.update(instance)
        return True

    async def delete_with_valid_by_id(self, social_id: int) -> bool:
        """删除社会化关系（逻辑删除）。"""
        return await self.crud.logic_delete(social_id)

    async def select_by_auth_id(self, auth_id: str) -> list[SocialOutSchema]:
        """根据 authId 查询用户授权信息（供社交登录使用）。"""
        rows = await self.crud.select_by_auth_id(auth_id)
        return [SocialOutSchema.model_validate(row) for row in rows]
