"""部门域 Schema。

- 入参含非空/长度/邮箱等校验（中文消息）；
- 出参含 parentName/leaderName/children；
- 前端契约为驼峰，统一通过 alias + ``model_dump(by_alias=True, mode="json")`` 输出。
"""

from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.common.constant import RegexConstants
from app.core.validator import DateStr, DateTimeStr
from app.utils.string_util import is_blank


def dump_camel(instance: BaseModel) -> dict[str, Any]:
    """Pydantic 模型 → 驼峰键字典（前端契约为驼峰）。"""
    return instance.model_dump(by_alias=True, mode="json")


class DeptCreateSchema(BaseModel):
    """新增部门入参。"""

    model_config = ConfigDict(populate_by_name=True)

    parent_id: int = Field(..., alias="parentId", description="父部门ID")
    dept_name: str | None = Field(default=None, alias="deptName", validate_default=True, description="部门名称")
    dept_category: str | None = Field(default=None, alias="deptCategory", description="部门类别编码")
    order_num: int | None = Field(default=None, alias="orderNum", validate_default=True, description="显示顺序")
    leader: int | None = Field(default=None, description="负责人（用户ID）")
    phone: str | None = Field(default=None, description="联系电话")
    email: str | None = Field(default=None, description="邮箱")
    status: str | None = Field(default=None, description="部门状态（0正常 1停用）")

    @field_validator("dept_name")
    @classmethod
    def validate_dept_name(cls, value: str | None) -> str:
        if value is None or is_blank(value):
            raise ValueError("部门名称不能为空")
        if len(value) > 30:
            raise ValueError("部门名称长度不能超过30个字符")
        return value

    @field_validator("dept_category")
    @classmethod
    def validate_dept_category(cls, value: str | None) -> str | None:
        if value is not None and len(value) > 100:
            raise ValueError("部门类别编码长度不能超过100个字符")
        return value

    @field_validator("order_num")
    @classmethod
    def validate_order_num(cls, value: int | None) -> int:
        if value is None:
            raise ValueError("显示顺序不能为空")
        return value

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value: str | None) -> str | None:
        if value is not None and len(value) > 11:
            raise ValueError("联系电话长度不能超过11个字符")
        return value

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str | None) -> str | None:
        if value is None:
            return value
        if len(value) > 50:
            raise ValueError("邮箱长度不能超过50个字符")
        if not re.match(RegexConstants.EMAIL, value):
            raise ValueError("邮箱格式不正确")
        return value


class DeptUpdateSchema(DeptCreateSchema):
    """修改部门入参（修改时 id 必填）。"""

    id: int = Field(..., description="部门ID")


class DeptQueryParam(BaseModel):
    """部门列表查询参数（GET 查询）。"""

    model_config = ConfigDict(populate_by_name=True)

    id: int | None = Field(default=None, description="部门ID")
    parent_id: int | None = Field(default=None, alias="parentId", description="父部门ID")
    dept_name: str | None = Field(default=None, alias="deptName", description="部门名称")
    dept_category: str | None = Field(default=None, alias="deptCategory", description="部门类别编码")
    status: str | None = Field(default=None, description="部门状态（0正常 1停用）")
    belong_dept_id: int | None = Field(default=None, alias="belongDeptId", description="归属部门ID（部门树搜索）")
    begin_time: DateStr | None = Field(default=None, alias="beginTime", description="开始时间（yyyy-MM-dd）")
    end_time: DateStr | None = Field(default=None, alias="endTime", description="结束时间（yyyy-MM-dd）")


class DeptOutSchema(BaseModel):
    """部门出参（驼峰输出）。"""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int | None = Field(default=None, description="部门id")
    parent_id: int | None = Field(default=None, alias="parentId", description="父部门id")
    parent_name: str | None = Field(default=None, alias="parentName", description="父部门名称")
    ancestors: str | None = Field(default=None, description="祖级列表")
    dept_name: str | None = Field(default=None, alias="deptName", description="部门名称")
    dept_category: str | None = Field(default=None, alias="deptCategory", description="部门类别编码")
    order_num: int | None = Field(default=None, alias="orderNum", description="显示顺序")
    leader: int | None = Field(default=None, description="负责人ID")
    leader_name: str | None = Field(default=None, alias="leaderName", description="负责人")
    phone: str | None = Field(default=None, description="联系电话")
    email: str | None = Field(default=None, description="邮箱")
    status: str | None = Field(default=None, description="部门状态（0正常 1停用）")
    create_time: DateTimeStr | None = Field(default=None, alias="createTime", description="创建时间")
    children: list[DeptOutSchema] = Field(default_factory=list, description="子部门")
