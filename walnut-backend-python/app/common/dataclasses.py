"""核心领域模型 / DTO。"""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class BaseLoginUser(BaseModel):
    """登录用户基础模型（抽象基类）。"""

    model_config = ConfigDict(from_attributes=True)

    user_id: int | None = Field(default=None, description="用户ID")
    token: str | None = Field(default=None, description="token")
    username: str | None = Field(default=None, description="用户名")
    user_type: str | None = Field(default=None, description="用户类型 sys_user/app_user")
    login_time: int | None = Field(default=None, description="登录时间戳(ms)")
    expire_time: int | None = Field(default=None, description="过期时间戳(ms)")
    ipaddr: str | None = Field(default=None, description="登录IP")
    login_location: str | None = Field(default=None, description="登录归属地")
    browser: str | None = Field(default=None, description="浏览器")
    os: str | None = Field(default=None, description="操作系统")
    device_type: str | None = Field(default=None, description="设备类型")

    def get_login_id(self) -> str:
        """返回 ``userType:userId`` 形式的登录ID。"""
        if not self.user_type:
            raise ValueError("用户类型不能为空")
        if self.user_id is None:
            raise ValueError("用户ID不能为空")
        return f"{self.user_type}:{self.user_id}"


class LoginUser(BaseLoginUser):
    """系统登录用户。"""

    dept_id: int | None = Field(default=None, description="部门ID")
    dept_category: str | None = Field(default=None, description="部门类别")
    dept_name: str | None = Field(default=None, description="部门名称")
    nickname: str | None = Field(default=None, description="用户昵称")
    menu_permission: set[str] = Field(default_factory=set, description="菜单权限标识集合")
    role_permission: set[str] = Field(default_factory=set, description="角色权限标识集合")
    roles: list[Any] = Field(default_factory=list, description="角色列表")
    posts: list[Any] = Field(default_factory=list, description="岗位列表")
    role_id: int | None = Field(default=None, description="数据范围角色ID")
    client_key: str | None = Field(default=None, description="客户端标识")


class SseMessageDto(BaseModel):
    """SSE 消息 DTO。"""

    user_ids: list[int] = Field(default_factory=list, description="目标用户ID列表，空则广播")
    message: str = Field(default="", description="消息内容")


class WebSocketMessageDto(BaseModel):
    """WebSocket 消息 DTO。"""

    session_keys: list[int] = Field(default_factory=list, description="目标会话键(用户ID)列表，空则广播")
    message: str = Field(default="", description="消息内容")


class OperLogEvent(BaseModel):
    """操作日志事件。"""

    id: int | None = None
    title: str | None = None
    business_type: int | None = None
    business_types: list[int] | None = None
    method: str | None = None
    request_method: str | None = None
    operator_type: int | None = None
    oper_name: str | None = None
    dept_name: str | None = None
    oper_url: str | None = None
    oper_ip: str | None = None
    oper_location: str | None = None
    oper_param: str | None = None
    json_result: str | None = None
    status: int | None = None
    error_msg: str | None = None
    oper_time: str | None = None
    cost_time: int | None = None


class LogininforEvent(BaseModel):
    """登录日志事件。"""

    username: str | None = None
    status: str | None = None  # 0成功 1失败
    message: str | None = None


class UploadResult(BaseModel):
    """上传结果。"""

    url: str | None = Field(default=None, description="文件访问地址")
    original_filename: str | None = Field(default=None, description="原始文件名")
