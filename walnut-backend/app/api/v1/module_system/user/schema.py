"""用户域 Schema。

契约说明：
- ``status`` / ``del_flag`` / ``sex`` 保持 CHAR(1) 字符串契约；
- 出参一律驼峰：字段通过 alias 对齐前端契约，序列化用 ``dump_camel``
  （``model_dump(by_alias=True, mode="json")``）；
- 出参模型中不包含 password 字段；
- 入参校验为非空/长度/邮箱格式等中文消息校验（未含 XSS 脚本校验）。
"""

from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.api.v1.module_system.role.schema import RoleOutSchema
from app.common.constant import RegexConstants
from app.core.base_schema import PageQueryParam
from app.core.validator import DateStr, DateTimeStr
from app.utils.string_util import is_blank


def dump_camel(instance: BaseModel) -> dict[str, Any]:
    """Pydantic 模型 → 驼峰键字典（前端契约为驼峰）。"""
    return instance.model_dump(by_alias=True, mode="json")


def _check_password_complexity(value: str | None, field_label: str = "用户密码") -> str:
    """密码复杂度校验：非空 + 大小写字母/数字/特殊字符（RegexConstants.PASSWORD）。"""
    if value is None or is_blank(value):
        raise ValueError(f"{field_label}不能为空")
    if not re.match(RegexConstants.PASSWORD, value):
        raise ValueError("密码必须包含大写字母、小写字母、数字和特殊字符")
    return value


# ==================== 查询参数 ====================
class UserQueryParam(PageQueryParam):
    """用户列表/导出查询参数（GET 查询）。"""

    id: int | None = Field(default=None, description="用户ID")
    dept_id: int | None = Field(default=None, alias="deptId", description="部门ID（部门树搜索，含子孙）")
    user_name: str | None = Field(default=None, alias="userName", description="用户账号")
    nick_name: str | None = Field(default=None, alias="nickName", description="用户昵称")
    status: str | None = Field(default=None, description="帐号状态（0正常 1停用）")
    phonenumber: str | None = Field(default=None, description="手机号码")
    user_ids: str | None = Field(default=None, alias="userIds", description="用户ID串（逗号分隔）")
    exclude_user_ids: str | None = Field(default=None, alias="excludeUserIds", description="排除不查询的用户ID串（工作流用）")
    begin_time: DateStr | None = Field(default=None, alias="beginTime", description="开始时间（yyyy-MM-dd）")
    end_time: DateStr | None = Field(default=None, alias="endTime", description="结束时间（yyyy-MM-dd）")


# ==================== 入参（新增/修改） ====================
class UserBaseSchema(BaseModel):
    """用户新增/修改公共入参（password 不在此强制）。"""

    model_config = ConfigDict(populate_by_name=True)

    dept_id: int | None = Field(default=None, alias="deptId", description="部门ID")
    user_name: str | None = Field(default=None, alias="userName", validate_default=True, description="用户账号")
    nick_name: str | None = Field(default=None, alias="nickName", validate_default=True, description="用户昵称")
    user_type: str | None = Field(default=None, alias="userType", description="用户类型（sys_user系统用户）")
    email: str | None = Field(default=None, description="用户邮箱")
    phonenumber: str | None = Field(default=None, description="手机号码")
    sex: str | None = Field(default=None, description="用户性别（0男 1女 2未知）")
    password: str | None = Field(default=None, description="密码")
    status: str | None = Field(default=None, description="帐号状态（0正常 1停用）")
    remark: str | None = Field(default=None, description="备注")
    role_ids: list[int] | None = Field(default=None, alias="roleIds", description="角色组")
    post_ids: list[int] | None = Field(default=None, alias="postIds", description="岗位组")

    @field_validator("user_name")
    @classmethod
    def check_user_name(cls, value: str | None) -> str:
        if value is None or is_blank(value):
            raise ValueError("用户账号不能为空")
        if len(value) < 2 or len(value) > 30:
            raise ValueError("用户账号长度必须在2到30个字符之间")
        return value

    @field_validator("nick_name")
    @classmethod
    def check_nick_name(cls, value: str | None) -> str:
        if value is None or is_blank(value):
            raise ValueError("用户昵称不能为空")
        if len(value) > 30:
            raise ValueError("用户昵称长度不能超过30个字符")
        return value

    @field_validator("email")
    @classmethod
    def check_email(cls, value: str | None) -> str | None:
        # null/空串不校验格式，仅在有值时校验
        if value is None or value == "":
            return value
        if len(value) > 50:
            raise ValueError("邮箱长度不能超过50个字符")
        if not re.match(RegexConstants.EMAIL, value):
            raise ValueError("邮箱格式不正确")
        return value

    @field_validator("role_ids")
    @classmethod
    def check_role_ids(cls, value: list[int] | None) -> list[int] | None:
        # null 放行，空数组报错
        if value is not None and len(value) == 0:
            raise ValueError("用户角色不能为空")
        return value


