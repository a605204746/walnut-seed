"""社交登录绑定控制器（前缀 /system/social）。

本模块仅暴露 /list 端点（查询当前用户绑定的社交账号列表），
其余服务方法（insert/update/delete/selectByAuthId）供认证模块社交登录使用。
"""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.module_system.social.service import SocialService
from app.common.response import SuccessResponse
from app.core.base_schema import AuthSchema
from app.core.dependencies import AuthPermission, db_getter, get_current_user
from app.core.router_class import OperationLogRoute

SocialRouter = APIRouter(route_class=OperationLogRoute, prefix="/system/social", tags=["社会化关系"])


@SocialRouter.get("/list", summary="社会化关系列表", dependencies=[Depends(AuthPermission())])
async def list_social(
    auth: Annotated[AuthSchema, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(db_getter)],
) -> SuccessResponse:
    """查询当前用户的社会化关系列表（需登录，无权限码要求）。"""
    service = SocialService(auth, db)
    rows = await service.query_list_by_user_id(auth.user.id)
    return SuccessResponse(data=[row.model_dump(by_alias=True, mode="json") for row in rows])
