"""社交登录绑定关系的入参/出参模型。

字段输出统一为驼峰命名（经 alias_generator 转换）。
"""

from pydantic import BaseModel, ConfigDict, Field, alias_generators, field_validator

from app.core.validator import DateTimeStr


class SocialCreateSchema(BaseModel):
    """新增社会化关系入参。"""

    model_config = ConfigDict(alias_generator=alias_generators.to_camel, populate_by_name=True)

    user_id: int = Field(..., description="用户的ID")
    auth_id: str = Field(..., description="认证唯一ID")
    source: str = Field(..., description="用户来源")
    access_token: str = Field(..., description="用户的授权令牌")
    expire_in: int | None = Field(default=None, description="用户的授权令牌的有效期，部分平台可能没有")
    refresh_token: str | None = Field(default=None, description="刷新令牌，部分平台可能没有")
    open_id: str | None = Field(default=None, description="平台唯一id")
    access_code: str | None = Field(default=None, description="平台的授权信息，部分平台可能没有")
    union_id: str | None = Field(default=None, description="用户的 unionid")
    scope: str | None = Field(default=None, description="授予的权限，部分平台可能没有")
    user_name: str | None = Field(default=None, description="授权的第三方账号")
    nick_name: str | None = Field(default=None, description="授权的第三方昵称")
    email: str | None = Field(default=None, description="授权的第三方邮箱")
    avatar: str | None = Field(default=None, description="授权的第三方头像地址")
    token_type: str | None = Field(default=None, description="个别平台的授权信息，部分平台可能没有")
    id_token: str | None = Field(default=None, description="id token，部分平台可能没有")
    mac_algorithm: str | None = Field(default=None, description="小米平台用户的附带属性，部分平台可能没有")
    mac_key: str | None = Field(default=None, description="小米平台用户的附带属性，部分平台可能没有")
    code: str | None = Field(default=None, description="用户的授权code，部分平台可能没有")
    oauth_token: str | None = Field(default=None, description="Twitter平台用户的附带属性，部分平台可能没有")
    oauth_token_secret: str | None = Field(default=None, description="Twitter平台用户的附带属性，部分平台可能没有")

    @field_validator("auth_id", "source", "access_token")
    @classmethod
    def check_not_blank(cls, value: str | None, info) -> str:
        messages = {"auth_id": "认证唯一ID不能为空", "source": "用户来源不能为空", "access_token": "用户的授权令牌不能为空"}
        if value is None or not value.strip():
            raise ValueError(messages[info.field_name])
        return value


class SocialUpdateSchema(SocialCreateSchema):
    """更新社会化关系入参。"""

    id: int = Field(..., description="主键")


class SocialOutSchema(BaseModel):
    """社会化关系视图对象。"""

    model_config = ConfigDict(from_attributes=True, alias_generator=alias_generators.to_camel, populate_by_name=True)

    id: int | None = Field(default=None, description="主键")
    user_id: int | None = Field(default=None, description="用户ID")
    auth_id: str | None = Field(default=None, description="平台+平台唯一id")
    source: str | None = Field(default=None, description="用户来源")
    access_token: str | None = Field(default=None, description="用户的授权令牌")
    expire_in: int | None = Field(default=None, description="access_token的过期时间")
    refresh_token: str | None = Field(default=None, description="刷新令牌")
    open_id: str | None = Field(default=None, description="平台openid")
    user_name: str | None = Field(default=None, description="登录账号")
    nick_name: str | None = Field(default=None, description="用户昵称")
    email: str | None = Field(default=None, description="用户邮箱")
    avatar: str | None = Field(default=None, description="用户头像")
    access_code: str | None = Field(default=None, description="授权code")
    union_id: str | None = Field(default=None, description="平台union_id")
    scope: str | None = Field(default=None, description="授予的权限")
    token_type: str | None = Field(default=None, description="令牌类型")
    id_token: str | None = Field(default=None, description="id_token(部分平台可用)")
    mac_algorithm: str | None = Field(default=None, description="MAC算法")
    mac_key: str | None = Field(default=None, description="MAC密钥")
    code: str | None = Field(default=None, description="请求码")
    oauth_token: str | None = Field(default=None, description="OAuth token")
    oauth_token_secret: str | None = Field(default=None, description="OAuth token secret")
    create_time: DateTimeStr | None = Field(default=None, description="创建时间")
