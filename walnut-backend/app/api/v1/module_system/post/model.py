"""岗位的域模型。"""

from sqlalchemy import BigInteger, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base_model import BaseEntity


class PostModel(BaseEntity):
    """岗位信息表 sys_post"""

    __tablename__ = "sys_post"
    __table_args__ = {"comment": "岗位信息表"}

    dept_id: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="部门ID")
    post_code: Mapped[str] = mapped_column(String(64), nullable=False, comment="岗位编码")
    post_category: Mapped[str | None] = mapped_column(String(100), default=None, nullable=True, comment="岗位类别编码")
    post_name: Mapped[str] = mapped_column(String(50), nullable=False, comment="岗位名称")
    post_sort: Mapped[int] = mapped_column(Integer, nullable=False, comment="显示顺序")
    status: Mapped[str] = mapped_column(String(1), nullable=False, comment="状态（0正常 1停用）")
    remark: Mapped[str | None] = mapped_column(String(500), default=None, nullable=True, comment="备注")
