"""菜单域 Schema。

前端契约字段名为驼峰（menuName/parentId/orderNum/queryParam/isFrame/isCache/menuType/createTime 等），
通过 ``alias`` 对齐；序列化时统一 ``model_dump(by_alias=True)`` 输出驼峰键名。
"""

from __future__ import annotations

import json
import re

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.common.constant import RegexConstants
from app.core.validator import DateTimeStr


# ---------------- 公共校验工具 ----------------
def _not_blank(value: str | None, message: str) -> str:
    """非空字符串校验。"""
    if value is None or len(value.strip()) == 0:
        raise ValueError(message)
    return value


def _max_len(value: str | None, max_length: int, message: str) -> str | None:
    """长度上限校验。"""
    if value is not None and len(value) > max_length:
        raise ValueError(message)
    return value


class MenuQuerySchema(BaseModel):
    """菜单列表/下拉树查询参数（GET，不分页）。"""

    model_config = ConfigDict(populate_by_name=True)

    menu_name: str | None = Field(default=None, alias="menuName", description="菜单名称")
    visible: str | None = Field(default=None, description="显示状态（0显示 1隐藏）")
    status: str | None = Field(default=None, description="菜单状态（0正常 1停用）")
    menu_type: str | None = Field(default=None, alias="menuType", description="菜单类型（M目录 C菜单 F按钮）")
    parent_id: int | None = Field(default=None, alias="parentId", description="父菜单ID")


class MenuCreateSchema(BaseModel):
    """新增菜单入参。

    ``validate_default=True``：未提供的字段也会对默认值执行校验，
    确保必填字段缺省时同样报错。
    """

    model_config = ConfigDict(populate_by_name=True, validate_default=True)

    id: int | None = Field(default=None, description="菜单ID")
    parent_id: int | None = Field(default=None, alias="parentId", description="父菜单ID")
    menu_name: str | None = Field(default=None, alias="menuName", description="菜单名称")
    order_num: int | None = Field(default=None, alias="orderNum", description="显示顺序")
    path: str | None = Field(default=None, description="路由地址")
    component: str | None = Field(default=None, description="组件路径")
    query_param: str | None = Field(default=None, alias="queryParam", description="路由参数")
    is_frame: str | None = Field(default=None, alias="isFrame", description="是否为外链（0是 1否）")
    is_cache: str | None = Field(default=None, alias="isCache", description="是否缓存（0缓存 1不缓存）")
    menu_type: str | None = Field(default=None, alias="menuType", description="菜单类型（M目录 C菜单 F按钮）")
    visible: str | None = Field(default=None, description="显示状态（0显示 1隐藏）")
    status: str | None = Field(default=None, description="菜单状态（0正常 1停用）")
    perms: str | None = Field(default=None, description="权限标识")
    icon: str | None = Field(default=None, description="菜单图标")
    remark: str | None = Field(default=None, description="备注")

    @field_validator("menu_name")
    @classmethod
    def validate_menu_name(cls, value: str | None) -> str:
        value = _not_blank(value, "菜单名称不能为空")
        _max_len(value, 50, "菜单名称长度不能超过50个字符")
        return value

    @field_validator("order_num")
    @classmethod
    def validate_order_num(cls, value: int | None) -> int:
        if value is None:
            raise ValueError("显示顺序不能为空")
        return value

    @field_validator("path")
    @classmethod
    def validate_path(cls, value: str | None) -> str | None:
        return _max_len(value, 200, "路由地址不能超过200个字符")

    @field_validator("component")
    @classmethod
    def validate_component(cls, value: str | None) -> str | None:
        return _max_len(value, 200, "组件路径不能超过200个字符")

    @field_validator("query_param")
    @classmethod
    def validate_query_param(cls, value: str | None) -> str | None:
        # 必须符合 JSON 对象格式
        if value is None or len(value.strip()) == 0:
            return value
        try:
            parsed = json.loads(value)
        except (TypeError, json.JSONDecodeError):
            raise ValueError("路由参数必须符合JSON格式")
        if not isinstance(parsed, dict):
            raise ValueError("路由参数必须符合JSON格式")
        return value

    @field_validator("menu_type")
    @classmethod
    def validate_menu_type(cls, value: str | None) -> str:
        return _not_blank(value, "菜单类型不能为空")

    @field_validator("perms")
    @classmethod
    def validate_perms(cls, value: str | None) -> str | None:
        value = _max_len(value, 100, "权限标识长度不能超过100个字符")
        if value is not None and not re.match(RegexConstants.PERMISSION_STRING, value):
            raise ValueError("权限标识必须符合 tool:build:list 格式")
        return value


