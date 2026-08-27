"""客户端的域模型。"""

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base_model import BaseEntity, SoftDeleteMixin


class ClientModel(SoftDeleteMixin, BaseEntity):
    """系统授权表 sys_client"""

    __tablename__ = "sys_client"
    __table_args__ = {"comment": "系统授权表"}

    client_id: Mapped[str | None] = mapped_column(String(64), default=None, nullable=True, comment="客户端id")
    client_key: Mapped[str | None] = mapped_column(String(32), default=None, nullable=True, comment="客户端key")
    client_secret: Mapped[str | None] = mapped_column(String(255), default=None, nullable=True, comment="客户端秘钥")
    grant_type: Mapped[str | None] = mapped_column(String(255), default=None, nullable=True, comment="授权类型（逗号分隔）")
    device_type: Mapped[str | None] = mapped_column(String(32), default=None, nullable=True, comment="设备类型")
    active_timeout: Mapped[int | None] = mapped_column(Integer, default=1800, nullable=True, comment="token活跃超时时间（秒）")
    timeout: Mapped[int | None] = mapped_column(Integer, default=604800, nullable=True, comment="token固定超时时间（秒）")
    status: Mapped[str | None] = mapped_column(String(1), default="0", nullable=True, comment="状态（0正常 1停用）")
