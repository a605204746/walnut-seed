"""操作日志与登录日志的业务层。

- ``consume_oper_log``：操作日志事件消费者，主线通过
  ``set_oper_log_consumer(consume_oper_log)`` 注册后由 OperationLogRoute 后台任务调用；
- ``record_login_infor``：登录日志写入函数，供认证模块调用。
"""

from datetime import datetime, time
from typing import Any

from fastapi import Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

from app.api.v1.module_system.client.model import ClientModel
from app.api.v1.module_system.dept.model import DeptModel
from app.api.v1.module_system.dict.model import DictDataModel
from app.api.v1.module_system.log.crud import LogininforCrud, OperLogCrud
from app.api.v1.module_system.log.model import LogininforModel, OperLogModel
from app.api.v1.module_system.log.schema import (
    OPERATOR_TYPE_LABELS,
    LogininforFilterSchema,
    LogininforOutSchema,
    LogininforQueryParam,
    OperLogFilterSchema,
    OperLogOutSchema,
    OperLogQueryParam,
)
from app.api.v1.module_system.user.model import UserModel
from app.common.constant import Constants
from app.common.dataclasses import OperLogEvent
from app.config.setting import settings
from app.core.base_schema import AuthSchema
from app.core.database import async_db_session
from app.core.logger import logger
from app.utils.common_util import get_client_ip
from app.utils.date_util import parse_date
from app.utils.ip_local_util import get_real_address_by_ip
from app.utils.string_util import is_not_blank

# ==================== 查询条件构造 ====================


def _oper_log_conditions(query: OperLogFilterSchema) -> list:
    """操作日志查询条件。"""
    conditions: list[ColumnElement[bool]] = []
    if is_not_blank(query.oper_ip):
        conditions.append(OperLogModel.oper_ip.like(f"%{query.oper_ip}%"))
    if is_not_blank(query.title):
        conditions.append(OperLogModel.title.like(f"%{query.title}%"))
    if query.business_type is not None and query.business_type > 0:
        conditions.append(OperLogModel.business_type == query.business_type)
    if query.business_types:
        conditions.append(OperLogModel.business_type.in_(query.business_types))
    if query.status is not None:
        conditions.append(OperLogModel.status == query.status)
    if is_not_blank(query.oper_name):
        conditions.append(OperLogModel.oper_name.like(f"%{query.oper_name}%"))
    if query.begin_time is not None and query.end_time is not None:
        conditions.append(
            OperLogModel.oper_time.between(
                datetime.combine(query.begin_time, time.min),
                datetime.combine(query.end_time, time(23, 59, 59)),
            )
        )
    return conditions


def _logininfor_conditions(query: LogininforFilterSchema) -> list:
    """登录日志查询条件。"""
    conditions: list[ColumnElement[bool]] = []
    if is_not_blank(query.ipaddr):
        conditions.append(LogininforModel.ipaddr.like(f"%{query.ipaddr}%"))
    if is_not_blank(query.status):
        conditions.append(LogininforModel.status == query.status)
    if is_not_blank(query.user_name):
        conditions.append(LogininforModel.user_name.like(f"%{query.user_name}%"))
    if query.begin_time is not None and query.end_time is not None:
        conditions.append(
            LogininforModel.login_time.between(
                datetime.combine(query.begin_time, time.min),
                datetime.combine(query.end_time, time(23, 59, 59)),
            )
        )
    return conditions


async def _dict_label_map(db: AsyncSession, dict_type: str) -> dict[Any | None, Any | None]:
    """字典值→标签映射（导出时用于字典字段转换）。"""
    stmt = select(DictDataModel.dict_value, DictDataModel.dict_label).where(DictDataModel.dict_type == dict_type)
    result = await db.execute(stmt)
    return {value: label for value, label in result.all() if value is not None and label is not None}



# ==================== 操作日志 ====================


