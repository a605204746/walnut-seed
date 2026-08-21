"""参数设置业务层。

缓存语义：参数值按 ``sys_config:{config_key}`` 缓存；
Redis 不可用时降级为直接查库（``redis`` 参数传 None 即可）。
"""

from datetime import datetime
from typing import cast

from redis.asyncio.client import Redis
from sqlalchemy import update
from sqlalchemy.engine import CursorResult
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

from app.api.v1.module_system.config.crud import ConfigCrud
from app.api.v1.module_system.config.model import ConfigModel
from app.api.v1.module_system.config.schema import ConfigCreateSchema, ConfigQueryParam, ConfigUpdateByKeySchema, ConfigUpdateSchema
from app.common.constant import SystemConstants
from app.common.enums import CacheNames
from app.core.base_crud import DEFAULT_USER_ID
from app.core.base_schema import AuthSchema
from app.core.exceptions import ServiceException
from app.core.redis_crud import RedisUtils
from app.utils.string_util import is_not_blank


class ConfigService:
    """参数配置业务层。"""

    def __init__(self, auth: AuthSchema, db: AsyncSession) -> None:
        self.auth = auth
        self.db = db
        self.config_crud = ConfigCrud(ConfigModel, auth, db)

    # ---------------- 查询 ----------------
    def _build_conditions(self, param: ConfigQueryParam) -> list:
        conditions: list[ColumnElement] = []
        if is_not_blank(param.config_name):
            conditions.append(ConfigModel.config_name.like(f"%{param.config_name}%"))
        if is_not_blank(param.config_type):
            conditions.append(ConfigModel.config_type == param.config_type)
        if is_not_blank(param.config_key):
            conditions.append(ConfigModel.config_key.like(f"%{param.config_key}%"))
        if param.begin_time is not None and param.end_time is not None:
            conditions.append(ConfigModel.create_time.between(param.begin_time, param.end_time))
        return conditions

    async def select_page_config_list(self, param: ConfigQueryParam) -> dict:
        """分页查询参数配置列表。"""
        return await self.config_crud.page(param, *self._build_conditions(param))

    async def select_config_list(self, param: ConfigQueryParam) -> list[ConfigModel]:
        """查询参数配置列表（导出用）。"""
        return await self.config_crud.list_all(*self._build_conditions(param))

    async def select_config_by_id(self, config_id: int) -> ConfigModel | None:
        """根据ID查询参数配置。"""
        return await self.config_crud.get(config_id)

    async def select_config_by_key(self, config_key: str, redis: Redis | None) -> str:
        """根据键名查询参数值（缓存优先，未找到返回空串）。"""
        cache_key = CacheNames.SYS_CONFIG_KEY + config_key
        if redis is not None:
            raw = await RedisUtils(redis).get(cache_key)
            if raw is not None:
                # 兼容 Redis 中带引号的 JSON 字符串值，统一解包为纯文本
                if isinstance(raw, str) and len(raw) >= 2 and raw.startswith('"') and raw.endswith('"'):
                    import json as _json

                    try:
                        return _json.loads(raw)
                    except (ValueError, TypeError):
                        pass
                return raw
        instance = await self.config_crud.get_by(config_key=config_key)
        value = instance.config_value if instance and instance.config_value is not None else ""
        if redis is not None:
            await RedisUtils(redis).set(cache_key, value)
        return value

    async def select_register_enabled(self, redis: Redis | None) -> bool:
        """获取注册开关。"""
        config_value = await self.select_config_by_key("sys.account.registerUser", redis)
        return config_value.strip().lower() in ("true", "yes", "1", "on")

    # ---------------- 写操作 ----------------
    async def insert_config(self, req: ConfigCreateSchema, redis: Redis | None) -> str:
        """新增参数配置（写后回填缓存）。"""
        if req.config_key is None:
            raise ServiceException("参数键名不能为空")
        if req.config_value is None:
            raise ServiceException("参数键值不能为空")
        data = {k: v for k, v in req.model_dump(exclude_unset=True).items() if v is not None}
        instance = ConfigModel(**data)
        await self.config_crud.create(instance)
        if redis is not None:
            await RedisUtils(redis).set(CacheNames.SYS_CONFIG_KEY + req.config_key, req.config_value)
        return req.config_value

    async def update_config(self, req: ConfigUpdateSchema | ConfigUpdateByKeySchema, redis: Redis | None) -> str | None:
        """修改参数配置（有 id 按主键改，无 id 按键名改）。"""
        if req.config_key is None:
            raise ServiceException("参数键名不能为空")
        row = 0
        req_id = getattr(req, "id", None)
        if req_id is not None:
            instance = await self.config_crud.get(req_id)
            if instance is None:
                raise ServiceException("操作失败")
            assert instance.config_key is not None
            if instance.config_key != req.config_key:
                if redis is not None:
                    await RedisUtils(redis).delete(CacheNames.SYS_CONFIG_KEY + instance.config_key)
            data = req.model_dump(exclude_unset=True)
            data.pop("id", None)
            for field, value in data.items():
                if value is not None:
                    setattr(instance, field, value)
            await self.config_crud.update(instance)
            row = 1
        else:
            if redis is not None:
                await RedisUtils(redis).delete(CacheNames.SYS_CONFIG_KEY + req.config_key)
            data = req.model_dump(exclude_unset=True)
            data.pop("id", None)
            values = {k: v for k, v in data.items() if v is not None}
            if values:
                values["update_by"] = self.auth.user.id or DEFAULT_USER_ID
                values["update_time"] = datetime.now()
                result = await self.db.execute(update(ConfigModel).where(ConfigModel.config_key == req.config_key).values(**values))
                row = cast("CursorResult", result).rowcount or 0
        if row > 0:
            if redis is not None:
                await RedisUtils(redis).set(CacheNames.SYS_CONFIG_KEY + req.config_key, req.config_value)
            return req.config_value
        raise ServiceException("操作失败")

    async def delete_config_by_ids(self, config_ids: list[int], redis: Redis | None) -> None:
        """批量删除参数配置（内置参数不允许删除）。"""
        config_list = await self.config_crud.list_all(ConfigModel.id.in_(config_ids))
        for item in config_list:
            assert item.config_key is not None
            if item.config_type == SystemConstants.YES:
                raise ServiceException(f"内置参数【{item.config_key}】不能删除")
            if redis is not None:
                await RedisUtils(redis).delete(CacheNames.SYS_CONFIG_KEY + item.config_key)
        await self.config_crud.delete_batch(config_ids)

    async def reset_config_cache(self, redis: Redis | None) -> None:
        """重置参数缓存。"""
        if redis is None:
            return
        await RedisUtils(redis).delete_by_pattern(CacheNames.SYS_CONFIG_KEY + "*")

    async def check_config_key_unique(self, req: ConfigCreateSchema | ConfigUpdateSchema) -> bool:
        """校验参数键名是否唯一。"""
        if req.config_key is None:
            raise ServiceException("参数键名不能为空")
        exclude_id = getattr(req, "id", None)
        return not await self.config_crud.exists_by_config_key(req.config_key, exclude_id=exclude_id)
