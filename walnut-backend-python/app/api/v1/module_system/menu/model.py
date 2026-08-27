"""菜单域模型（sys_menu 表）。"""

from sqlalchemy import BigInteger, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base_model import BaseEntity


class MenuModel(BaseEntity):
    """菜单权限表 sys_menu（无 del_flag）。"""

    __tablename__ = "sys_menu"
    __table_args__ = {"comment": "菜单权限表"}

    menu_name: Mapped[str] = mapped_column(String(50), nullable=False, comment="菜单名称")
    parent_id: Mapped[int | None] = mapped_column(BigInteger, default=0, nullable=True, index=True, comment="父菜单ID")
    order_num: Mapped[int | None] = mapped_column(Integer, default=0, nullable=True, comment="显示顺序")
    path: Mapped[str | None] = mapped_column(String(200), default="", nullable=True, comment="路由地址")
    component: Mapped[str | None] = mapped_column(String(255), default=None, nullable=True, comment="组件路径")
    query_param: Mapped[str | None] = mapped_column(String(255), default=None, nullable=True, comment="路由参数")
    is_frame: Mapped[str | None] = mapped_column(String(1), default="1", nullable=True, comment="是否为外链（0是 1否）")
    is_cache: Mapped[str | None] = mapped_column(String(1), default="0", nullable=True, comment="是否缓存（0缓存 1不缓存）")
    menu_type: Mapped[str | None] = mapped_column(String(1), default="", nullable=True, comment="菜单类型（M目录 C菜单 F按钮）")
    visible: Mapped[str | None] = mapped_column(String(1), default="0", nullable=True, comment="显示状态（0显示 1隐藏）")
    status: Mapped[str | None] = mapped_column(String(1), default="0", nullable=True, comment="菜单状态（0正常 1停用）")
    perms: Mapped[str | None] = mapped_column(String(100), default=None, nullable=True, comment="权限标识")
    icon: Mapped[str | None] = mapped_column(String(100), default="#", nullable=True, comment="菜单图标")
    remark: Mapped[str | None] = mapped_column(String(500), default="", nullable=True, comment="备注")