class OperLogService:
    """操作日志服务。"""

    def __init__(self, auth: AuthSchema, db: AsyncSession) -> None:
        self.auth = auth
        self.db = db
        self.crud = OperLogCrud(OperLogModel, auth, db)

    async def page_list(self, query: OperLogQueryParam) -> dict:
        """分页查询操作日志列表。"""
        page = await self.crud.page(query, *_oper_log_conditions(query))
        page["rows"] = [OperLogOutSchema.model_validate(row) for row in page["rows"]]
        return page

    async def list_all(self, query: OperLogFilterSchema) -> list[OperLogModel]:
        """查询系统操作日志集合。"""
        return await self.crud.list_all(*_oper_log_conditions(query))

    async def delete_by_ids(self, oper_ids: list[int]) -> int:
        """批量删除系统操作日志。"""
        return await self.crud.delete_batch(oper_ids)

    async def select_by_id(self, oper_id: int) -> OperLogOutSchema | None:
        """查询操作日志详细。"""
        instance = await self.crud.get(oper_id)
        return OperLogOutSchema.model_validate(instance) if instance else None

    async def clean(self) -> None:
        """清空操作日志。"""
        await self.crud.clean()

    async def export_rows(self, query: OperLogFilterSchema) -> list[dict]:
        """导出数据行（字典字段转标签）。"""
        rows = await self.list_all(query)
        oper_type_labels = await _dict_label_map(self.db, "sys_oper_type")
        status_labels = await _dict_label_map(self.db, "sys_common_status")
        result: list[dict] = []
        for row in rows:
            item = OperLogOutSchema.model_validate(row).model_dump()
            if row.business_type is not None:
                item["business_type"] = oper_type_labels.get(str(row.business_type), row.business_type)
            if row.operator_type is not None:
                item["operator_type"] = OPERATOR_TYPE_LABELS.get(str(row.operator_type), row.operator_type)
            if row.status is not None:
                item["status"] = status_labels.get(str(row.status), row.status)
            result.append(item)
        return result

    # ---------------- 操作日志写入（事件消费） ----------------

    async def _dept_name_by_user_name(self, user_name: str) -> str | None:
        """按操作人账号联查部门名称（事件未携带 dept_name 时补齐）。"""
        stmt = (
            select(DeptModel.dept_name)
            .join(UserModel, UserModel.dept_id == DeptModel.id)
            .where(UserModel.user_name == user_name, UserModel.del_flag == "0", DeptModel.del_flag == "0")
            .limit(1)
        )
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def insert_from_event(self, event: OperLogEvent) -> None:
        """操作日志事件入库。"""
        dept_name = event.dept_name
        if not dept_name and is_not_blank(event.oper_name):
            dept_name = await self._dept_name_by_user_name(event.oper_name or "")
        oper_time = parse_date(event.oper_time) if event.oper_time else None
        instance = OperLogModel(
            title=event.title,
            business_type=event.business_type,
            method=event.method,
            request_method=event.request_method,
            operator_type=event.operator_type,
            oper_name=event.oper_name,
            dept_name=dept_name,
            oper_url=event.oper_url,
            oper_ip=event.oper_ip,
            oper_location=get_real_address_by_ip(event.oper_ip),
            oper_param=event.oper_param,
            json_result=event.json_result,
            status=event.status,
            error_msg=event.error_msg,
            oper_time=oper_time or datetime.now(),
            cost_time=event.cost_time,
        )
        await self.crud.create(instance)


async def consume_oper_log(event: OperLogEvent) -> None:
    """操作日志事件消费者。

    由主线调用 ``set_oper_log_consumer(consume_oper_log)`` 注册；
    在独立数据库会话中写入 sys_oper_log（后台任务执行，无请求级会话可用）。
    """
    async with async_db_session() as session, session.begin():
        await OperLogService(AuthSchema(), session).insert_from_event(event)


# ==================== 登录日志 ====================


