"""通知公告的域模型。"""

from sqlalchemy import LargeBinary, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base_model import BaseEntity


class NoticeModel(BaseEntity):
    """通知公告表 sys_notice"""

    __tablename__ = "sys_notice"
    __table_args__ = {"comment": "通知公告表"}

    notice_title: Mapped[str] = mapped_column(String(50), nullable=False, comment="公告标题")
    notice_type: Mapped[str] = mapped_column(String(1), nullable=False, comment="公告类型（1通知 2公告）")
    notice_content: Mapped[bytes | None] = mapped_column(LargeBinary, default=None, nullable=True, comment="公告内容（UTF-8 字节）")
    status: Mapped[str | None] = mapped_column(String(1), default="0", nullable=True, comment="公告状态（0正常 1关闭）")
    remark: Mapped[str | None] = mapped_column(String(255), default=None, nullable=True, comment="备注")
