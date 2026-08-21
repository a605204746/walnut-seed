"""参数设置入参/出参模型。

- 入参校验为非空与长度上限校验，错误消息为中文；
- 前端契约为驼峰，统一通过 alias + ``model_dump(by_alias=True, mode="json")`` 输出。
"""

from typing import overload

from pydantic import BaseModel, ConfigDict, Field, field_validator

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


class ConfigCreateSchema(BaseModel):
    """新增参数配置入参。"""

    model_config = ConfigDict(populate_by_name=True)

    config_name: str | None = Field(default=None, alias="configName", description="参数名称")
    config_key: str | None = Field(default=None, alias="configKey", description="参数键名")
    config_value: str | None = Field(default=None, alias="configValue", description="参数键值")
    config_type: str | None = Field(default=None, alias="configType", description="系统内置（Y是 N否）")
    remark: str | None = Field(default=None, description="备注")

    @field_validator("config_name")
    @classmethod
    def validate_config_name(cls, value: str | None) -> str:
        value = _not_blank(value, "参数名称不能为空")
        return _max_len(value, 100, "参数名称不能超过100个字符")

    @field_validator("config_key")
    @classmethod
    def validate_config_key(cls, value: str | None) -> str:
        value = _not_blank(value, "参数键名不能为空")
        return _max_len(value, 100, "参数键名长度不能超过100个字符")

    @field_validator("config_value")
    @classmethod
    def validate_config_value(cls, value: str | None) -> str:
        value = _not_blank(value, "参数键值不能为空")
        return _max_len(value, 500, "参数键值长度不能超过500个字符")


class ConfigUpdateSchema(ConfigCreateSchema):
    """修改参数配置入参（按主键修改）。"""

    id: int = Field(..., description="参数主键")


class ConfigUpdateByKeySchema(BaseModel):
    """按参数键名修改入参。

    此处最低限度要求 ``config_key``/``config_value``：无键名则无法定位记录，
    其余字段可选，仅更新提供的字段（非空更新语义）。
    """

    model_config = ConfigDict(populate_by_name=True)

    id: int | None = Field(default=None, description="参数主键")
    config_name: str | None = Field(default=None, alias="configName", description="参数名称")
    config_key: str | None = Field(default=None, alias="configKey", description="参数键名")
    config_value: str | None = Field(default=None, alias="configValue", description="参数键值")
    config_type: str | None = Field(default=None, alias="configType", description="系统内置（Y是 N否）")
    remark: str | None = Field(default=None, description="备注")

    @field_validator("config_key")
    @classmethod
    def validate_config_key(cls, value: str | None) -> str:
        return _not_blank(value, "参数键名不能为空")

    @field_validator("config_value")
    @classmethod
    def validate_config_value(cls, value: str | None) -> str:
        return _not_blank(value, "参数键值不能为空")


class ConfigQueryParam(PageQueryParam):
    """参数配置列表查询参数（GET）。"""

    config_name: str | None = Field(default=None, alias="configName", description="参数名称")
    config_key: str | None = Field(default=None, alias="configKey", description="参数键名")
    config_type: str | None = Field(default=None, alias="configType", description="系统内置（Y是 N否）")
    begin_time: DateStr | None = Field(default=None, alias="beginTime", description="开始时间")
    end_time: DateStr | None = Field(default=None, alias="endTime", description="结束时间")


class ConfigOutSchema(BaseModel):
    """参数配置出参（驼峰输出）。"""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int | None = Field(default=None, description="参数主键")
    config_name: str | None = Field(default=None, alias="configName", description="参数名称")
    config_key: str | None = Field(default=None, alias="configKey", description="参数键名")
    config_value: str | None = Field(default=None, alias="configValue", description="参数键值")
    config_type: str | None = Field(default=None, alias="configType", description="系统内置（Y是 N否）")
    remark: str | None = Field(default=None, description="备注")
    create_time: DateTimeStr | None = Field(default=None, alias="createTime", description="创建时间")
