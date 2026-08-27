"""日志域入参/出参模型。

时间范围查询：通过可选查询参数 begin_time/end_time（alias 为 beginTime/endTime）过滤，格式 yyyy-MM-dd。
"""


from pydantic import BaseModel, ConfigDict, Field, alias_generators, field_validator

from app.core.base_schema import PageQueryParam
from app.core.validator import DateStr, DateTimeStr


class OperLogFilterSchema(BaseModel):
    """操作日志查询条件。"""

    model_config = ConfigDict(populate_by_name=True)

    title: str | None = Field(default=None, description="模块标题")
    business_type: int | None = Field(default=None, alias="businessType", description="业务类型（0其它 1新增 2修改 3删除）")
    business_types: list[int] | None = Field(default=None, alias="businessTypes", description="业务类型数组")
    status: int | None = Field(default=None, description="操作状态（0正常 1异常）")
    oper_name: str | None = Field(default=None, alias="operName", description="操作人员")
    oper_ip: str | None = Field(default=None, alias="operIp", description="主机地址")
    begin_time: DateStr | None = Field(default=None, alias="beginTime", description="开始时间（yyyy-MM-dd）")
    end_time: DateStr | None = Field(default=None, alias="endTime", description="结束时间（yyyy-MM-dd）")

    @field_validator("business_types", mode="before")
    @classmethod
    def split_business_types(cls, value):
        """兼容 businessTypes=1,2 逗号分隔串。"""
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()] or None
        return value


class OperLogQueryParam(OperLogFilterSchema, PageQueryParam):
    """操作日志分页查询参数（GET /monitor/operlog/list）。"""


class OperLogOutSchema(BaseModel):
    """操作日志记录视图对象。"""

    model_config = ConfigDict(from_attributes=True, alias_generator=alias_generators.to_camel, populate_by_name=True)

    id: int | None = Field(default=None, description="日志主键")
    title: str | None = Field(default=None, description="模块标题")
    business_type: int | None = Field(default=None, description="业务类型（0其它 1新增 2修改 3删除）")
    method: str | None = Field(default=None, description="方法名称")
    request_method: str | None = Field(default=None, description="请求方式")
    operator_type: int | None = Field(default=None, description="操作类别（0其它 1后台用户 2手机端用户）")
    oper_name: str | None = Field(default=None, description="操作人员")
    dept_name: str | None = Field(default=None, description="部门名称")
    oper_url: str | None = Field(default=None, description="请求URL")
    oper_ip: str | None = Field(default=None, description="主机地址")
    oper_location: str | None = Field(default=None, description="操作地点")
    oper_param: str | None = Field(default=None, description="请求参数")
    json_result: str | None = Field(default=None, description="返回参数")
    status: int | None = Field(default=None, description="操作状态（0正常 1异常）")
    error_msg: str | None = Field(default=None, description="错误消息")
    oper_time: DateTimeStr | None = Field(default=None, description="操作时间")
    cost_time: int | None = Field(default=None, description="消耗时间（毫秒）")


class LogininforFilterSchema(BaseModel):
    """登录日志查询条件。"""

    model_config = ConfigDict(populate_by_name=True)

    user_name: str | None = Field(default=None, alias="userName", description="用户账号")
    ipaddr: str | None = Field(default=None, description="登录IP地址")
    status: str | None = Field(default=None, description="登录状态（0成功 1失败）")
    begin_time: DateStr | None = Field(default=None, alias="beginTime", description="开始时间（yyyy-MM-dd）")
    end_time: DateStr | None = Field(default=None, alias="endTime", description="结束时间（yyyy-MM-dd）")


class LogininforQueryParam(LogininforFilterSchema, PageQueryParam):
    """登录日志分页查询参数（GET /monitor/logininfor/list）。"""


class LogininforOutSchema(BaseModel):
    """系统访问记录视图对象。"""

    model_config = ConfigDict(from_attributes=True, alias_generator=alias_generators.to_camel, populate_by_name=True)

    id: int | None = Field(default=None, description="访问ID")
    user_name: str | None = Field(default=None, description="用户账号")
    client_key: str | None = Field(default=None, description="客户端")
    device_type: str | None = Field(default=None, description="设备类型")
    ipaddr: str | None = Field(default=None, description="登录IP地址")
    login_location: str | None = Field(default=None, description="登录地点")
    browser: str | None = Field(default=None, description="浏览器类型")
    os: str | None = Field(default=None, description="操作系统")
    status: str | None = Field(default=None, description="登录状态（0成功 1失败）")
    msg: str | None = Field(default=None, description="提示消息")
    login_time: DateTimeStr | None = Field(default=None, description="访问时间")


# ==================== 导出表头 ====================

OPER_LOG_EXPORT_HEADERS: dict[str, str] = {
    "id": "日志主键",
    "title": "操作模块",
    "business_type": "业务类型",
    "method": "请求方法",
    "request_method": "请求方式",
    "operator_type": "操作类别",
    "oper_name": "操作人员",
    "dept_name": "部门名称",
    "oper_url": "请求地址",
    "oper_ip": "操作地址",
    "oper_location": "操作地点",
    "oper_param": "请求参数",
    "json_result": "返回参数",
    "status": "状态",
    "error_msg": "错误消息",
    "oper_time": "操作时间",
    "cost_time": "消耗时间",
}

LOGININFOR_EXPORT_HEADERS: dict[str, str] = {
    "id": "序号",
    "user_name": "用户账号",
    "client_key": "客户端",
    "device_type": "设备类型",
    "status": "登录状态",
    "ipaddr": "登录地址",
    "login_location": "登录地点",
    "browser": "浏览器",
    "os": "操作系统",
    "msg": "提示消息",
    "login_time": "访问时间",
}

# 操作类别：0=其它，1=后台用户，2=手机端用户
OPERATOR_TYPE_LABELS: dict[str, str] = {"0": "其它", "1": "后台用户", "2": "手机端用户"}