class MenuUpdateSchema(MenuCreateSchema):
    """修改菜单入参。"""

    id: int = Field(..., description="菜单ID")


class MenuOutSchema(BaseModel):
    """菜单出参（驼峰输出）。"""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int | None = Field(default=None, description="菜单ID")
    menu_name: str | None = Field(default=None, alias="menuName", description="菜单名称")
    parent_id: int | None = Field(default=None, alias="parentId", description="父菜单ID")
    order_num: int | None = Field(default=None, alias="orderNum", description="显示顺序")
    path: str | None = Field(default=None, description="路由地址")
    component: str | None = Field(default=None, description="组件路径")
    query_param: str | None = Field(default=None, alias="queryParam", description="路由参数")
    is_frame: str | None = Field(default=None, alias="isFrame", description="是否为外链（0是 1否）")
    is_cache: str | None = Field(default=None, alias="isCache", description="是否缓存（0缓存 1不缓存）")
    menu_type: str | None = Field(default=None, alias="menuType", description="菜单类型（M目录 C菜单 F按钮）")
    visible: str | None = Field(default=None, description="显示状态（0显示 1隐藏）")
    status: str | None = Field(default=None, description="菜单状态（0正常 1停用）")
    perms: str | None = Field(default=None, description="权限标识")
    icon: str | None = Field(default=None, description="菜单图标")
    create_dept: int | None = Field(default=None, alias="createDept", description="创建部门")
    remark: str | None = Field(default=None, description="备注")
    create_time: DateTimeStr | None = Field(default=None, alias="createTime", description="创建时间")
    children: list[MenuOutSchema] = Field(default_factory=list, description="子菜单")


class MetaResp(BaseModel):
    """路由显示信息（字段大小写与前端契约一致）。"""

    model_config = ConfigDict(populate_by_name=True)

    title: str | None = Field(default=None, description="路由展示名字")
    icon: str | None = Field(default=None, description="路由图标")
    no_cache: bool | None = Field(default=None, alias="noCache", description="是否不被 keep-alive 缓存")
    link: str | None = Field(default=None, description="内链地址（http(s)://开头）")
    active_menu: str | None = Field(default=None, alias="activeMenu", description="激活菜单")


class RouterResp(BaseModel):
    """路由配置信息（空值字段过滤由 service 层序列化实现）。"""

    model_config = ConfigDict(populate_by_name=True)

    name: str | None = Field(default=None, description="路由名字")
    path: str | None = Field(default=None, description="路由地址")
    hidden: bool | None = Field(default=None, description="是否隐藏路由")
    redirect: str | None = Field(default=None, description="重定向地址")
    component: str | None = Field(default=None, description="组件地址")
    query: str | None = Field(default=None, description="路由参数")
    always_show: bool | None = Field(default=None, alias="alwaysShow", description="是否总是显示多级目录")
    meta: MetaResp | None = Field(default=None, description="路由元信息")
    children: list[RouterResp] | None = Field(default=None, description="子路由")


class MenuTreeSelectVoSchema(BaseModel):
    """角色菜单树选中结果。"""

    model_config = ConfigDict(populate_by_name=True)

    checked_keys: list[int] = Field(default_factory=list, alias="checkedKeys", description="选中菜单ID列表")
    menus: list[dict] = Field(default_factory=list, description="菜单下拉树结构列表")
