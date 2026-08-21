from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Integer, MetaData, String
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase, Mapped, declared_attr, mapped_column

from app.utils.snowflake import IdGeneratorUtil

# 约束/索引命名约定（最佳实践）：让 autogenerate 与 DDL 中的名字稳定、可预测，
# 避免数据库匿名命名导致的迁移 diff 噪音。0N 变体连接全部列名，复合索引不会与单列索引撞名。
NAMING_CONVENTION = {
    "ix": "ix_%(column_0N_label)s",
    "uq": "uq_%(table_name)s_%(column_0N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class MappedBase(AsyncAttrs, DeclarativeBase):
    """声明式基类。

    `AsyncAttrs <https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html>`__
    `DeclarativeBase <https://docs.sqlalchemy.org/en/20/orm/declarative_config.html>`__

    支持 MySQL。
    """

    __abstract__: bool = True

    metadata = MetaData(naming_convention=NAMING_CONVENTION)

    @declared_attr.directive
    def __tablename__(cls) -> str:
        return cls.__name__.lower()


class BaseEntity(MappedBase):
    """实体基类。

    字段：
    - ``id`` 雪花主键；
    - ``create_dept`` / ``create_by`` / ``create_time`` 新增时自动填充；
    - ``update_by`` / ``update_time`` 新增与更新时自动填充。

    自动填充逻辑在 ``base_crud`` 中实现：
    写入时从当前登录上下文取用户ID/部门ID，未登录时取默认值 -1。
    """

    __abstract__: bool = True

    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=False,
        default=IdGeneratorUtil.next_long_id,
        comment="主键ID（雪花）",
    )
    create_dept: Mapped[int | None] = mapped_column(
        BigInteger,
        default=None,
        nullable=True,
        comment="创建部门",
    )
    create_by: Mapped[int | None] = mapped_column(
        BigInteger,
        default=None,
        nullable=True,
        comment="创建者",
    )
    create_time: Mapped[datetime | None] = mapped_column(
        DateTime,
        default=datetime.now,
        nullable=True,
        comment="创建时间",
    )
    update_by: Mapped[int | None] = mapped_column(
        BigInteger,
        default=None,
        nullable=True,
        comment="更新者",
    )
    update_time: Mapped[datetime | None] = mapped_column(
        DateTime,
        default=datetime.now,
        onupdate=datetime.now,
        nullable=True,
        comment="更新时间",
    )


class SoftDeleteMixin(MappedBase):
    """逻辑删除混入（del_flag 字段，按需混入）。"""

    __abstract__: bool = True

    del_flag: Mapped[str] = mapped_column(
        String(1),
        default="0",
        nullable=False,
        index=True,
        comment="删除标志（0代表存在 1代表删除）",
    )


class TreeEntityMixin(MappedBase):
    """树形实体混入（树表公共字段）。"""

    __abstract__: bool = True

    parent_id: Mapped[int | None] = mapped_column(BigInteger, default=0, nullable=True, comment="父级ID")
    ancestors: Mapped[str | None] = mapped_column(String(500), default=None, nullable=True, comment="祖级列表")
    order_num: Mapped[int | None] = mapped_column(Integer, default=0, nullable=True, comment="显示顺序")
