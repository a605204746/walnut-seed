"""通知公告管理（URL 前缀 /system/notice）。"""

from typing import Annotated

from fastapi import APIRouter, Depends
from redis.asyncio.client import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.module_system.notice.schema import NoticeCreateSchema, NoticeQueryParam, NoticeUpdateSchema
from app.api.v1.module_system.notice.service import NoticeService
from app.common.enums import BusinessType, HttpStatus
from app.common.response import EnvelopeResponse, ErrorResponse, SuccessResponse
from app.core.base_schema import AuthSchema
from app.core.dependencies import AuthPermission, db_getter, redis_getter
from app.core.exceptions import ServiceException
from app.core.idempotent import RepeatSubmit
from app.core.router_class import OperationLogRoute, log
from app.core.sse import sse_manager
from app.utils.string_util import str2list

NoticeRouter = APIRouter(route_class=OperationLogRoute, prefix="/notice", tags=["通知公告"])

DbSession = Annotated[AsyncSession, Depends(db_getter)]


def _parse_ids(ids: str) -> list[int]:
    """解析路径中的ID串。"""
    try:
        id_list = [int(item) for item in str2list(ids)]
    except ValueError:
        raise ServiceException("公告ID格式有误", code=HttpStatus.BAD_REQUEST)
    if not id_list:
        raise ServiceException("公告ID不能为空", code=HttpStatus.BAD_REQUEST)
    return id_list


@NoticeRouter.get("/list", summary="获取通知公告列表")
async def list_notice(
    params: Annotated[NoticeQueryParam, Depends()],
    db: DbSession,
    auth: Annotated[AuthSchema, Depends(AuthPermission(permissions=["system:notice:list"]))],
) -> SuccessResponse:
    return SuccessResponse(data=await NoticeService(auth, db).page_list(params))


@NoticeRouter.get("/{notice_id}", summary="根据通知公告编号获取详细信息")
async def get_notice(
    notice_id: int,
    db: DbSession,
    auth: Annotated[AuthSchema, Depends(AuthPermission(permissions=["system:notice:query"]))],
) -> SuccessResponse:
    return SuccessResponse(data=await NoticeService(auth, db).get_by_id(notice_id))


@NoticeRouter.post("", summary="新增通知公告", dependencies=[Depends(RepeatSubmit())])
@log(title="通知公告", business_type=BusinessType.INSERT)
async def add_notice(
    req: NoticeCreateSchema,
    db: DbSession,
    redis: Annotated[Redis, Depends(redis_getter)],
    auth: Annotated[AuthSchema, Depends(AuthPermission(permissions=["system:notice:add"]))],
) -> EnvelopeResponse:
    service = NoticeService(auth, db)
    if not await service.insert_notice(req):
        return ErrorResponse()
    # 全站 SSE 广播（消息内容为 "[类型标签] 公告标题"）
    label = await service.get_notice_type_label(req.notice_type)
    await sse_manager.publish_all(redis, f"[{label}] {req.notice_title}")
    return SuccessResponse()


@NoticeRouter.put("", summary="修改通知公告", dependencies=[Depends(RepeatSubmit())])
@log(title="通知公告", business_type=BusinessType.UPDATE)
async def update_notice(
    req: NoticeUpdateSchema,
    db: DbSession,
    auth: Annotated[AuthSchema, Depends(AuthPermission(permissions=["system:notice:edit"]))],
) -> EnvelopeResponse:
    return SuccessResponse() if await NoticeService(auth, db).update_notice(req) else ErrorResponse()


@NoticeRouter.delete("/{notice_ids}", summary="删除通知公告")
@log(title="通知公告", business_type=BusinessType.DELETE)
async def delete_notice(
    notice_ids: str,
    db: DbSession,
    auth: Annotated[AuthSchema, Depends(AuthPermission(permissions=["system:notice:remove"]))],
) -> EnvelopeResponse:
    return SuccessResponse() if await NoticeService(auth, db).delete_notice_by_ids(_parse_ids(notice_ids)) > 0 else ErrorResponse()
