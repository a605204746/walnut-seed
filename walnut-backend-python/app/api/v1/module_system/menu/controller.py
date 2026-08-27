"""菜单管理端点。

挂载于 /system 之下（最终路径 /system/menu/...）。
依赖注入统一使用 ``Annotated`` 风格（ruff FAST002）。
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Path
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.module_system.menu.model import MenuModel
from app.api.v1.module_system.menu.schema import (
    MenuCreateSchema,
    MenuOutSchema,
    MenuQuerySchema,
    MenuTreeSelectVoSchema,
    MenuUpdateSchema,
)
from app.api.v1.module_system.menu.service import MenuService
from app.common.constant import SystemConstants
from app.common.enums import BusinessType
from app.common.response import EnvelopeResponse, ErrorResponse, SuccessResponse, WarnResponse
from app.core.base_schema import AuthSchema
from app.core.dependencies import AuthPermission, db_getter, get_current_user
from app.core.idempotent import RepeatSubmit
from app.core.router_class import OperationLogRoute, log
from app.utils.string_util import is_http

MenuRouter = APIRouter(route_class=OperationLogRoute, prefix="/menu", tags=["菜单管理"])

SUPER_ADMIN = SystemConstants.SUPER_ADMIN_ROLE_KEY

# ---------------- 依赖注入（Annotated 风格） ----------------
DbSession = Annotated[AsyncSession, Depends(db_getter)]
AuthUser = Annotated[AuthSchema, Depends(get_current_user)]
MenuListAuth = Annotated[AuthSchema, Depends(AuthPermission(permissions=["system:menu:list"], roles=[SUPER_ADMIN], role_mode="OR"))]
MenuQueryAuth = Annotated[AuthSchema, Depends(AuthPermission(permissions=["system:menu:query"]))]
MenuQuerySuperAuth = Annotated[AuthSchema, Depends(AuthPermission(permissions=["system:menu:query"], roles=[SUPER_ADMIN], role_mode="OR"))]
MenuAddAuth = Annotated[AuthSchema, Depends(AuthPermission(permissions=["system:menu:add"], roles=[SUPER_ADMIN]))]
MenuEditAuth = Annotated[AuthSchema, Depends(AuthPermission(permissions=["system:menu:edit"], roles=[SUPER_ADMIN]))]
MenuRemoveAuth = Annotated[AuthSchema, Depends(AuthPermission(permissions=["system:menu:remove"], roles=[SUPER_ADMIN]))]
MenuQueryParams = Annotated[MenuQuerySchema, Depends()]
MenuIdPath = Annotated[int, Path(description="菜单ID")]
RoleIdPath = Annotated[int, Path(description="角色ID")]
MenuIdsPath = Annotated[str, Path(description="菜单ID串（逗号分隔）")]


def _menu_to_dict(menu: MenuModel | None) -> dict | None:
    if menu is None:
        return None
    return MenuOutSchema.model_validate(menu).model_dump(by_alias=True, mode="json")


@MenuRouter.get("/getRouters", summary="获取路由信息")
async def get_routers(auth: AuthUser, db: DbSession) -> SuccessResponse:
    service = MenuService(auth, db)
    menus = await service.select_menu_tree_by_user_id()
    return SuccessResponse(data=service.build_menus(menus))


@MenuRouter.get("/list", summary="获取菜单列表")
async def list_menu(query: MenuQueryParams, auth: MenuListAuth, db: DbSession) -> SuccessResponse:
    service = MenuService(auth, db)
    menus = await service.select_menu_list(query)
    return SuccessResponse(data=[_menu_to_dict(menu) for menu in menus])


@MenuRouter.get("/treeselect", summary="获取菜单下拉树列表")
async def tree_select(query: MenuQueryParams, auth: MenuQueryAuth, db: DbSession) -> SuccessResponse:
    service = MenuService(auth, db)
    menus = await service.select_menu_list(query)
    return SuccessResponse(data=service.build_menu_tree_select(menus))


@MenuRouter.get("/roleMenuTreeselect/{role_id}", summary="加载指定角色菜单列表树")
async def role_menu_tree_select(role_id: RoleIdPath, auth: MenuQueryAuth, db: DbSession) -> SuccessResponse:
    service = MenuService(auth, db)
    menus = await service.select_menu_list(MenuQuerySchema())
    data = MenuTreeSelectVoSchema(
        checked_keys=await service.select_menu_list_by_role_id(role_id),
        menus=service.build_menu_tree_select(menus),
    ).model_dump(by_alias=True)
    return SuccessResponse(data=data)


@MenuRouter.get("/{menu_id}", summary="根据菜单编号获取详细信息")
async def get_menu(menu_id: MenuIdPath, auth: MenuQuerySuperAuth, db: DbSession) -> SuccessResponse:
    service = MenuService(auth, db)
    return SuccessResponse(data=_menu_to_dict(await service.select_menu_by_id(menu_id)))


@MenuRouter.post("", summary="新增菜单", dependencies=[Depends(RepeatSubmit())])
@log(title="菜单管理", business_type=BusinessType.INSERT)
async def add_menu(req: MenuCreateSchema, auth: MenuAddAuth, db: DbSession) -> EnvelopeResponse:
    service = MenuService(auth, db)
    if not await service.check_menu_name_unique(req):
        return ErrorResponse(msg=f"新增菜单'{req.menu_name}'失败，菜单名称已存在")
    if req.is_frame == SystemConstants.YES_FRAME and not is_http(req.path):
        return ErrorResponse(msg=f"新增菜单'{req.menu_name}'失败，地址必须以http(s)://开头")
    if not await service.check_route_config_unique(req):
        return ErrorResponse(msg=f"新增菜单'{req.menu_name}'失败，路由名称或地址已存在")
    return SuccessResponse() if await service.insert_menu(req) > 0 else ErrorResponse()


@MenuRouter.put("", summary="修改菜单", dependencies=[Depends(RepeatSubmit())])
@log(title="菜单管理", business_type=BusinessType.UPDATE)
async def update_menu(req: MenuUpdateSchema, auth: MenuEditAuth, db: DbSession) -> EnvelopeResponse:
    service = MenuService(auth, db)
    if not await service.check_menu_name_unique(req):
        return ErrorResponse(msg=f"修改菜单'{req.menu_name}'失败，菜单名称已存在")
    if req.is_frame == SystemConstants.YES_FRAME and not is_http(req.path):
        return ErrorResponse(msg=f"修改菜单'{req.menu_name}'失败，地址必须以http(s)://开头")
    if req.id == req.parent_id:
        return ErrorResponse(msg=f"修改菜单'{req.menu_name}'失败，上级菜单不能选择自己")
    if not await service.check_route_config_unique(req):
        return ErrorResponse(msg=f"修改菜单'{req.menu_name}'失败，路由名称或地址已存在")
    return SuccessResponse() if await service.update_menu(req) > 0 else ErrorResponse()


@MenuRouter.delete("/cascade/{menu_ids}", summary="批量级联删除菜单")
@log(title="菜单管理", business_type=BusinessType.DELETE)
async def delete_menu_cascade(menu_ids: MenuIdsPath, auth: MenuRemoveAuth, db: DbSession) -> EnvelopeResponse:
    service = MenuService(auth, db)
    id_list = [int(item) for item in menu_ids.split(",") if item.strip()]
    if await service.has_child_by_menu_ids(id_list):
        return WarnResponse(msg="存在子菜单,不允许删除")
    await service.delete_menu_by_ids(id_list)
    return SuccessResponse()


@MenuRouter.delete("/{menu_id}", summary="删除菜单")
@log(title="菜单管理", business_type=BusinessType.DELETE)
async def delete_menu(menu_id: MenuIdPath, auth: MenuRemoveAuth, db: DbSession) -> EnvelopeResponse:
    service = MenuService(auth, db)
    if await service.has_child_by_menu_id(menu_id):
        return WarnResponse(msg="存在子菜单,不允许删除")
    if await service.check_menu_exist_role(menu_id):
        return WarnResponse(msg="菜单已分配,不允许删除")
    return SuccessResponse() if await service.delete_menu_by_id(menu_id) > 0 else ErrorResponse()
