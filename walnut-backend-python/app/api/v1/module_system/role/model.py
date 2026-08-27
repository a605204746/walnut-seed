"""角色域模型（sys_role 及角色-菜单、角色-部门关联表）。"""

from sqlalchemy import BigInteger, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

# 导入关联模型模块，确保字符串关系解析时类已注册（无循环依赖）
from app.api.v1.module_system.dept.model import DeptModel  # noqa: E402, F401
from app.api.v1.module_system.menu.model import MenuModel  # noqa: E402, F401
from app.api.v1.module_system.user.model import UserModel, UserRoleModel  # noqa: E402, F401
from app.core.base_model import BaseEntity, MappedBase, SoftDeleteMixin


class RoleMenuModel(MappedBase):
    """角色和菜单关联表 sys_role_menu（复合主键，无审计字段）。"""

    __tablename__ = "sys_role_menu"
    __table_args__ = {"comment": "角色和菜单关联表"}

    role_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, comment="角色ID")
    menu_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, comment="菜单ID")


class RoleDeptModel(MappedBase):
    """角色和部门关联表 sys_role_dept（复合主键，无审计字段）。"""

    __tablename__ = "sys_role_dept"
    __table_args__ = {"comment": "角色和部门关联表"}

    role_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, comment="角色ID")
    dept_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, comment="部门ID")


class RoleModel(SoftDeleteMixin, BaseEntity):
    """角色信息表 sys_role"""

    __tablename__ = "sys_role"
    __table_args__ = {"comment": "角色信息表"}

    role_name: Mapped[str] = mapped_column(String(30), nullable=False, comment="角色名称")
    role_key: Mapped[str] = mapped_column(String(100), nullable=False, comment="角色权限字符串")
    role_sort: Mapped[int] = mapped_column(Integer, nullable=False, comment="显示顺序")
    data_scope: Mapped[str | None] = mapped_column(String(1), default="1", nullable=True, comment="数据范围（1全部 2自定义 3本部门 4本部门及以下 5仅本人 6本部门及以下或本人）")
    menu_check_strictly: Mapped[int | None] = mapped_column(Integer, default=1, nullable=True, comment="菜单树选择项是否关联显示")
    dept_check_strictly: Mapped[int | None] = mapped_column(Integer, default=1, nullable=True, comment="部门树选择项是否关联显示")
    status: Mapped[str] = mapped_column(String(1), nullable=False, comment="角色状态（0正常 1停用）")
    remark: Mapped[str | None] = mapped_column(String(500), default=None, nullable=True, comment="备注")

    # 关联（不声明数据库级外键）
    users: Mapped[list["UserModel"]] = relationship(  # noqa: F821
        secondary="sys_user_role",
        primaryjoin="RoleModel.id == foreign(UserRoleModel.role_id)",
        secondaryjoin="UserModel.id == foreign(UserRoleModel.user_id)",
        back_populates="roles",
        lazy="selectin",
    )
    menus: Mapped[list["MenuModel"]] = relationship(  # noqa: F821
        secondary="sys_role_menu",
        primaryjoin="RoleModel.id == foreign(RoleMenuModel.role_id)",
        secondaryjoin="MenuModel.id == foreign(RoleMenuModel.menu_id)",
        lazy="selectin",
    )
    depts: Mapped[list["DeptModel"]] = relationship(  # noqa: F821
        secondary="sys_role_dept",
        primaryjoin="RoleModel.id == foreign(RoleDeptModel.role_id)",
        secondaryjoin="DeptModel.id == foreign(RoleDeptModel.dept_id)",
        lazy="selectin",
    )
