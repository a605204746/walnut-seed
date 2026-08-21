"""参数配置的域模型。"""

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base_model import BaseEntity


class ConfigModel(BaseEntity):
    """参数配置表 sys_config"""

    __tablename__ = "sys_config"
    __table_args__ = {"comment": "参数配置表"}

    config_name: Mapped[str | None] = mapped_column(String(100), default="", nullable=True, comment="参数名称")
    config_key: Mapped[str | None] = mapped_column(String(100), default="", nullable=True, index=True, comment="参数键名")
    config_value: Mapped[str | None] = mapped_column(String(500), default="", nullable=True, comment="参数键值")
    config_type: Mapped[str | None] = mapped_column(String(1), default="N", nullable=True, comment="系统内置（Y是 N否）")
    remark: Mapped[str | None] = mapped_column(String(500), default=None, nullable=True, comment="备注")