class UserCreateSchema(UserBaseSchema):
    """新增用户入参（密码必填，用于哈希）。"""

    @field_validator("password")
    @classmethod
    def check_password(cls, value: str | None) -> str:
        return _check_password_complexity(value)


class UserUpdateSchema(UserBaseSchema):
    """修改用户入参（id 必填，不强制密码）。"""

    id: int | None = Field(default=None, validate_default=True, description="用户ID")

    @field_validator("id")
    @classmethod
    def check_id(cls, value: int | None) -> int:
        if value is None:
            raise ValueError("用户ID不能为空")
        return value


# ==================== 入参（重置密码 / 状态修改） ====================
class UserResetPwdSchema(BaseModel):
    """重置密码入参（PUT /user/resetPwd）。"""

    model_config = ConfigDict(populate_by_name=True)

    id: int | None = Field(default=None, validate_default=True, description="用户ID")
    password: str | None = Field(default=None, validate_default=True, description="新密码")

    @field_validator("id")
    @classmethod
    def check_id(cls, value: int | None) -> int:
        if value is None:
            raise ValueError("用户ID不能为空")
        return value

    @field_validator("password")
    @classmethod
    def check_password(cls, value: str | None) -> str:
        return _check_password_complexity(value)


class UserChangeStatusSchema(BaseModel):
    """状态修改入参（PUT /user/changeStatus）。"""

    model_config = ConfigDict(populate_by_name=True)

    id: int | None = Field(default=None, validate_default=True, description="用户ID")
    status: str | None = Field(default=None, description="帐号状态（0正常 1停用）")

    @field_validator("id")
    @classmethod
    def check_id(cls, value: int | None) -> int:
        if value is None:
            raise ValueError("用户ID不能为空")
        return value


# ==================== 入参（个人中心） ====================
class UserProfileUpdateSchema(BaseModel):
    """修改个人基本资料入参（PUT /user/profile）。"""

    model_config = ConfigDict(populate_by_name=True)

    nick_name: str | None = Field(default=None, alias="nickName", description="用户昵称")
    email: str | None = Field(default=None, description="用户邮箱")
    phonenumber: str | None = Field(default=None, description="手机号码")
    sex: str | None = Field(default=None, description="用户性别（0男 1女 2未知）")

    @field_validator("nick_name")
    @classmethod
    def check_nick_name(cls, value: str | None) -> str | None:
        if value is not None and len(value) > 30:
            raise ValueError("用户昵称长度不能超过30个字符")
        return value

    @field_validator("email")
    @classmethod
    def check_email(cls, value: str | None) -> str | None:
        if value is None or value == "":
            return value
        if len(value) > 50:
            raise ValueError("邮箱长度不能超过50个字符")
        if not re.match(RegexConstants.EMAIL, value):
            raise ValueError("邮箱格式不正确")
        return value

    @field_validator("phonenumber")
    @classmethod
    def check_phonenumber(cls, value: str | None) -> str | None:
        if value is None or value == "":
            return value
        if not re.match(RegexConstants.MOBILE, value):
            raise ValueError("手机号格式不正确")
        return value


class UserPasswordUpdateSchema(BaseModel):
    """修改个人密码入参（PUT /user/profile/updatePwd）。"""

    model_config = ConfigDict(populate_by_name=True)

    old_password: str | None = Field(default=None, alias="oldPassword", validate_default=True, description="旧密码")
    new_password: str | None = Field(default=None, alias="newPassword", validate_default=True, description="新密码")

    @field_validator("old_password")
    @classmethod
    def check_old_password(cls, value: str | None) -> str:
        if value is None or is_blank(value):
            raise ValueError("旧密码不能为空")
        return value

    @field_validator("new_password")
    @classmethod
    def check_new_password(cls, value: str | None) -> str:
        return _check_password_complexity(value, "新密码")


