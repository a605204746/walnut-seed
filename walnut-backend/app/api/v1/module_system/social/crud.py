"""社交登录绑定关系的数据访问层。"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.module_system.social.model import SocialModel
from app.core.base_crud import CRUDBase
from app.core.base_schema import AuthSchema
from app.utils.string_util import is_not_blank


class SocialCrud(CRUDBase[SocialModel]):
    """sys_social 数据访问（逻辑删除表，查询一律追加 del_flag='0'）。"""

    def __init__(self, model: type[SocialModel], auth: AuthSchema, db: AsyncSession) -> None:
        super().__init__(model, auth, db)

    async def get_by_id(self, social_id: int) -> SocialModel | None:
        """按主键查询（过滤已逻辑删除）。"""
        return await self.get_by(id=social_id, del_flag="0")

    async def list_by_user_id(self, user_id: int) -> list[SocialModel]:
        """按用户ID查询授权列表。"""
        return await self.list_all(SocialModel.user_id == user_id, SocialModel.del_flag == "0")

    async def select_by_auth_id(self, auth_id: str) -> list[SocialModel]:
        """按平台唯一ID查询授权信息。"""
        return await self.list_all(SocialModel.auth_id == auth_id, SocialModel.del_flag == "0")

    async def query_list(self, user_id: int | None = None, auth_id: str | None = None, source: str | None = None) -> list[SocialModel]:
        """条件查询授权列表。"""
        conditions = [SocialModel.del_flag == "0"]
        if user_id is not None:
            conditions.append(SocialModel.user_id == user_id)
        if is_not_blank(auth_id):
            conditions.append(SocialModel.auth_id == auth_id)
        if is_not_blank(source):
            conditions.append(SocialModel.source == source)
        return await self.list_all(*conditions)

    async def logic_delete(self, social_id: int) -> bool:
        """逻辑删除（del_flag 置为 '1'）。"""
        instance = await self.get_by_id(social_id)
        if instance is None:
            return False
        instance.del_flag = "1"
        await self.update(instance)
        return True
