"""客户端管理（URL 前缀 /system/client）。"""

from typing import Annotated

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.module_system.client.schema import ClientCreateSchema, ClientQueryParam, ClientStatusSchema, ClientUpdateSchema
from app.api.v1.module_system.client.service import ClientService
from app.common.enums import BusinessType, HttpStatus
from app.common.response import EnvelopeResponse, ErrorResponse, SuccessResponse
from app.core.base_schema import AuthSchema
from app.core.dependencies import AuthPermission, db_getter
from app.core.exceptions import ServiceException
from app.core.idempotent import RepeatSubmit
from app.core.router_class import OperationLogRoute, log
from app.utils.excel_util import ExcelUtil
from app.utils.string_util import str2list

ClientRouter = APIRouter(route_class=OperationLogRoute, prefix="/client", tags=["客户端管理"])

DbSession = Annotated[AsyncSession, Depends(db_getter)]

# 导出表头
_EXPORT_HEADERS = {
    "id": "id",
    "clientId": "客户端id",
    "clientKey": "客户端key",
    "clientSecret": "客户端秘钥",
    "grantTypeList": "授权类型",
    "activeTimeout": "token活跃超时时间",
    "timeout": "token固定超时时间",
    "status": "状态",
}


def _parse_ids(ids: str) -> list[int]:
    """解析路径中的ID串。"""
    try:
        id_list = [int(item) for item in str2list(ids)]
    except ValueError:
        raise ServiceException("主键格式有误", code=HttpStatus.BAD_REQUEST)
    if not id_list:
        raise ServiceException("主键不能为空", code=HttpStatus.BAD_REQUEST)
    return id_list


@ClientRouter.get("/list", summary="查询客户端管理列表")
async def list_client(
    params: Annotated[ClientQueryParam, Depends()],
    db: DbSession,
    auth: Annotated[AuthSchema, Depends(AuthPermission(permissions=["system:client:list"]))],
) -> SuccessResponse:
    return SuccessResponse(data=await ClientService(auth, db).query_page_list(params))


@ClientRouter.post("/export", summary="导出客户端管理列表")
@log(title="客户端管理", business_type=BusinessType.EXPORT)
async def export_client(
    request: Request,
    db: DbSession,
    auth: Annotated[AuthSchema, Depends(AuthPermission(permissions=["system:client:export"]))],
):
    form = await request.form()
    data = {key: value for key, value in form.items() if value not in (None, "")}
    data.pop("pageSize", None)  # 导出时不分页，查询全部
    params = ClientQueryParam.model_validate(data)
    rows = await ClientService(auth, db).query_list(params)
    for row in rows:  # 授权类型列表转逗号分隔字符串落 Excel
        if isinstance(row.get("grantTypeList"), list):
            row["grantTypeList"] = ",".join(row["grantTypeList"])
    return ExcelUtil.export_excel_response(rows, _EXPORT_HEADERS, "客户端管理")


@ClientRouter.get("/{client_id}", summary="获取客户端管理详细信息")
async def get_client(
    client_id: int,
    db: DbSession,
    auth: Annotated[AuthSchema, Depends(AuthPermission(permissions=["system:client:query"]))],
) -> SuccessResponse:
    return SuccessResponse(data=await ClientService(auth, db).query_by_id(client_id))


@ClientRouter.post("", summary="新增客户端管理", dependencies=[Depends(RepeatSubmit())])
@log(title="客户端管理", business_type=BusinessType.INSERT)
async def add_client(
    req: ClientCreateSchema,
    db: DbSession,
    auth: Annotated[AuthSchema, Depends(AuthPermission(permissions=["system:client:add"]))],
) -> EnvelopeResponse:
    service = ClientService(auth, db)
    if not await service.check_client_key_unique(req):
        raise ServiceException(f"新增客户端'{req.client_key}'失败，客户端key已存在")
    return SuccessResponse() if await service.insert_by_bo(req) else ErrorResponse()


@ClientRouter.put("", summary="修改客户端管理", dependencies=[Depends(RepeatSubmit())])
@log(title="客户端管理", business_type=BusinessType.UPDATE)
async def update_client(
    req: ClientUpdateSchema,
    db: DbSession,
    auth: Annotated[AuthSchema, Depends(AuthPermission(permissions=["system:client:edit"]))],
) -> EnvelopeResponse:
    service = ClientService(auth, db)
    if not await service.check_client_key_unique(req):
        raise ServiceException(f"修改客户端'{req.client_key}'失败，客户端key已存在")
    return SuccessResponse() if await service.update_by_bo(req) else ErrorResponse()


@ClientRouter.put("/changeStatus", summary="状态修改")
@log(title="客户端管理", business_type=BusinessType.UPDATE)
async def change_client_status(
    req: ClientStatusSchema,
    db: DbSession,
    auth: Annotated[AuthSchema, Depends(AuthPermission(permissions=["system:client:edit"]))],
) -> EnvelopeResponse:
    assert req.client_id is not None and req.status is not None  # schema 校验（validate_default）保证非空
    return SuccessResponse() if await ClientService(auth, db).update_client_status(req.client_id, req.status) > 0 else ErrorResponse()


@ClientRouter.delete("/{ids}", summary="删除客户端管理")
@log(title="客户端管理", business_type=BusinessType.DELETE)
async def delete_client(
    ids: str,
    db: DbSession,
    auth: Annotated[AuthSchema, Depends(AuthPermission(permissions=["system:client:remove"]))],
) -> EnvelopeResponse:
    return SuccessResponse() if await ClientService(auth, db).delete_with_valid_by_ids(_parse_ids(ids)) else ErrorResponse()
