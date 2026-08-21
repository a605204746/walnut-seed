"""社交登录绑定关系的域模型。"""

from sqlalchemy import BigInteger, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base_model import BaseEntity, SoftDeleteMixin


class SocialModel(SoftDeleteMixin, BaseEntity):
    """社交授权关系表 sys_social"""

    __tablename__ = "sys_social"
    __table_args__ = {"comment": "社交授权关系表"}

    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True, comment="用户ID")
    auth_id: Mapped[str] = mapped_column(String(255), nullable=False, comment="平台+平台唯一id")
    source: Mapped[str] = mapped_column(String(255), nullable=False, comment="用户来源")
    open_id: Mapped[str | None] = mapped_column(String(255), default=None, nullable=True, comment="平台openid")
    user_name: Mapped[str] = mapped_column(String(30), nullable=False, comment="登录账号")
    nick_name: Mapped[str | None] = mapped_column(String(30), default="", nullable=True, comment="用户昵称")
    email: Mapped[str | None] = mapped_column(String(255), default="", nullable=True, comment="用户邮箱")
    avatar: Mapped[str | None] = mapped_column(String(500), default="", nullable=True, comment="用户头像")
    access_token: Mapped[str] = mapped_column(String(2000), nullable=False, comment="用户的授权令牌")
    expire_in: Mapped[int | None] = mapped_column(Integer, default=None, nullable=True, comment="access_token的过期时间")
    refresh_token: Mapped[str | None] = mapped_column(String(255), default=None, nullable=True, comment="刷新令牌")
    access_code: Mapped[str | None] = mapped_column(String(2000), default=None, nullable=True, comment="授权code")
    union_id: Mapped[str | None] = mapped_column(String(255), default=None, nullable=True, comment="平台union_id")
    scope: Mapped[str | None] = mapped_column(String(255), default=None, nullable=True, comment="授予的权限")
    token_type: Mapped[str | None] = mapped_column(String(255), default=None, nullable=True, comment="令牌类型")
    id_token: Mapped[str | None] = mapped_column(String(2000), default=None, nullable=True, comment="id_token(部分平台可用)")
    mac_algorithm: Mapped[str | None] = mapped_column(String(255), default=None, nullable=True, comment="MAC算法")
    mac_key: Mapped[str | None] = mapped_column(String(255), default=None, nullable=True, comment="MAC密钥")
    code: Mapped[str | None] = mapped_column(String(255), default=None, nullable=True, comment="请求码")
    oauth_token: Mapped[str | None] = mapped_column(String(255), default=None, nullable=True, comment="OAuth token")
    oauth_token_secret: Mapped[str | None] = mapped_column(String(255), default=None, nullable=True, comment="OAuth token secret")
