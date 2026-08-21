"""角色域 Schema。

契约说明：
- ``status`` / ``del_flag`` 保持 CHAR(1) 字符串契约；
- ``menuCheckStrictly`` / ``deptCheckStrictly`` 入参/出参均为布尔，
  实体列为整型 1/0，落库时转为 1/0；
- 出参 ``superAdmin`` 为 id == 1 的派生标识；
- 前端契约为驼峰，出参统一通过 alias + ``model_dump(by_alias=True, mode="json")`` 输出。
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.common.constant import SystemConstants
from app.core.base_schema import PageQueryParam
from app.core.validator import DateStr, DateTimeStr


def dump_camel(instance: BaseModel) -> dict[str, Any]:
    """Pydantic 模型 → 驼峰键字典（前端契约为驼峰）。"""
    return instance.model_dump(by_alias=True, mode="json")


# ==================== 查询参数 ====================
class RoleQueryParam(PageQueryParam):
    """角色列表/导出查询参数（GET）。"""

    role_name: str | None = Field(default=None, alias="roleName", description="角色名称")
    role_key: str | None = Field(default=None, alias="roleKey", description="角色权限字符串")
    status: str | None = Field(default=None, description="角色状态（0正常 1停用）")
    begin_time: DateStr | None = Field(default=None, alias="beginTime", description="开始时间")
    end_time: DateStr | None = Field(default=None, alias="endTime", description="结束时间")


class AuthUserQueryParam(PageQueryParam):
    """已分配/未分配用户查询参数（GET /role/authUser/*）。"""

    role_id: int | None = Field(default=None, alias="roleId", description="角色ID")
    user_name: str | None = Field(default=None, alias="userName", description="用户账号")
    phonenumber: str | None = Field(default=None, description="手机号码")
    status: str | None = Field(default=None, description="帐号状态（0正常 1停用）")


# ==================== 入参 ====================
class RoleCreateSchema(BaseModel):
    """新增角色入参。"""

    model_config = ConfigDict(populate_by_name=True)

    role_name: str | None = Field(default=None, alias="roleName", description="角色名称")
    role_key: str | None = Field(default=None, alias="roleKey", description="角色权限字符串")
    role_sort: int | None = Field(default=None, alias="roleSort", description="显示顺序")
    data_scope: str | None = Field(default=None, alias="dataScope", description="数据范围（1-6）")
    menu_check_strictly: bool | None = Field(default=None, alias="menuCheckStrictly", description="菜单树选择项是否关联显示")
    dept_check_strictly: bool | None = Field(default=None, alias="deptCheckStrictly", description="部门树选择项是否关联显示")
    status: str | None = Field(default=None, description="角色状态（0正常 1停用）")
    remark: str | None = Field(default=None, description="备注")
    menu_ids: list[int] | None = Field(default=None, alias="menuIds", description="菜单组")
    dept_ids: list[int] | None = Field(default=None, alias="deptIds", description="部门组（数据权限）")

    @field_validator("role_name")
    @classmethod
    def check_role_name(cls, value: str | None) -> str:
        if value is None or not value.strip():
            raise ValueError("角色名称不能为空")
        if len(value) > 30:
            raise ValueError("角色名称长度不能超过30个字符")
        return value

    @field_validator("role_key")
    @classmethod
    def check_role_key(cls, value: str | None) -> str:
        if value is None or not value.strip():
            raise ValueError("角色权限字符串不能为空")
        if len(value) > 100:
            raise ValueError("权限字符长度不能超过100个字符")
        return value

    @field_validator("role_sort")
    @classmethod
    def check_role_sort(cls, value: int | None) -> int:
        if value is None:
            raise ValueError("显示顺序不能为空")
        return value


class RoleUpdateSchema(RoleCreateSchema):
    """修改角色入参（新增 id 必填）。"""

    id: int | None = Field(default=None, description="角色ID")

    @field_validator("id")
    @classmethod
    def check_id(cls, value: int | None) -> int:
        if value is None:
            raise ValueError("角色ID不能为空")
        return value


class RoleStatusSchema(BaseModel):
    """角色状态修改入参（PUT /role/changeStatus）。"""

    model_config = ConfigDict(populate_by_name=True)

    id: int | None = Field(default=None, description="角色ID")
    status: str | None = Field(default=None, description="角色状态（0正常 1停用）")

    @field_validator("id")
    @classmethod
    def check_id(cls, value: int | None) -> int:
        if value is None:
            raise ValueError("角色ID不能为空")
        return value


class RoleDataScopeSchema(BaseModel):
    """数据权限修改入参（PUT /role/dataScope）。"""

    model_config = ConfigDict(populate_by_name=True)

    id: int | None = Field(default=None, description="角色ID")
    data_scope: str | None = Field(default=None, alias="dataScope", description="数据范围（1-6）")
    dept_check_strictly: bool | None = Field(default=None, alias="deptCheckStrictly", description="部门树选择项是否关联显示")
    dept_ids: list[int] | None = Field(default=None, alias="deptIds", description="部门组（数据权限）")

    @field_validator("id")
    @classmethod
    def check_id(cls, value: int | None) -> int:
        if value is None:
            raise ValueError("角色ID不能为空")
        return value


class AuthUserCancelSchema(BaseModel):
    """取消授权用户入参（PUT /role/authUser/cancel）。"""

    model_config = ConfigDict(populate_by_name=True)

    role_id: int | None = Field(default=None, alias="roleId", description="角色ID")
    user_id: int | None = Field(default=None, alias="userId", description="用户ID")

    @field_validator("role_id")
    @classmethod
    def check_role_id(cls, value: int | None) -> int:
        if value is None:
            raise ValueError("角色ID不能为空")
        return value

    @field_validator("user_id")
    @classmethod
    def check_user_id(cls, value: int | None) -> int:
        if value is None:
            raise ValueError("用户ID不能为空")
        return value


# ==================== 出参 ====================
def _int_to_bool(value):
    """实体列 1/0 转布尔。"""
    if value is None:
        return None
    return bool(value)


class RoleOutSchema(BaseModel):
    """角色出参（驼峰输出）。"""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int | None = Field(default=None, description="角色ID")
    role_name: str | None = Field(default=None, alias="roleName", description="角色名称")
    role_key: str | None = Field(default=None, alias="roleKey", description="角色权限字符串")
    role_sort: int | None = Field(default=None, alias="roleSort", description="显示顺序")
    data_scope: str | None = Field(default=None, alias="dataScope", description="数据范围（1-6）")
    menu_check_strictly: bool | None = Field(default=None, alias="menuCheckStrictly", description="菜单树选择项是否关联显示")
    dept_check_strictly: bool | None = Field(default=None, alias="deptCheckStrictly", description="部门树选择项是否关联显示")
    status: str | None = Field(default=None, description="角色状态（0正常 1停用）")
    remark: str | None = Field(default=None, description="备注")
    create_time: DateTimeStr | None = Field(default=None, alias="createTime", description="创建时间")
    flag: bool = Field(default=False, description="用户是否存在此角色标识（默认不存在）")
    super_admin: bool = Field(default=False, alias="superAdmin", description="是否超级管理员角色")

    @field_validator("menu_check_strictly", "dept_check_strictly", mode="before")
    @classmethod
    def check_strictly(cls, value):
        return _int_to_bool(value)

    @model_validator(mode="after")
    def compute_super_admin(self):
        # superAdmin 由 id 派生（序列化为 superAdmin 字段）
        self.super_admin = self.id == SystemConstants.SUPER_ADMIN_ID
        return self


class AuthUserOutSchema(BaseModel):
    """已分配/未分配用户出参（驼峰输出）。"""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int | None = Field(default=None, description="用户ID")
    dept_id: int | None = Field(default=None, alias="deptId", description="部门ID")
    user_name: str | None = Field(default=None, alias="userName", description="用户账号")
    nick_name: str | None = Field(default=None, alias="nickName", description="用户昵称")
    email: str | None = Field(default=None, description="用户邮箱")
    phonenumber: str | None = Field(default=None, description="手机号码")
    status: str | None = Field(default=None, description="帐号状态（0正常 1停用）")
    create_time: DateTimeStr | None = Field(default=None, alias="createTime", description="创建时间")
    dept_name: str | None = Field(default=None, alias="deptName", description="部门名")
