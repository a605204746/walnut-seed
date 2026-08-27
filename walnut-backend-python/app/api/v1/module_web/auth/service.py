"""认证服务。

会话模型（JWT + Redis 实现）：
- ``user_session:<session_id>``：会话 JSON（user_id/user_name/nickname/dept_id/user_status/
  menu_permission/role_permission/menu_ids/_active_timeout），滑动过期时 TTL=client.active_timeout；
- ``access_token:<session_id>``：JWT 令牌值（滑动过期续期用）；
- ``online_tokens:<token>``：在线用户信息 JSON。
"""

import json
import uuid
from datetime import datetime, timedelta

import bcrypt
from fastapi import Request
from redis.asyncio.client import Redis
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.constant import Constants, SystemConstants
from app.common.enums import CacheNames, LoginType, UserType
from app.config.setting import settings
from app.core.base_schema import JWTPayloadSchema
from app.core.exceptions import NotLoginException, ServiceException
from app.core.logger import logger
from app.core.redis_crud import RedisUtils
from app.core.security import create_access_token, decode_access_token
from app.utils.common_util import get_client_ip
from app.utils.i18n import MessageUtils
from app.utils.ip_local_util import get_real_address_by_ip
from app.utils.snowflake import IdGeneratorUtil
from app.utils.string_util import equals_ignore_case

from ..exception import AuthErrorCode
from . import captcha as captcha_gen
from .schema import CaptchaOutSchema, PasswordLoginBodySchema, RegisterBodySchema


