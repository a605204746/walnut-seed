"""客户端管理的业务层。

说明：按客户端id查询当前直查库，未接入 Redis 缓存；缓存读写留待认证/装配主线按需接入。
"""

import hashlib
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.module_system.client.crud import ClientCrud
from app.api.v1.module_system.client.model import ClientModel
from app.api.v1.module_system.client.schema import ClientCreateSchema, ClientOutSchema, ClientQueryParam, ClientUpdateSchema
from app.core.base_schema import AuthSchema
from app.utils.string_util import is_not_blank, join_comma


class ClientService:
    """客户端管理服务。"""

    def __init__(self, auth: AuthSchema, db: AsyncSession) -> None:
        self.auth = auth
        self.db = db
        self.crud = ClientCrud(ClientModel, auth, db)

    # ---------------- 查询 ----------------
    async def query_by_id(self, client_id: int) -> dict | None:
        """按主键查询。"""
        client = await self.crud.get(client_id)
        if client is None:
            return None
        return ClientOutSchema.model_validate(client).model_dump(by_alias=True, mode="json")

    async def query_by_client_key(self, client_key: str) -> ClientOutSchema | None:
        """按客户端key查询（供认证登录时的客户端校验使用）。"""
        client = await self.crud.get_by_client_key(client_key)
        if client is None:
            return None
        return ClientOutSchema.model_validate(client)

    async def query_by_client_id(self, client_id: str) -> ClientOutSchema | None:
        """按客户端id查询（未接 Redis 缓存，直查库）。"""
        client = await self.crud.get_by_client_id(client_id)
        if client is None:
            return None
        return ClientOutSchema.model_validate(client)

    def _build_conditions(self, req: ClientQueryParam) -> list[Any]:
        conditions: list[Any] = []
        if is_not_blank(req.client_id):
            conditions.append(ClientModel.client_id == req.client_id)
        if is_not_blank(req.client_key):
            conditions.append(ClientModel.client_key == req.client_key)
        if is_not_blank(req.client_secret):
            conditions.append(ClientModel.client_secret == req.client_secret)
        if is_not_blank(req.status):
            conditions.append(ClientModel.status == req.status)
        return conditions

    async def query_page_list(self, req: ClientQueryParam) -> dict:
        """分页查询客户端列表。"""
        result = await self.crud.page(req, *self._build_conditions(req))
        rows = [ClientOutSchema.model_validate(client).model_dump(by_alias=True, mode="json") for client in result["rows"]]
        return {"rows": rows, "total": result["total"]}

    async def query_list(self, req: ClientQueryParam) -> list[dict]:
        """查询客户端列表（导出使用）。"""
        clients = await self.crud.list_all(*self._build_conditions(req))
        return [ClientOutSchema.model_validate(client).model_dump(by_alias=True, mode="json") for client in clients]

    # ---------------- 校验 ----------------
    async def check_client_key_unique(self, req: ClientCreateSchema | ClientUpdateSchema) -> bool:
        """校验客户端key是否唯一。"""
        assert req.client_key is not None  # schema 校验（validate_default）保证非空
        exclude_id = getattr(req, "id", None)
        return not await self.crud.exists_by_key(req.client_key, exclude_id)

    # ---------------- 写入 ----------------
    async def insert_by_bo(self, req: ClientCreateSchema) -> bool:
        """新增客户端（clientId = md5(clientKey + clientSecret)）。"""
        data = req.model_dump(exclude_none=True)
        grant_type_list = data.pop("grant_type_list", [])
        data["grant_type"] = join_comma(grant_type_list)
        data["client_id"] = hashlib.md5(f"{req.client_key}{req.client_secret}".encode()).hexdigest()
        client = await self.crud.create(ClientModel(**data))
        return client.id is not None

    async def update_by_bo(self, req: ClientUpdateSchema) -> bool:
        """修改客户端（仅更新非空字段）。"""
        client = await self.crud.get(req.id)
        if client is None:
            return False
        data = req.model_dump(exclude_none=True, exclude={"id"})
        grant_type_list = data.pop("grant_type_list", None)
        if grant_type_list is not None:
            data["grant_type"] = join_comma(grant_type_list)
        for field, value in data.items():
            setattr(client, field, value)
        await self.crud.update(client)
        return True

    async def update_client_status(self, client_id: str, status: str) -> int:
        """修改状态。"""
        return await self.crud.update_status_by_client_id(client_id, status)

    async def delete_with_valid_by_ids(self, ids: list[int]) -> bool:
        """校验并批量删除（逻辑删除）。"""
        return await self.crud.delete_batch(ids) > 0
