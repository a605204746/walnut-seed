"""操作日志与登录日志的域模型（无审计字段，直接继承 MappedBase）。"""

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base_model import MappedBase
from app.utils.snowflake import IdGeneratorUtil


class OperLogModel(MappedBase):
    """操作日志记录 sys_oper_log"""

    __tablename__ = "sys_oper_log"
    __table_args__ = {"comment": "操作日志记录"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=IdGeneratorUtil.next_long_id, comment="日志主键（雪花）")
    title: Mapped[str | None] = mapped_column(String(50), default="", nullable=True, index=True, comment="模块标题")
    business_type: Mapped[int | None] = mapped_column(Integer, default=0, nullable=True, index=True, comment="业务类型（0其它 1新增 2修改 3删除）")
    method: Mapped[str | None] = mapped_column(String(100), default="", nullable=True, comment="方法名称")
    request_method: Mapped[str | None] = mapped_column(String(10), default="", nullable=True, comment="请求方式")
    operator_type: Mapped[int | None] = mapped_column(Integer, default=0, nullable=True, comment="操作类别（0其它 1后台用户 2手机端用户）")
    oper_name: Mapped[str | None] = mapped_column(String(50), default="", nullable=True, comment="操作人员")
    dept_name: Mapped[str | None] = mapped_column(String(50), default="", nullable=True, comment="部门名称")
    oper_url: Mapped[str | None] = mapped_column(String(255), default="", nullable=True, comment="请求URL")
    oper_ip: Mapped[str | None] = mapped_column(String(128), default="", nullable=True, comment="主机地址")
    oper_location: Mapped[str | None] = mapped_column(String(255), default="", nullable=True, comment="操作地点")
    oper_param: Mapped[str | None] = mapped_column(String(4000), default="", nullable=True, comment="请求参数")
    json_result: Mapped[str | None] = mapped_column(String(4000), default="", nullable=True, comment="返回参数")
    status: Mapped[int | None] = mapped_column(Integer, default=0, nullable=True, index=True, comment="操作状态（0正常 1异常）")
    error_msg: Mapped[str | None] = mapped_column(String(4000), default="", nullable=True, comment="错误消息")
    oper_time: Mapped[datetime | None] = mapped_column(DateTime, default=None, nullable=True, index=True, comment="操作时间")
    cost_time: Mapped[int | None] = mapped_column(BigInteger, default=0, nullable=True, comment="消耗时间（毫秒）")


class LogininforModel(MappedBase):
    """系统访问记录 sys_logininfor"""

    __tablename__ = "sys_logininfor"
    __table_args__ = {"comment": "系统访问记录"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=IdGeneratorUtil.next_long_id, comment="访问ID（雪花）")
    user_name: Mapped[str | None] = mapped_column(String(50), default="", nullable=True, comment="用户账号")
    client_key: Mapped[str | None] = mapped_column(String(32), default="", nullable=True, comment="客户端")
    device_type: Mapped[str | None] = mapped_column(String(32), default="", nullable=True, comment="设备类型")
    ipaddr: Mapped[str | None] = mapped_column(String(128), default="", nullable=True, comment="登录IP地址")
    login_location: Mapped[str | None] = mapped_column(String(255), default="", nullable=True, comment="登录地点")
    browser: Mapped[str | None] = mapped_column(String(50), default="", nullable=True, comment="浏览器类型")
    os: Mapped[str | None] = mapped_column(String(50), default="", nullable=True, comment="操作系统")
    status: Mapped[str | None] = mapped_column(String(1), default="0", nullable=True, index=True, comment="登录状态（0成功 1失败）")
    msg: Mapped[str | None] = mapped_column(String(255), default="", nullable=True, comment="提示消息")
    login_time: Mapped[datetime | None] = mapped_column(DateTime, default=None, nullable=True, index=True, comment="访问时间")
