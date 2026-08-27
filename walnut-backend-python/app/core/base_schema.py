"""通用 Schema（审计字段输出模型 + 认证模型）。"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.common.request import PageReq
from app.core.validator import DateTimeStr


class BaseSchema(BaseModel):
    """实体公共输出模型（审计字段）。"""

    model_config = ConfigDict(from_attributes=True)

    id: int | None = Field(default=None, description="主键ID")
    create_dept: int | None = Field(default=None, description="创建部门")
    create_by: int | None = Field(default=None, description="创建者")
    create_time: DateTimeStr | None = Field(default=None, description="创建时间")
    update_by: int | None = Field(default=None, description="更新者")
    update_time: DateTimeStr | None = Field(default=None, description="更新时间")


class CoreUserSchema(BaseModel):
    """核心层用户信息（不依赖业务模块，业务 UserOutSchema 应继承此类）。"""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(default=0, description="用户ID")
    username: str | None = Field(default=None, description="用户名")
    nickname: str | None = Field(default=None, description="用户昵称")
    dept_id: int | None = Field(default=None, description="部门ID")
    is_superuser: bool = Field(default=False, description="是否超级管理员")


class AuthSchema(BaseModel):
    """权限认证模型（当前登录用户上下文与权限集合）。"""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    user: CoreUserSchema = Field(default_factory=CoreUserSchema, description="用户信息", exclude=True)
    permissions: list[str] = Field(default_factory=list, description="菜单权限标识列表")
    roles: list[str] = Field(default_factory=list, description="角色权限标识列表")
    menu_ids: list[int] = Field(default_factory=list, description="角色授权的菜单ID列表")


class JWTPayloadSchema(BaseModel):
    """JWT 载荷模型（签发时写入的扩展字段）。"""

    sub: str = Field(..., description="登录ID/会话编号")
    user_id: int | None = Field(default=None, description="用户ID")
    user_name: str | None = Field(default=None, description="用户名")
    dept_id: int | None = Field(default=None, description="部门ID")
    dept_name: str | None = Field(default=None, description="部门名称")
    dept_category: str | None = Field(default=None, description="部门类别")
    clientid: str | None = Field(default=None, description="客户端ID")
    is_refresh: bool = Field(default=False, description="是否刷新token")
    exp: datetime | int = Field(..., description="过期时间")

    @model_validator(mode="after")
    def validate_fields(self):
        if not self.sub or len(self.sub.strip()) == 0:
            raise ValueError("会话编号不能为空")
        return self


class JWTOutSchema(BaseModel):
    """JWT 响应模型。"""

    model_config = ConfigDict(from_attributes=True)

    access_token: str = Field(..., min_length=1, description="访问token")
    refresh_token: str | None = Field(default=None, description="刷新token")
    token_type: str = Field(default="Bearer", description="token类型")
    expires_in: int = Field(..., gt=0, description="过期时间(秒)")


class PageQueryParam(PageReq):
    """分页查询参数（GET 请求使用）。

    前端契约字段名为驼峰（pageNum/pageSize/orderByColumn/isAsc），
    通过 alias 对齐；Python 侧仍以 snake_case 访问。
    继承 ``PageReq`` 的分页字段与 offset/has_limit，可直接传入分页接口。
    """

    page_size: int | None = Field(default=10, ge=1, le=1000, alias="pageSize", description="每页数量")
