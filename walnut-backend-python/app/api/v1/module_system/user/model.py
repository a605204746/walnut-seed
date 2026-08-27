"""用户域模型（sys_user 及用户-角色、用户-岗位关联表）。"""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

# 导入关联模型模块，确保字符串关系解析时类已注册（无循环依赖）
from app.api.v1.module_system.dept.model import DeptModel  # noqa: E402, F401
from app.api.v1.module_system.post.model import PostModel  # noqa: E402, F401
from app.core.base_model import BaseEntity, MappedBase, SoftDeleteMixin

if TYPE_CHECKING:
    from app.api.v1.module_system.role.model import RoleModel


class UserRoleModel(MappedBase):
    """用户和角色关联表 sys_user_role（复合主键，无审计字段）。"""

    __tablename__ = "sys_user_role"
    __table_args__ = {"comment": "用户和角色关联表"}

    user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, comment="用户ID")
    role_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, comment="角色ID")


class UserPostModel(MappedBase):
    """用户与岗位关联表 sys_user_post（复合主键，无审计字段）。"""

    __tablename__ = "sys_user_post"
    __table_args__ = {"comment": "用户与岗位关联表"}

    user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, comment="用户ID")
    post_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, comment="岗位ID")


class UserModel(SoftDeleteMixin, BaseEntity):
    """用户信息表 sys_user"""

    __tablename__ = "sys_user"
    __table_args__ = {"comment": "用户信息表"}

    dept_id: Mapped[int | None] = mapped_column(BigInteger, default=None, nullable=True, index=True, comment="部门ID")
    user_name: Mapped[str] = mapped_column(String(30), nullable=False, index=True, comment="用户账号")
    nick_name: Mapped[str] = mapped_column(String(30), nullable=False, comment="用户昵称")
    user_type: Mapped[str] = mapped_column(String(10), default="sys_user", nullable=False, comment="用户类型（sys_user系统用户）")
    email: Mapped[str | None] = mapped_column(String(50), default="", nullable=True, comment="用户邮箱")
    phonenumber: Mapped[str | None] = mapped_column(String(11), default="", nullable=True, comment="手机号码")
    sex: Mapped[str | None] = mapped_column(String(1), default="0", nullable=True, comment="用户性别")
    avatar: Mapped[str | None] = mapped_column(String(500), default=None, nullable=True, comment="用户头像")
    password: Mapped[str | None] = mapped_column(String(100), default="", nullable=True, comment="密码")
    status: Mapped[str] = mapped_column(String(1), default="0", nullable=False, comment="帐号状态（0正常 1停用）")
    login_ip: Mapped[str | None] = mapped_column(String(128), default="", nullable=True, comment="最后登录IP")
    login_date: Mapped[datetime | None] = mapped_column(DateTime, default=None, nullable=True, comment="最后登录时间")
    remark: Mapped[str | None] = mapped_column(String(500), default=None, nullable=True, comment="备注")

    # 关联（不声明数据库级外键）
    roles: Mapped[list["RoleModel"]] = relationship(
        secondary="sys_user_role",
        primaryjoin="UserModel.id == foreign(UserRoleModel.user_id)",
        secondaryjoin="RoleModel.id == foreign(UserRoleModel.role_id)",
        back_populates="users",
        lazy="selectin",
    )
    posts: Mapped[list["PostModel"]] = relationship(  # noqa: F821
        secondary="sys_user_post",
        primaryjoin="UserModel.id == foreign(UserPostModel.user_id)",
        secondaryjoin="PostModel.id == foreign(UserPostModel.post_id)",
        lazy="selectin",
    )
    dept: Mapped["DeptModel | None"] = relationship(  # noqa: F821
        primaryjoin="UserModel.dept_id == foreign(DeptModel.id)",
        lazy="selectin",
    )
