"""部门管理端点。

- /list、/list/exclude/{deptId}、/{deptId}、POST、PUT、DELETE /{deptId}、/optionselect；
- /treeselect 为部门下拉树（树构建逻辑在本模块）；
- 角色部门树（checkedKeys + depts）由 role 模块的 /system/role/deptTree/{roleId} 提供，
  本模块 service 暴露 select_dept_tree_list / select_dept_list_by_role_id 供其调用。
Router prefix="/dept"，由主路由挂载到 /system。
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.module_system.dept.schema import DeptCreateSchema, DeptQueryParam, DeptUpdateSchema, dump_camel
from app.api.v1.module_system.dept.service import DeptService
from app.common.constant import SystemConstants
from app.common.enums import BusinessType, HttpStatus
from app.common.response import ErrorResponse, SuccessResponse, WarnResponse
from app.core.base_schema import AuthSchema
from app.core.dependencies import AuthPermission, db_getter, get_current_user
from app.core.exceptions import ServiceException
from app.core.idempotent import RepeatSubmit
from app.core.router_class import OperationLogRoute, log
from app.utils.string_util import str2list

DeptRouter = APIRouter(route_class=OperationLogRoute, prefix="/dept", tags=["部门管理"])

DbSession = Annotated[AsyncSession, Depends(db_getter)]
AuthDep = Annotated[AuthSchema, Depends(get_current_user)]
ListParamDep = Annotated[DeptQueryParam, Depends()]


@DeptRouter.get("/list", summary="获取部门列表", dependencies=[Depends(AuthPermission(permissions=["system:dept:list"]))])
async def list_dept(param: ListParamDep, auth: AuthDep, db: DbSession) -> SuccessResponse:
    """获取部门列表（不分页，支持 deptName/status 等过滤）。"""
    depts = await DeptService(auth, db).list_dept_out(param)
    return SuccessResponse(data=[dump_camel(dept) for dept in depts])


@DeptRouter.get("/list/exclude/{dept_id}", summary="查询部门列表（排除节点）", dependencies=[Depends(AuthPermission(permissions=["system:dept:list"]))])
async def exclude_child(dept_id: int, auth: AuthDep, db: DbSession) -> SuccessResponse:
    """查询部门列表（排除指定节点及其子孙）。"""
    depts = await DeptService(auth, db).list_dept_out_exclude(dept_id)
    return SuccessResponse(data=[dump_camel(dept) for dept in depts])


@DeptRouter.get("/treeselect", summary="获取部门下拉树列表", dependencies=[Depends(AuthPermission(permissions=["system:dept:query"]))])
async def treeselect(param: ListParamDep, auth: AuthDep, db: DbSession) -> SuccessResponse:
    """获取部门下拉树列表（节点结构 id/parentId/label/weight/disabled/children）。"""
    tree = await DeptService(auth, db).select_dept_tree_list(param)
    return SuccessResponse(data=tree)


@DeptRouter.get("/optionselect", summary="获取部门选择框列表", dependencies=[Depends(AuthPermission(permissions=["system:dept:query"]))])
async def optionselect(auth: AuthDep, db: DbSession, dept_ids: Annotated[str | None, Query(alias="deptIds")] = None) -> SuccessResponse:
    """获取部门选择框列表（deptIds 参数支持逗号分隔）。"""
    ids: list[int] | None = None
    if dept_ids:
        try:
            ids = [int(item) for item in str2list(dept_ids)]
        except ValueError:
            raise ServiceException("部门ID参数格式不正确", code=HttpStatus.BAD_REQUEST)
    depts = await DeptService(auth, db).select_dept_by_ids(ids)
    return SuccessResponse(data=[dump_camel(dept) for dept in depts])


@DeptRouter.get("/{dept_id}", summary="根据部门编号获取详细信息", dependencies=[Depends(AuthPermission(permissions=["system:dept:query"]))])
async def get_dept(dept_id: int, auth: AuthDep, db: DbSession) -> SuccessResponse:
    """根据部门编号获取详细信息。"""
    service = DeptService(auth, db)
    await service.check_dept_data_scope(dept_id)
    dept = await service.select_dept_by_id(dept_id)
    return SuccessResponse(data=dump_camel(dept) if dept is not None else None)


@DeptRouter.post("", summary="新增部门", dependencies=[Depends(AuthPermission(permissions=["system:dept:add"])), Depends(RepeatSubmit())])
@log(title="部门管理", business_type=BusinessType.INSERT)
async def add_dept(req: DeptCreateSchema, auth: AuthDep, db: DbSession) -> JSONResponse:
    """新增部门。"""
    service = DeptService(auth, db)
    if not await service.check_dept_name_unique(req):
        return ErrorResponse(msg=f"新增部门'{req.dept_name}'失败，部门名称已存在")
    return SuccessResponse() if await service.insert_dept(req) > 0 else ErrorResponse()


@DeptRouter.put("", summary="修改部门", dependencies=[Depends(AuthPermission(permissions=["system:dept:edit"])), Depends(RepeatSubmit())])
@log(title="部门管理", business_type=BusinessType.UPDATE)
async def update_dept(req: DeptUpdateSchema, auth: AuthDep, db: DbSession) -> JSONResponse:
    """修改部门。"""
    service = DeptService(auth, db)
    dept_id = req.id
    await service.check_dept_data_scope(dept_id)
    if not await service.check_dept_name_unique(req):
        return ErrorResponse(msg=f"修改部门'{req.dept_name}'失败，部门名称已存在")
    if req.parent_id == dept_id:
        return ErrorResponse(msg=f"修改部门'{req.dept_name}'失败，上级部门不能是自己")
    if req.status == SystemConstants.DISABLE:
        if await service.select_normal_children_dept_by_id(dept_id) > 0:
            return ErrorResponse(msg="该部门包含未停用的子部门!")
        if await service.check_dept_exist_user(dept_id):
            return ErrorResponse(msg="该部门下存在已分配用户，不能禁用!")
    return SuccessResponse() if await service.update_dept(req) > 0 else ErrorResponse()


@DeptRouter.delete("/{dept_id}", summary="删除部门", dependencies=[Depends(AuthPermission(permissions=["system:dept:remove"]))])
@log(title="部门管理", business_type=BusinessType.DELETE)
async def delete_dept(dept_id: int, auth: AuthDep, db: DbSession) -> JSONResponse:
    """删除部门。"""
    service = DeptService(auth, db)
    if SystemConstants.DEFAULT_DEPT_ID == dept_id:
        return WarnResponse(msg="默认部门,不允许删除")
    if await service.has_child_by_dept_id(dept_id):
        return WarnResponse(msg="存在下级部门,不允许删除")
    if await service.check_dept_exist_user(dept_id):
        return WarnResponse(msg="部门存在用户,不允许删除")
    if await service.count_post_by_dept_id(dept_id) > 0:
        return WarnResponse(msg="部门存在岗位,不允许删除")
    await service.check_dept_data_scope(dept_id)
    return SuccessResponse() if await service.delete_dept_by_id(dept_id) > 0 else ErrorResponse()
