"""认证模块入参/出参模型。"""

from pydantic import BaseModel, ConfigDict, Field


class LoginBodySchema(BaseModel):
    """登录公共入参（字段名与前端契约一致）。"""

    model_config = ConfigDict(populate_by_name=True)

    client_id: str = Field(..., min_length=1, alias="clientId", description="客户端id")
    grant_type: str = Field(..., min_length=1, alias="grantType", description="授权/登录类型")
    tenant_id: str | None = Field(default=None, alias="tenantId", description="租户id（未启用多租户，忽略）")
    code: str | None = Field(default=None, description="验证码")
    uuid: str | None = Field(default=None, description="验证码唯一标识")


class PasswordLoginBodySchema(LoginBodySchema):
    """密码登录入参。"""

    username: str = Field(..., min_length=2, max_length=30, description="用户名")
    password: str = Field(..., min_length=5, max_length=30, description="密码")


class RegisterBodySchema(LoginBodySchema):
    """注册入参。"""

    username: str = Field(..., min_length=2, max_length=30, description="用户名")
    password: str = Field(..., min_length=5, max_length=30, description="密码")
    user_type: str | None = Field(default=None, alias="userType", description="用户类型")


class CaptchaOutSchema(BaseModel):
    """验证码响应（序列化用 by_alias 输出驼峰键名）。"""

    model_config = ConfigDict(populate_by_name=True)

    captcha_enabled: bool = Field(default=True, alias="captchaEnabled", description="是否开启验证码")
    uuid: str | None = Field(default=None, description="验证码唯一标识")
    img: str | None = Field(default=None, description="验证码图片 base64（前端自行拼接 data:image/png;base64, 前缀）")
