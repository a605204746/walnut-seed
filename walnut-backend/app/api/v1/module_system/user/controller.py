"""用户管理与个人中心端点。

- UserRouter prefix="/user"：list、export、importData、importTemplate、getInfo、GET / 与 /{userId}、
  POST、PUT、DELETE /{userIds}、optionselect、resetPwd、changeStatus、authRole/{userId}、PUT authRole、
  deptTree、list/dept/{deptId}；
- ProfileRouter prefix="/user/profile"：GET、PUT、PUT /updatePwd、POST /avatar（multipart）。
两个 Router 由主线挂载到 /system 前缀下。GET /{userId} 使用 ``{user_id:int}`` 路径转换器，
避免吞掉 /user/profile 等同前缀路由。
"""

from __future__ import annotations

import os
from typing import Annotated, Any, cast
from urllib.parse import quote

import bcrypt
from fastapi import APIRouter, Depends, Query, Request, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.module_system.dept.schema import DeptQueryParam
from app.api.v1.module_system.user.schema import (
    UserChangeStatusSchema,
    UserCreateSchema,
    UserPasswordUpdateSchema,
    UserProfileUpdateSchema,
    UserQueryParam,
    UserResetPwdSchema,
    UserUpdateSchema,
)
from app.api.v1.module_system.user.service import UserService
from app.common.enums import BusinessType, HttpStatus
from app.common.response import EnvelopeResponse, ErrorResponse, StreamResponse, SuccessResponse
from app.core.base_schema import AuthSchema
from app.core.dependencies import AuthPermission, db_getter, get_current_user
from app.core.exceptions import ServiceException
from app.core.file_storage import get_file_storage
from app.core.idempotent import RepeatSubmit
from app.core.router_class import OperationLogRoute, log
from app.utils.date_util import date_time_now
from app.utils.excel_util import ExcelUtil
from app.utils.string_util import str2list

UserRouter = APIRouter(route_class=OperationLogRoute, prefix="/user", tags=["用户管理"])
ProfileRouter = APIRouter(route_class=OperationLogRoute, prefix="/user/profile", tags=["个人信息"])

DbSession = Annotated[AsyncSession, Depends(db_getter)]
AuthDep = Annotated[AuthSchema, Depends(get_current_user)]

# 头像允许的图片扩展名
_IMAGE_EXTENSIONS = ["bmp", "gif", "jpg", "jpeg", "png"]

# 导出表头
_EXPORT_HEADERS = {
    "id": "用户序号",
    "user_name": "用户账号",
    "nick_name": "用户昵称",
    "email": "用户邮箱",
    "phonenumber": "手机号码",
    "sex": "用户性别",
    "status": "账号状态",
    "login_ip": "最后登录IP",
    "login_date": "最后登录时间",
    "dept_name": "部门名称",
    "leader_name": "部门负责人",
}

# 导入模板表头（顺序即列序）
_IMPORT_HEADERS = ["用户序号", "部门编号", "用户账号", "用户昵称", "用户邮箱", "手机号码", "用户性别", "账号状态"]


def _parse_id_list(raw: str, label: str) -> list[int]:
    """解析路径/查询中逗号分隔的ID串。"""
    try:
        return [int(item) for item in str2list(raw)]
    except ValueError:
        raise ServiceException(f"{label}格式有误", code=HttpStatus.BAD_REQUEST)


