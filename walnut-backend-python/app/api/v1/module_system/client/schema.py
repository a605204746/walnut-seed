"""客户端管理的入参/出参模型。"""

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from pydantic.alias_generators import to_camel

from app.core.base_schema import PageQueryParam
from app.utils.string_util import str2list


class ClientQueryParam(PageQueryParam):
    """客户端列表查询参数（GET）。"""

    client_id: str | None = Field(default=None, alias="clientId", description="客户端id")
    client_key: str | None = Field(default=None, alias="clientKey", description="客户端key")
    client_secret: str | None = Field(default=None, alias="clientSecret", description="客户端秘钥")
    status: str | None = Field(default=None, description="状态（0正常 1停用）")


class ClientCreateSchema(BaseModel):
    """新增客户端入参。"""

    model_config = ConfigDict(populate_by_name=True)

    client_key: str | None = Field(default=None, validate_default=True, alias="clientKey", description="客户端key")
    client_secret: str | None = Field(default=None, validate_default=True, alias="clientSecret", description="客户端秘钥")
    grant_type_list: list[str] | None = Field(default=None, validate_default=True, alias="grantTypeList", description="授权类型列表")
    device_type: str | None = Field(default=None, alias="deviceType", description="设备类型")
    active_timeout: int | None = Field(default=None, alias="activeTimeout", description="token活跃超时时间（秒）")
    timeout: int | None = Field(default=None, description="token固定超时时间（秒）")
    status: str | None = Field(default=None, description="状态（0正常 1停用）")

    @field_validator("client_key")
    @classmethod
    def check_client_key(cls, value: str | None) -> str:
        if value is None or not value.strip():
            raise ValueError("客户端key不能为空")
        return value

    @field_validator("client_secret")
    @classmethod
    def check_client_secret(cls, value: str | None) -> str:
        if value is None or not value.strip():
            raise ValueError("客户端秘钥不能为空")
        return value

    @field_validator("grant_type_list")
    @classmethod
    def check_grant_type_list(cls, value: list[str] | None) -> list[str]:
        if value is None:
            raise ValueError("授权类型不能为空")
        return value


class ClientUpdateSchema(ClientCreateSchema):
    """修改客户端入参。"""

    id: int | None = Field(default=None, validate_default=True, description="主键ID")
    client_id: str | None = Field(default=None, alias="clientId", description="客户端id")

    @field_validator("id")
    @classmethod
    def check_id(cls, value: int | None) -> int:
        if value is None:
            raise ValueError("id不能为空")
        return value


class ClientStatusSchema(BaseModel):
    """客户端状态修改入参。"""

    model_config = ConfigDict(populate_by_name=True)

    client_id: str | None = Field(default=None, validate_default=True, alias="clientId", description="客户端id")
    status: str | None = Field(default=None, validate_default=True, description="状态（0正常 1停用）")

    @field_validator("client_id")
    @classmethod
    def check_client_id(cls, value: str | None) -> str:
        if value is None or not value.strip():
            raise ValueError("客户端id不能为空")
        return value

    @field_validator("status")
    @classmethod
    def check_status(cls, value: str | None) -> str:
        if value is None or not value.strip():
            raise ValueError("状态不能为空")
        return value


class ClientOutSchema(BaseModel):
    """客户端出参。"""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True, alias_generator=to_camel)

    id: int | None = Field(default=None, description="主键ID")
    client_id: str | None = Field(default=None, description="客户端id")
    client_key: str | None = Field(default=None, description="客户端key")
    client_secret: str | None = Field(default=None, description="客户端秘钥")
    grant_type_list: list[str] = Field(default_factory=list, description="授权类型列表")
    grant_type: str | None = Field(default=None, description="授权类型（逗号分隔）")
    device_type: str | None = Field(default=None, description="设备类型")
    active_timeout: int | None = Field(default=None, description="token活跃超时时间（秒）")
    timeout: int | None = Field(default=None, description="token固定超时时间（秒）")
    status: str | None = Field(default=None, description="状态（0正常 1停用）")

    @model_validator(mode="after")
    def split_grant_type(self):
        # 授权类型由逗号分隔串拆分为列表
        if not self.grant_type_list and self.grant_type:
            self.grant_type_list = str2list(self.grant_type)
        return self