# ==================== 出参 ====================
class UserOutSchema(BaseModel):
    """用户出参（驼峰输出；不含 password）。"""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int | None = Field(default=None, description="用户ID")
    dept_id: int | None = Field(default=None, alias="deptId", description="部门ID")
    user_name: str | None = Field(default=None, alias="userName", description="用户账号")
    nick_name: str | None = Field(default=None, alias="nickName", description="用户昵称")
    user_type: str | None = Field(default=None, alias="userType", description="用户类型（sys_user系统用户）")
    email: str | None = Field(default=None, description="用户邮箱")
    phonenumber: str | None = Field(default=None, description="手机号码")
    sex: str | None = Field(default=None, description="用户性别（0男 1女 2未知）")
    avatar: str | None = Field(default=None, description="头像地址")
    status: str | None = Field(default=None, description="帐号状态（0正常 1停用）")
    login_ip: str | None = Field(default=None, alias="loginIp", description="最后登录IP")
    login_date: DateTimeStr | None = Field(default=None, alias="loginDate", description="最后登录时间")
    remark: str | None = Field(default=None, description="备注")
    create_time: DateTimeStr | None = Field(default=None, alias="createTime", description="创建时间")
    dept_name: str | None = Field(default=None, alias="deptName", description="部门名")
    roles: list[RoleOutSchema] | None = Field(default=None, description="角色对象")
    role_ids: list[int] | None = Field(default=None, alias="roleIds", description="角色组")
    post_ids: list[int] | None = Field(default=None, alias="postIds", description="岗位组")
    role_id: int | None = Field(default=None, alias="roleId", description="数据权限 当前角色ID")


class ProfileUserOutSchema(BaseModel):
    """个人中心用户出参（无密码/角色等敏感与冗余字段）。"""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int | None = Field(default=None, description="用户ID")
    tenant_id: str | None = Field(default=None, alias="tenantId", description="租户ID")
    dept_id: int | None = Field(default=None, alias="deptId", description="部门ID")
    user_name: str | None = Field(default=None, alias="userName", description="用户账号")
    nick_name: str | None = Field(default=None, alias="nickName", description="用户昵称")
    user_type: str | None = Field(default=None, alias="userType", description="用户类型（sys_user系统用户）")
    email: str | None = Field(default=None, description="用户邮箱")
    phonenumber: str | None = Field(default=None, description="手机号码")
    sex: str | None = Field(default=None, description="用户性别（0男 1女 2未知）")
    avatar: str | None = Field(default=None, description="头像地址")
    login_ip: str | None = Field(default=None, alias="loginIp", description="最后登录IP")
    login_date: DateTimeStr | None = Field(default=None, alias="loginDate", description="最后登录时间")
    dept_name: str | None = Field(default=None, alias="deptName", description="部门名")


class UserInfoOutSchema(BaseModel):
    """GET /user 与 /user/{userId} 出参。"""

    model_config = ConfigDict(populate_by_name=True)

    user: UserOutSchema | None = Field(default=None, description="用户信息")
    role_ids: list[int] | None = Field(default=None, alias="roleIds", description="角色ID列表")
    roles: list[RoleOutSchema] | None = Field(default=None, description="角色列表")
    post_ids: list[int] | None = Field(default=None, alias="postIds", description="岗位ID列表")
    posts: list[dict[str, Any]] | None = Field(default=None, description="岗位列表")


class GetInfoOutSchema(BaseModel):
    """GET /user/getInfo 出参。"""

    model_config = ConfigDict(populate_by_name=True)

    user: UserOutSchema | None = Field(default=None, description="用户基本信息")
    permissions: list[str] = Field(default_factory=list, description="菜单权限")
    roles: list[str] = Field(default_factory=list, description="角色权限")


class ProfileOutSchema(BaseModel):
    """GET /user/profile 出参。"""

    model_config = ConfigDict(populate_by_name=True)

    user: ProfileUserOutSchema | None = Field(default=None, description="用户信息")
    role_group: str | None = Field(default=None, alias="roleGroup", description="用户所属角色组")
    post_group: str | None = Field(default=None, alias="postGroup", description="用户所属岗位组")
