"""认证模块错误码。"""

from enum import IntEnum, unique


@unique
class AuthErrorCode(IntEnum):
    """认证模块错误码（10000–19999 段，携带 i18n 消息键）。"""

    CAPTCHA_EXPIRED = 10001
    CAPTCHA_ERROR = 10002
    USER_NOT_EXISTS = 10003
    USER_BLOCKED = 10004
    # 用户不存在与密码错误统一为该码与文案（防用户枚举）
    USER_PASSWORD_NOT_MATCH = 10005
    USER_PASSWORD_RETRY_LIMIT_EXCEED = 10006
    USER_REGISTER_FAILED = 10007
    USER_REGISTER_EXISTS = 10008

    @property
    def key(self) -> str:
        return {
            AuthErrorCode.CAPTCHA_EXPIRED: "user.jcaptcha.expire",
            AuthErrorCode.CAPTCHA_ERROR: "user.jcaptcha.error",
            AuthErrorCode.USER_NOT_EXISTS: "user.not.exists",
            AuthErrorCode.USER_BLOCKED: "user.blocked",
            AuthErrorCode.USER_PASSWORD_NOT_MATCH: "user.password.not.match",
            AuthErrorCode.USER_PASSWORD_RETRY_LIMIT_EXCEED: "user.password.retry.limit.exceed",
            AuthErrorCode.USER_REGISTER_FAILED: "user.register.error",
            AuthErrorCode.USER_REGISTER_EXISTS: "user.register.save.error",
        }[self]