def _hash_password(raw: str) -> str:
    """BCrypt 哈希密码。"""
    return bcrypt.hashpw(raw.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


# ==================== 用户管理 ====================
@UserRouter.get("/list", summary="获取用户列表", dependencies=[Depends(AuthPermission(permissions=["system:user:list"]))])
async def list_user(param: Annotated[UserQueryParam, Depends()], auth: AuthDep, db: DbSession) -> SuccessResponse:
    """获取用户分页列表（带数据权限，回填 deptName）。"""
    return SuccessResponse(data=await UserService(auth, db).select_page_user_list(param))


@UserRouter.get(
    "/list/dept/{dept_id}", summary="获取部门下的所有用户信息", dependencies=[Depends(AuthPermission(permissions=["system:user:list"]))]
)
async def list_by_dept(dept_id: int, auth: AuthDep, db: DbSession) -> SuccessResponse:
    """获取部门下的所有用户信息。"""
    return SuccessResponse(data=await UserService(auth, db).select_user_list_by_dept(dept_id))


@UserRouter.post("/export", summary="导出用户列表", dependencies=[Depends(AuthPermission(permissions=["system:user:export"]))])
@log(title="用户管理", business_type=BusinessType.EXPORT)
async def export_user(request: Request, auth: AuthDep, db: DbSession):
    """导出用户列表（导出全部不分页）。"""
    form = await request.form()
    data: dict[str, Any] = dict(request.query_params)
    data.update({k: v for k, v in form.items() if v not in (None, "")})
    data.pop("pageSize", None)
    data.pop("pageNum", None)
    param = UserQueryParam.model_validate(data)
    rows = await UserService(auth, db).select_user_export_list(param)
    return ExcelUtil.export_excel_response(rows, _EXPORT_HEADERS, "用户数据")


@UserRouter.post("/importData", summary="导入用户数据", dependencies=[Depends(AuthPermission(permissions=["system:user:import"]))])
@log(title="用户管理", business_type=BusinessType.IMPORT)
async def import_data(request: Request, auth: AuthDep, db: DbSession) -> SuccessResponse:
    """导入用户数据（multipart file + updateSupport 参数）。"""
    form = await request.form()
    file = form.get("file")
    if file is None or not hasattr(file, "read"):
        raise ServiceException("导入文件不能为空", code=HttpStatus.BAD_REQUEST)
    raw_support = form.get("updateSupport", request.query_params.get("updateSupport", "false"))
    update_support = str(raw_support).strip().lower() in ("true", "1", "yes", "on")
    contents = await file.read()
    rows = ExcelUtil.read_excel_to_dicts(contents)
    message = await UserService(auth, db).import_users(rows, update_support)
    return SuccessResponse(msg=message)


@UserRouter.post("/importTemplate", summary="获取用户导入模板")
async def import_template(auth: AuthDep, db: DbSession):
    """获取用户导入模板（带性别/状态下拉的模板，仅需登录）。"""
    from app.api.v1.module_system.dict.service import DictTypeService

    dict_service = DictTypeService(auth, db)
    sex_data = await dict_service.select_dict_data_by_type("sys_user_sex", None) or []
    status_data = await dict_service.select_dict_data_by_type("sys_normal_disable", None) or []
    sex_labels = [label for item in sex_data if (label := item.get("dictLabel"))]
    status_labels = [label for item in status_data if (label := item.get("dictLabel"))]

    option_list = [{"用户性别": sex_labels}, {"账号状态": status_labels}]
    selector_header_list = ["用户性别", "账号状态"]
    data = ExcelUtil.get_excel_template(_IMPORT_HEADERS, selector_header_list, option_list)

    filename = f"用户数据_{date_time_now()}.xlsx"
    encoded = quote(filename)
    headers = {
        "Content-Disposition": f"attachment;filename*=utf-8''{encoded}",
        "download-filename": encoded,
        "Access-Control-Expose-Headers": "Content-Disposition,download-filename",
    }
    return StreamResponse(data=iter([data]), media_type=ExcelUtil.EXCEL_CONTENT_TYPE, headers=headers)


@UserRouter.get("/getInfo", summary="获取用户信息")
async def get_info(auth: AuthDep, db: DbSession) -> EnvelopeResponse:
    """获取当前登录用户信息（需登录不查权限，忽略数据权限）。"""
    data = await UserService(auth, db).get_info()
    if data is None:
        return ErrorResponse(msg="没有权限访问用户数据!")
    return SuccessResponse(data=data)


@UserRouter.get("/optionselect", summary="批量获取用户基础信息", dependencies=[Depends(AuthPermission(permissions=["system:user:query"]))])
async def optionselect(
    auth: AuthDep,
    db: DbSession,
    user_ids: Annotated[str | None, Query(alias="userIds", description="用户ID串")] = None,
    dept_id: Annotated[int | None, Query(alias="deptId", description="部门ID")] = None,
) -> SuccessResponse:
    """根据用户ID串批量获取用户基础信息。"""
    ids = _parse_id_list(user_ids, "用户ID") if user_ids else None
    return SuccessResponse(data=await UserService(auth, db).select_user_by_ids(ids, dept_id))


@UserRouter.get("/deptTree", summary="获取部门树列表", dependencies=[Depends(AuthPermission(permissions=["system:user:list"]))])
async def dept_tree(param: Annotated[DeptQueryParam, Depends()], auth: AuthDep, db: DbSession) -> SuccessResponse:
    """获取部门树列表（复用 DeptService.select_dept_tree_list）。"""
    from app.api.v1.module_system.dept.service import DeptService

    return SuccessResponse(data=await DeptService(auth, db).select_dept_tree_list(param))


@UserRouter.get(
    "/authRole/{user_id:int}", summary="根据用户编号获取授权角色", dependencies=[Depends(AuthPermission(permissions=["system:user:query"]))]
)
async def auth_role(user_id: int, auth: AuthDep, db: DbSession) -> SuccessResponse:
    """根据用户编号获取授权角色（返回 user + roles，roles 带 flag）。"""
    return SuccessResponse(data=await UserService(auth, db).get_auth_role(user_id))


@UserRouter.put(
    "/resetPwd",
    summary="重置密码",
    dependencies=[Depends(AuthPermission(permissions=["system:user:resetPwd"])), Depends(RepeatSubmit())],
)
@log(title="用户管理", business_type=BusinessType.UPDATE)
async def reset_pwd(req: UserResetPwdSchema, auth: AuthDep, db: DbSession) -> EnvelopeResponse:
    """重置用户密码。"""
    if req.id is None:
        raise ServiceException("用户ID不能为空")
    if req.password is None:
        raise ServiceException("用户密码不能为空")
    service = UserService(auth, db)
    await service.check_user_allowed(req.id)
    await service.check_user_data_scope(req.id)
    return SuccessResponse() if await service.reset_user_pwd(req.id, _hash_password(req.password)) > 0 else ErrorResponse()


@UserRouter.put(
    "/changeStatus",
    summary="状态修改",
    dependencies=[Depends(AuthPermission(permissions=["system:user:edit"])), Depends(RepeatSubmit())],
)
@log(title="用户管理", business_type=BusinessType.UPDATE)
async def change_status(req: UserChangeStatusSchema, auth: AuthDep, db: DbSession) -> EnvelopeResponse:
    """用户状态修改。"""
    if req.id is None:
        raise ServiceException("用户ID不能为空")
    service = UserService(auth, db)
    await service.check_user_allowed(req.id)
    await service.check_user_data_scope(req.id)
    return SuccessResponse() if await service.update_user_status(req.id, req.status) > 0 else ErrorResponse()


@UserRouter.put(
    "/authRole",
    summary="用户授权角色",
    dependencies=[Depends(AuthPermission(permissions=["system:user:edit"])), Depends(RepeatSubmit())],
)
@log(title="用户管理", business_type=BusinessType.GRANT)
async def insert_auth_role(
    auth: AuthDep,
    db: DbSession,
    user_id: Annotated[int | None, Query(alias="userId", description="用户ID")] = None,
    role_ids: Annotated[str | None, Query(alias="roleIds", description="角色ID串")] = None,
) -> SuccessResponse:
    """用户授权角色（userId + roleIds 走 query 参数）。"""
    ids = _parse_id_list(role_ids, "角色ID") if role_ids else []
    await UserService(auth, db).insert_user_auth(user_id, ids)
    return SuccessResponse()


@UserRouter.post(
    "",
    summary="新增用户",
    dependencies=[Depends(AuthPermission(permissions=["system:user:add"])), Depends(RepeatSubmit())],
)
@log(title="用户管理", business_type=BusinessType.INSERT)
async def add_user(req: UserCreateSchema, auth: AuthDep, db: DbSession) -> EnvelopeResponse:
    """新增用户。"""
    if req.user_name is None:
        raise ServiceException("用户账号不能为空")
    if req.password is None:
        raise ServiceException("用户密码不能为空")
    service = UserService(auth, db)
    await service.check_dept_data_scope(req.dept_id)
    if not await service.check_user_name_unique(req.user_name):
        return ErrorResponse(msg=f"新增用户'{req.user_name}'失败，登录账号已存在")
    if req.phonenumber and not await service.check_phone_unique(req.phonenumber):
        return ErrorResponse(msg=f"新增用户'{req.user_name}'失败，手机号码已存在")
    if req.email and not await service.check_email_unique(req.email):
        return ErrorResponse(msg=f"新增用户'{req.user_name}'失败，邮箱账号已存在")
    req.password = _hash_password(req.password)
    return SuccessResponse() if await service.insert_user(req) > 0 else ErrorResponse()


@UserRouter.put(
    "",
    summary="修改用户",
    dependencies=[Depends(AuthPermission(permissions=["system:user:edit"])), Depends(RepeatSubmit())],
)
@log(title="用户管理", business_type=BusinessType.UPDATE)
async def update_user(req: UserUpdateSchema, auth: AuthDep, db: DbSession) -> EnvelopeResponse:
    """修改用户。"""
    if req.user_name is None:
        raise ServiceException("用户账号不能为空")
    service = UserService(auth, db)
    await service.check_user_allowed(req.id)
    await service.check_user_data_scope(req.id)
    await service.check_dept_data_scope(req.dept_id)
    if not await service.check_user_name_unique(req.user_name, req.id):
        return ErrorResponse(msg=f"修改用户'{req.user_name}'失败，登录账号已存在")
    if req.phonenumber and not await service.check_phone_unique(req.phonenumber, req.id):
        return ErrorResponse(msg=f"修改用户'{req.user_name}'失败，手机号码已存在")
    if req.email and not await service.check_email_unique(req.email, req.id):
        return ErrorResponse(msg=f"修改用户'{req.user_name}'失败，邮箱账号已存在")
    return SuccessResponse() if await service.update_user(req) > 0 else ErrorResponse()


@UserRouter.delete("/{user_ids}", summary="删除用户", dependencies=[Depends(AuthPermission(permissions=["system:user:remove"]))])
@log(title="用户管理", business_type=BusinessType.DELETE)
async def delete_user(user_ids: str, auth: AuthDep, db: DbSession) -> EnvelopeResponse:
    """删除用户（不能删除自己，逻辑删除并清理关联）。"""
    id_list = _parse_id_list(user_ids, "用户ID")
    if auth.user.id in id_list:
        return ErrorResponse(msg="当前用户不能删除")
    return SuccessResponse() if await UserService(auth, db).delete_user_by_ids(id_list) > 0 else ErrorResponse()


@UserRouter.get("/", summary="获取用户信息", dependencies=[Depends(AuthPermission(permissions=["system:user:query"]))])
async def get_user_root(auth: AuthDep, db: DbSession) -> SuccessResponse:
    """获取用户信息（无 userId：仅返回角色选项）。"""
    return SuccessResponse(data=await UserService(auth, db).get_user_info(None))


@UserRouter.get(
    "/{user_id:int}", summary="根据用户编号获取详细信息", dependencies=[Depends(AuthPermission(permissions=["system:user:query"]))]
)
async def get_user(user_id: int, auth: AuthDep, db: DbSession) -> SuccessResponse:
    """根据用户编号获取详细信息。"""
    return SuccessResponse(data=await UserService(auth, db).get_user_info(user_id))


# ==================== 个人中心 ====================
@ProfileRouter.get("", summary="个人信息")
async def profile(auth: AuthDep, db: DbSession) -> SuccessResponse:
    """个人信息（返回 user + roleGroup + postGroup）。"""
    return SuccessResponse(data=await UserService(auth, db).get_profile())


@ProfileRouter.put("", summary="修改用户信息", dependencies=[Depends(RepeatSubmit())])
@log(title="个人信息", business_type=BusinessType.UPDATE)
async def update_profile(req: UserProfileUpdateSchema, auth: AuthDep, db: DbSession) -> EnvelopeResponse:
    """修改个人基本资料（user_name 不可改，校验手机/邮箱唯一）。"""
    service = UserService(auth, db)
    user_id = auth.user.id
    username = auth.user.username
    if req.phonenumber and not await service.check_phone_unique(req.phonenumber, user_id):
        return ErrorResponse(msg=f"修改用户'{username}'失败，手机号码已存在")
    if req.email and not await service.check_email_unique(req.email, user_id):
        return ErrorResponse(msg=f"修改用户'{username}'失败，邮箱账号已存在")
    rows = await service.update_user_profile(req, user_id)
    if rows > 0:
        return SuccessResponse()
    return ErrorResponse(msg="修改个人信息异常，请联系管理员")


@ProfileRouter.put("/updatePwd", summary="重置密码", dependencies=[Depends(RepeatSubmit())])
@log(title="个人信息", business_type=BusinessType.UPDATE)
async def update_pwd(req: UserPasswordUpdateSchema, auth: AuthDep, db: DbSession) -> EnvelopeResponse:
    """修改个人密码（校验旧密码、新旧密码不同）。"""
    rows = await UserService(auth, db).update_pwd(req, auth.user.id)
    if rows > 0:
        return SuccessResponse()
    return ErrorResponse(msg="修改密码异常，请联系管理员")


@ProfileRouter.post("/avatar", summary="头像上传", dependencies=[Depends(RepeatSubmit())])
@log(title="用户头像", business_type=BusinessType.UPDATE)
async def avatar(request: Request, auth: AuthDep, db: DbSession) -> EnvelopeResponse:
    """头像上传（multipart avatarfile，校验图片格式并更新 sys_user.avatar）。"""
    form = await request.form()
    file = form.get("avatarfile")
    if file is not None and hasattr(file, "read"):
        file = cast("UploadFile", file)
        extension = os.path.splitext(file.filename or "")[1].lstrip(".").lower()
        if extension not in _IMAGE_EXTENSIONS:
            return ErrorResponse(msg="文件格式不正确，请上传[" + ", ".join(_IMAGE_EXTENSIONS) + "]格式")
        result = await get_file_storage().upload(file)
        if result.url is not None and await UserService(auth, db).update_user_avatar(auth.user.id, result.url):
            return SuccessResponse(data={"imgUrl": result.url})
    return ErrorResponse(msg="上传图片异常，请联系管理员")