class AuthService:
    def __init__(self, db: AsyncSession, redis: Redis, request: Request) -> None:
        self.db = db
        self.redis = redis
        self.request = request
        self.redis_util = RedisUtils(redis)

    # ==================== 登录 ====================

    async def load_user_by_username(self, username: str):
        """按用户账号查询可登录用户；用户不存在返回 None（不向外暴露存在性，防用户枚举）。"""
        from app.api.v1.module_system.user.model import UserModel

        stmt = select(UserModel).where(UserModel.user_name == username, UserModel.del_flag == SystemConstants.NORMAL)
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def validate_captcha(self, username: str, code: str | None, uuid_str: str | None) -> None:
        """校验图形验证码。"""
        verify_key = CacheNames.CAPTCHA_CODE_KEY + (uuid_str or "")
        captcha = await self.redis_util.get(verify_key)
        await self.redis_util.delete(verify_key)
        if captcha is None:
            await self.record_logininfor(username, Constants.LOGIN_FAIL, MessageUtils.message("user.jcaptcha.expire"))
            raise ServiceException.of(AuthErrorCode.CAPTCHA_EXPIRED)
        if not equals_ignore_case(code or "", str(captcha)):
            await self.record_logininfor(username, Constants.LOGIN_FAIL, MessageUtils.message("user.jcaptcha.error"))
            raise ServiceException.of(AuthErrorCode.CAPTCHA_ERROR)

    async def check_login(self, login_type: LoginType, username: str, ip: str | None, mismatch: bool) -> None:
        """登录重试次数校验。``mismatch=True`` 表示密码/验证码不匹配。

        锁定键为 ``用户名+IP`` 组合，防止攻击者用错误密码恶意锁定他人账号（DoS）；
        不匹配时统一抛出 ``用户不存在/密码错误``（code=10005），不回显错误次数，防用户枚举。
        """
        error_key = f"{CacheNames.PWD_ERR_CNT_KEY}{username}:{ip or 'unknown'}"
        max_retry = settings.PASSWORD_MAX_RETRY_COUNT
        lock_time = settings.PASSWORD_LOCK_TIME
        exceed_key = login_type.retry_limit_key

        raw = await self.redis_util.get(error_key)
        error_number = int(raw) if raw else 0
        if error_number >= max_retry:
            await self.record_logininfor(username, Constants.LOGIN_FAIL, MessageUtils.message(exceed_key, max_retry, lock_time))
            raise ServiceException.of(AuthErrorCode.USER_PASSWORD_RETRY_LIMIT_EXCEED, max_retry, lock_time)

        if mismatch:
            error_number += 1
            await self.redis_util.set(error_key, error_number, expire=lock_time * 60)
            if error_number >= max_retry:
                await self.record_logininfor(username, Constants.LOGIN_FAIL, MessageUtils.message(exceed_key, max_retry, lock_time))
                raise ServiceException.of(AuthErrorCode.USER_PASSWORD_RETRY_LIMIT_EXCEED, max_retry, lock_time)
            await self.record_logininfor(username, Constants.LOGIN_FAIL, MessageUtils.message("user.password.not.match"))
            raise ServiceException.of(AuthErrorCode.USER_PASSWORD_NOT_MATCH)

        await self.redis_util.delete(error_key)

    async def build_session_info(self, user) -> dict:
        """构建会话信息（用户基本信息、角色权限与菜单权限）。"""
        from app.api.v1.module_system.dept.model import DeptModel
        from app.api.v1.module_system.menu.model import MenuModel
        from app.api.v1.module_system.role.model import RoleModel
        from app.api.v1.module_system.user.model import UserRoleModel

        user_id = user.id
        is_super = user_id == SystemConstants.SUPER_ADMIN_ID

        dept_name, dept_category = "", ""
        if user.dept_id:
            dept = await self.db.get(DeptModel, user.dept_id)
            if dept is not None:
                dept_name = dept.dept_name or ""
                dept_category = dept.dept_category or ""

        if is_super:
            role_permission = [SystemConstants.SUPER_ADMIN_ROLE_KEY]
            menu_permission = ["*:*:*"]
            stmt = select(MenuModel.id).where(MenuModel.status == SystemConstants.NORMAL)
            result = await self.db.execute(stmt)
            menu_ids = list(result.scalars().all())
        else:
            # 用户的有效角色（角色状态正常且未删除）
            role_stmt = (
                select(RoleModel)
                .join(UserRoleModel, UserRoleModel.role_id == RoleModel.id)
                .where(UserRoleModel.user_id == user_id, RoleModel.status == SystemConstants.NORMAL, RoleModel.del_flag == SystemConstants.NORMAL)
            )
            roles = list((await self.db.execute(role_stmt)).scalars().all())
            role_permission = [r.role_key for r in roles if r.role_key]
            role_ids = [r.id for r in roles]

            menu_ids, menu_permission = [], []
            if role_ids:
                from app.api.v1.module_system.role.model import RoleMenuModel

                menu_stmt = (
                    select(MenuModel)
                    .join(RoleMenuModel, RoleMenuModel.menu_id == MenuModel.id)
                    .where(RoleMenuModel.role_id.in_(role_ids), MenuModel.status == SystemConstants.NORMAL)
                )
                menus = list((await self.db.execute(menu_stmt)).scalars().all())
                menu_ids = sorted({m.id for m in menus})
                menu_permission = sorted({m.perms for m in menus if m.perms and m.perms.strip()})

        return {
            "user_id": user_id,
            "user_name": user.user_name,
            "nickname": user.nick_name,
            "dept_id": user.dept_id,
            "dept_name": dept_name,
            "dept_category": dept_category,
            "user_status": user.status,
            "menu_permission": menu_permission,
            "role_permission": role_permission,
            "menu_ids": menu_ids,
        }

    async def login_password(self, body: PasswordLoginBodySchema, client) -> dict:
        """密码登录。返回登录响应结构 dict。

        用户不存在与密码错误走同一重试计数路径、返回同一错误码与文案（防用户枚举）。
        """
        username, password = body.username, body.password
        ip = get_client_ip(self.request)

        if settings.CAPTCHA_ENABLE:
            await self.validate_captcha(username, body.code, body.uuid)

        user = await self.load_user_by_username(username)
        if user is not None and SystemConstants.DISABLE == user.status:
            logger.info("登录用户：{} 已被停用.", username)
            raise ServiceException.of(AuthErrorCode.USER_BLOCKED, username)

        # 用户不存在同样计入重试次数（与密码错误统一路径），对外不区分两者
        mismatch = True
        if user is not None:
            try:
                mismatch = not bcrypt.checkpw(password.encode("utf-8"), (user.password or "").encode("utf-8"))
            except ValueError:
                mismatch = True
        else:
            logger.info("登录用户：{} 不存在.", username)
        await self.check_login(LoginType.PASSWORD, username, ip, mismatch)

        session_info = await self.build_session_info(user)
        login_resp = await self.do_login(user, session_info, client)

        # 登录成功日志与登录信息更新
        await self.record_logininfor(username, Constants.LOGIN_SUCCESS, MessageUtils.message("user.login.success"))
        await self.record_login_info(user.id, ip)
        return login_resp

    async def do_login(self, user, session_info: dict, client) -> dict:
        """发放 JWT 并写入会话/在线缓存。"""
        session_id = uuid.uuid4().hex
        timeout = int(client.timeout or settings.ACCESS_TOKEN_EXPIRE_SECONDS)
        active_timeout = int(client.active_timeout or timeout)
        if timeout <= 0 or active_timeout <= 0:
            raise ServiceException("客户端 token 超时时间配置无效")
        # 活跃超时不能超过固定超时，否则 Redis 可能比 JWT 硬过期时间存活更久。
        active_timeout = min(active_timeout, timeout)
        # JWT exp 始终是固定硬过期时间；滑动过期只通过 Redis TTL 实现。
        jwt_expire = timeout

        payload = JWTPayloadSchema(
            sub=session_id,
            user_id=user.id,
            user_name=user.user_name,
            dept_id=session_info.get("dept_id"),
            dept_name=session_info.get("dept_name"),
            dept_category=session_info.get("dept_category"),
            clientid=client.client_id,
            is_refresh=False,
            exp=datetime.now() + timedelta(seconds=jwt_expire),
        )
        token = create_access_token(payload)

        # 将活跃超时写入会话，鉴权续期不依赖全局默认值。
        session_info = {**session_info, "_active_timeout": active_timeout}
        session_ttl = active_timeout if settings.TOKEN_SLIDING_EXPIRE else timeout
        await self.redis_util.set(f"user_session:{session_id}", json.dumps(session_info, ensure_ascii=False), expire=session_ttl)
        await self.redis_util.set(f"access_token:{session_id}", token, expire=session_ttl)

        # 在线用户信息（写入 online_tokens:<token> 键）
        online_dto = await self._build_online_dto(user, session_info, client, token)
        await self.redis_util.set(f"{CacheNames.ONLINE_TOKEN_KEY}{token}", json.dumps(online_dto, ensure_ascii=False), expire=session_ttl)

        return {
            "access_token": token,
            "refresh_token": None,
            "expire_in": timeout,
            "refresh_expire_in": None,
            "client_id": client.client_id,
            "scope": None,
            "openid": None,
        }

    async def _build_online_dto(self, user, session_info: dict, client, token: str) -> dict:
        """在线用户信息（字段名为驼峰格式）。"""
        from ua_parser import parse as parse_ua

        ip = get_client_ip(self.request)
        ua = parse_ua(self.request.headers.get("User-Agent", ""))
        browser = ua.user_agent.family if ua.user_agent else ""
        os_name = ua.os.family if ua.os else ""
        return {
            "tokenId": token,
            "userName": user.user_name,
            "deptName": session_info.get("dept_name") or "",
            "ipaddr": ip,
            "loginLocation": get_real_address_by_ip(ip),
            "browser": browser,
            "os": os_name,
            "loginTime": int(datetime.now().timestamp() * 1000),
            "clientKey": client.client_key,
            "deviceType": client.device_type,
        }

    async def record_login_info(self, user_id: int, ip: str | None) -> None:
        """更新最后登录信息。"""
        from app.api.v1.module_system.user.model import UserModel

        user = await self.db.get(UserModel, user_id)
        if user is not None:
            user.login_ip = ip
            user.login_date = datetime.now()
            user.update_by = user_id
            await self.db.flush()

    # ==================== 登出 ====================

    async def logout(self) -> None:
        """退出登录（清理会话与在线记录，并记录登出日志）。"""
        authorization = self.request.headers.get(settings.TOKEN_NAME, "")
        token = authorization.split(" ", 1)[1].strip() if " " in authorization else authorization
        username = None
        if token:
            try:
                payload = decode_access_token(token, verify_exp=False)
                session_id = payload.sub
                username = payload.user_name
                raw = await self.redis_util.get(f"user_session:{session_id}")
                if raw:
                    username = json.loads(raw).get("user_name") or username
                await self.redis_util.delete(f"user_session:{session_id}", f"access_token:{session_id}")
            except NotLoginException:
                pass
            except Exception:
                logger.debug("logout 解析 token 失败，忽略", exc_info=True)
            await self.redis_util.delete(f"{CacheNames.ONLINE_TOKEN_KEY}{token}")
        if username:
            await self.record_logininfor(username, Constants.LOGOUT, MessageUtils.message("user.logout.success"))

    # ==================== 注册 ====================

    async def register(self, body: RegisterBodySchema) -> None:
        """用户注册。"""
        from app.api.v1.module_system.user.model import UserModel

        username, password = body.username, body.password
        user_type = UserType.get_user_type(body.user_type or UserType.SYS_USER.value).value

        if settings.CAPTCHA_ENABLE:
            await self.validate_captcha(username, body.code, body.uuid)

        stmt = select(func.count()).select_from(UserModel).where(UserModel.user_name == username, UserModel.del_flag == SystemConstants.NORMAL)
        if ((await self.db.execute(stmt)).scalar() or 0) > 0:
            raise ServiceException.of(AuthErrorCode.USER_REGISTER_EXISTS, username)

        new_user = UserModel(
            id=IdGeneratorUtil.next_long_id(),
            user_name=username,
            nick_name=username,
            password=bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8"),
            user_type=user_type,
            create_by=-1,
            update_by=-1,
        )
        self.db.add(new_user)
        await self.db.flush()
        await self.record_logininfor(username, Constants.REGISTER, MessageUtils.message("user.register.success"))

    # ==================== 验证码 ====================

    async def get_captcha(self) -> dict:
        """生成图形验证码。"""
        if not settings.CAPTCHA_ENABLE:
            return CaptchaOutSchema(captcha_enabled=False).model_dump(by_alias=True)

        uuid_str = uuid.uuid4().hex
        if settings.CAPTCHA_TYPE == "math":
            text, answer, img = captcha_gen.generate_math(settings.CAPTCHA_NUMBER_LENGTH)
        else:
            text, answer, img = captcha_gen.generate_char(settings.CAPTCHA_CHAR_LENGTH)
        await self.redis_util.set(CacheNames.CAPTCHA_CODE_KEY + uuid_str, answer, expire=settings.CAPTCHA_EXPIRE_SECONDS)
        return CaptchaOutSchema(captcha_enabled=True, uuid=uuid_str, img=img).model_dump(by_alias=True)

    # ==================== 登录日志 ====================

    async def record_logininfor(self, username: str, status: str, message: str) -> None:
        """记录登录信息（写入 sys_logininfor 登录日志表）。"""
        try:
            from app.api.v1.module_system.log.service import record_login_infor

            await record_login_infor(self.request, username, status, message)
        except ImportError:
            logger.warning("登录日志模块未就绪，跳过记录: {} {}", username, message)
        except Exception:
            logger.exception("登录日志记录失败: {}", username)
