"""字典域入参/出参模型。

- 入参校验为非空、长度上限、格式校验，错误消息为中文；
- 前端契约为驼峰，统一通过 alias + ``model_dump(by_alias=True, mode="json")`` 输出。
"""

import re
from typing import overload

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.common.constant import RegexConstants
from app.core.base_schema import PageQueryParam
from app.core.validator import DateStr, DateTimeStr


# ---------------- 公共校验工具 ----------------
def _not_blank(value: str | None, message: str) -> str:
    """非空校验（None 或纯空白视为非法）。"""
    if value is None or len(value.strip()) == 0:
        raise ValueError(message)
    return value


@overload
def _max_len(value: str, max_length: int, message: str) -> str: ...
@overload
def _max_len(value: str | None, max_length: int, message: str) -> str | None: ...
def _max_len(value: str | None, max_length: int, message: str) -> str | None:
    """长度上限校验（None 跳过）。"""
    if value is not None and len(value) > max_length:
        raise ValueError(message)
    return value


# ==================== 字典类型 ====================
class DictTypeCreateSchema(BaseModel):
    """新增字典类型入参。"""

    model_config = ConfigDict(populate_by_name=True)

    dict_name: str | None = Field(default=None, alias="dictName", description="字典名称")
    dict_type: str | None = Field(default=None, alias="dictType", description="字典类型")
    remark: str | None = Field(default=None, description="备注")

    @field_validator("dict_name")
    @classmethod
    def validate_dict_name(cls, value: str | None) -> str:
        value = _not_blank(value, "字典名称不能为空")
        return _max_len(value, 100, "字典类型名称长度不能超过100个字符")

    @field_validator("dict_type")
    @classmethod
    def validate_dict_type(cls, value: str | None) -> str:
        value = _not_blank(value, "字典类型不能为空")
        value = _max_len(value, 100, "字典类型类型长度不能超过100个字符")
        if not re.match(RegexConstants.DICTIONARY_TYPE, value):
            raise ValueError("字典类型必须以字母开头，且只能为（小写字母，数字，下滑线）")
        return value


class DictTypeUpdateSchema(DictTypeCreateSchema):
    """修改字典类型入参。"""

    id: int = Field(..., description="字典主键")


class DictTypeQueryParam(PageQueryParam):
    """字典类型列表查询参数（GET）。"""

    dict_name: str | None = Field(default=None, alias="dictName", description="字典名称")
    dict_type: str | None = Field(default=None, alias="dictType", description="字典类型")
    begin_time: DateStr | None = Field(default=None, alias="beginTime", description="开始时间")
    end_time: DateStr | None = Field(default=None, alias="endTime", description="结束时间")


class DictTypeOutSchema(BaseModel):
    """字典类型出参（驼峰输出）。"""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int | None = Field(default=None, description="字典主键")
    dict_name: str | None = Field(default=None, alias="dictName", description="字典名称")
    dict_type: str | None = Field(default=None, alias="dictType", description="字典类型")
    remark: str | None = Field(default=None, description="备注")
    create_time: DateTimeStr | None = Field(default=None, alias="createTime", description="创建时间")


# ==================== 字典数据 ====================
class DictDataCreateSchema(BaseModel):
    """新增字典数据入参。"""

    model_config = ConfigDict(populate_by_name=True)

    dict_sort: int | None = Field(default=None, alias="dictSort", description="字典排序")
    dict_label: str | None = Field(default=None, alias="dictLabel", description="字典标签")
    dict_value: str | None = Field(default=None, alias="dictValue", description="字典键值")
    dict_type: str | None = Field(default=None, alias="dictType", description="字典类型")
    css_class: str | None = Field(default=None, alias="cssClass", description="样式属性（其他样式扩展）")
    list_class: str | None = Field(default=None, alias="listClass", description="表格回显样式")
    is_default: str | None = Field(default=None, alias="isDefault", description="是否默认（Y是 N否）")
    remark: str | None = Field(default=None, description="备注")

    @field_validator("dict_label")
    @classmethod
    def validate_dict_label(cls, value: str | None) -> str:
        value = _not_blank(value, "字典标签不能为空")
        return _max_len(value, 100, "字典标签长度不能超过100个字符")

    @field_validator("dict_value")
    @classmethod
    def validate_dict_value(cls, value: str | None) -> str:
        value = _not_blank(value, "字典键值不能为空")
        return _max_len(value, 100, "字典键值长度不能超过100个字符")

    @field_validator("dict_type")
    @classmethod
    def validate_dict_type(cls, value: str | None) -> str:
        value = _not_blank(value, "字典类型不能为空")
        return _max_len(value, 100, "字典类型长度不能超过100个字符")

    @field_validator("css_class")
    @classmethod
    def validate_css_class(cls, value: str | None) -> str | None:
        return _max_len(value, 100, "样式属性长度不能超过100个字符")


class DictDataUpdateSchema(DictDataCreateSchema):
    """修改字典数据入参。"""

    id: int = Field(..., description="字典编码")


class DictDataQueryParam(PageQueryParam):
    """字典数据列表查询参数（GET）。"""

    dict_sort: int | None = Field(default=None, alias="dictSort", description="字典排序")
    dict_label: str | None = Field(default=None, alias="dictLabel", description="字典标签")
    dict_type: str | None = Field(default=None, alias="dictType", description="字典类型")


class DictDataOutSchema(BaseModel):
    """字典数据出参（驼峰输出）。"""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int | None = Field(default=None, description="字典编码")
    dict_sort: int | None = Field(default=None, alias="dictSort", description="字典排序")
    dict_label: str | None = Field(default=None, alias="dictLabel", description="字典标签")
    dict_value: str | None = Field(default=None, alias="dictValue", description="字典键值")
    dict_type: str | None = Field(default=None, alias="dictType", description="字典类型")
    css_class: str | None = Field(default=None, alias="cssClass", description="样式属性（其他样式扩展）")
    list_class: str | None = Field(default=None, alias="listClass", description="表格回显样式")
    is_default: str | None = Field(default=None, alias="isDefault", description="是否默认（Y是 N否）")
    remark: str | None = Field(default=None, description="备注")
    create_time: DateTimeStr | None = Field(default=None, alias="createTime", description="创建时间")
