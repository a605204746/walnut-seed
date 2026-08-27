"""字典类型与字典数据的域模型。"""

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base_model import BaseEntity


class DictTypeModel(BaseEntity):
    """字典类型表 sys_dict_type"""

    __tablename__ = "sys_dict_type"
    __table_args__ = {"comment": "字典类型表"}

    dict_name: Mapped[str | None] = mapped_column(String(100), default="", nullable=True, comment="字典名称")
    dict_type: Mapped[str | None] = mapped_column(String(100), default="", nullable=True, unique=True, comment="字典类型")
    remark: Mapped[str | None] = mapped_column(String(500), default=None, nullable=True, comment="备注")


class DictDataModel(BaseEntity):
    """字典数据表 sys_dict_data"""

    __tablename__ = "sys_dict_data"
    __table_args__ = {"comment": "字典数据表"}

    dict_sort: Mapped[int | None] = mapped_column(Integer, default=0, nullable=True, comment="字典排序")
    dict_label: Mapped[str | None] = mapped_column(String(100), default="", nullable=True, comment="字典标签")
    dict_value: Mapped[str | None] = mapped_column(String(100), default="", nullable=True, comment="字典键值")
    dict_type: Mapped[str | None] = mapped_column(String(100), default="", nullable=True, index=True, comment="字典类型")
    css_class: Mapped[str | None] = mapped_column(String(100), default=None, nullable=True, comment="样式属性（其他样式扩展）")
    list_class: Mapped[str | None] = mapped_column(String(100), default=None, nullable=True, comment="表格回显样式")
    is_default: Mapped[str | None] = mapped_column(String(1), default="N", nullable=True, comment="是否默认（Y是 N否）")
    remark: Mapped[str | None] = mapped_column(String(500), default=None, nullable=True, comment="备注")