class LogininforService:
    """系统访问记录服务。"""

    def __init__(self, auth: AuthSchema, db: AsyncSession) -> None:
        self.auth = auth
        self.db = db
        self.crud = LogininforCrud(LogininforModel, auth, db)

    async def page_list(self, query: LogininforQueryParam) -> dict:
        """分页查询登录日志列表。"""
        page = await self.crud.page(query, *_logininfor_conditions(query))
        page["rows"] = [LogininforOutSchema.model_validate(row) for row in page["rows"]]
        return page

    async def list_all(self, query: LogininforFilterSchema) -> list[LogininforModel]:
        """查询系统登录日志集合。"""
        return await self.crud.list_all(*_logininfor_conditions(query))

    async def delete_by_ids(self, info_ids: list[int]) -> int:
        """批量删除系统登录日志。"""
        return await self.crud.delete_batch(info_ids)

    async def clean(self) -> None:
        """清空系统登录日志。"""
        await self.crud.clean()

    async def export_rows(self, query: LogininforFilterSchema) -> list[dict]:
        """导出数据行（字典字段转标签）。"""
        rows = await self.list_all(query)
        device_type_labels = await _dict_label_map(self.db, "sys_device_type")
        status_labels = await _dict_label_map(self.db, "sys_common_status")
        result: list[dict] = []
        for row in rows:
            item = LogininforOutSchema.model_validate(row).model_dump()
            if row.device_type:
                item["device_type"] = device_type_labels.get(row.device_type, row.device_type)
            if row.status:
                item["status"] = status_labels.get(row.status, row.status)
            result.append(item)
        return result


def _parse_user_agent(user_agent: str | None) -> tuple[str | None, str | None]:
    """解析 User-Agent 得到 (浏览器, 操作系统) 名称。"""
    if not user_agent:
        return None, None
    try:
        from ua_parser import parse

        result = parse(user_agent)
        browser = result.user_agent.family if result.user_agent and result.user_agent.family else None
        os_name = result.os.family if result.os and result.os.family else None
        return browser, os_name
    except Exception as e:
        logger.warning(f"User-Agent 解析失败: {e}")
        return None, None


async def record_login_infor(
    request: Request,
    username: str | None,
    status: str | None,
    message: str | None,
    client_key: str | None = None,
    device_type: str | None = None,
) -> None:
    """写入登录日志。

    供认证模块调用：``status`` 取登录动作标识
    （Login-Success/Login-Fail/Logout/Register），入库时转为 '0'成功/'1'失败。
    ``client_key``/``device_type`` 缺省时按请求头 clientid 联查 sys_client 补齐。
    """
    browser, os_name = _parse_user_agent(request.headers.get("User-Agent"))
    ip = get_client_ip(request)
    address = get_real_address_by_ip(ip)
    # 按固定格式打印信息到日志
    logger.info("[{}]{}[{}][{}][{}]", ip or "", address, username or "", status or "", message or "")

    # 客户端信息
    if not client_key:
        client_id = request.headers.get(settings.CLIENT_ID_HEADER) or request.query_params.get(settings.CLIENT_ID_HEADER)
        if is_not_blank(client_id):
            async with async_db_session() as session:
                stmt = select(ClientModel).where(ClientModel.client_id == client_id, ClientModel.del_flag == "0").limit(1)
                client = (await session.execute(stmt)).scalars().first()
            if client:
                client_key = client.client_key
                device_type = client.device_type

    # 日志状态：成功/登出/注册 → '0'，登录失败 → '1'
    login_status: str | None = None
    if status in (Constants.LOGIN_SUCCESS, Constants.LOGOUT, Constants.REGISTER):
        login_status = Constants.SUCCESS
    elif status == Constants.LOGIN_FAIL:
        login_status = Constants.FAIL

    fields: dict = {
        "user_name": username,
        "client_key": client_key,
        "device_type": device_type,
        "ipaddr": ip,
        "login_location": address,
        "browser": browser,
        "os": os_name,
        "msg": message,
        "login_time": datetime.now(),
    }
    if login_status is not None:
        fields["status"] = login_status
    instance = LogininforModel(**fields)

    async with async_db_session() as session, session.begin():
        await LogininforCrud(LogininforModel, AuthSchema(), session).create(instance)
