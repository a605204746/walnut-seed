"""部门域模型（sys_dept 表）。"""

from sqlalchemy import BigInteger, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base_model import BaseEntity, SoftDeleteMixin


class DeptModel(SoftDeleteMixin, BaseEntity):
    """部门表 sys_dept"""

    __tablename__ = "sys_dept"
    __table_args__ = {"comment": "部门表"}

    parent_id: Mapped[int | None] = mapped_column(BigInteger, default=0, nullable=True, index=True, comment="父部门ID")
    ancestors: Mapped[str | None] = mapped_column(String(500), default="", nullable=True, comment="祖级列表")
    dept_name: Mapped[str | None] = mapped_column(String(30), default="", nullable=True, comment="部门名称")
    dept_category: Mapped[str | None] = mapped_column(String(100), default=None, nullable=True, comment="部门类别编码")
    order_num: Mapped[int | None] = mapped_column(Integer, default=0, nullable=True, comment="显示顺序")
    leader: Mapped[int | None] = mapped_column(BigInteger, default=None, nullable=True, comment="负责人（用户ID）")
    phone: Mapped[str | None] = mapped_column(String(11), default=None, nullable=True, comment="联系电话")
    email: Mapped[str | None] = mapped_column(String(50), default=None, nullable=True, comment="邮箱")
    status: Mapped[str | None] = mapped_column(String(1), default="0", nullable=True, comment="部门状态（0正常 1停用）")
