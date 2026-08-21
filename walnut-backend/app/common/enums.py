from enum import Enum, IntEnum, unique


@unique
class EnvironmentEnum(str, Enum):
    """应用运行环境（开发 / 生产）。"""

    DEV = "dev"
    PROD = "prod"


class HttpStatus(IntEnum):
    """业务状态码（写入响应体 code 字段）。

    与 HTTP 传输状态码相互独立：业务异常几乎都返回 HTTP 200，
    真实结果通过 body.code 表达，前端依据 code 判断（401 时跳转登录）。
    """

    SUCCESS = 200
    CREATED = 201
    ACCEPTED = 202
    NO_CONTENT = 204
    MOVED_PERM = 301
    SEE_OTHER = 303
    NOT_MODIFIED = 304
    BAD_REQUEST = 400
    UNAUTHORIZED = 401
    FORBIDDEN = 403
    NOT_FOUND = 404
    BAD_METHOD = 405
    CONFLICT = 409
    UNSUPPORTED_TYPE = 415
    ERROR = 500
    NOT_IMPLEMENTED = 501
    WARN = 601


@unique
class BusinessType(IntEnum):
    """业务操作类型（ordinal 值入库）。"""

    OTHER = 0
    INSERT = 1
    UPDATE = 2
    DELETE = 3
    GRANT = 4
    EXPORT = 5
    IMPORT = 6
    FORCE = 7
    GENCODE = 8
    CLEAN = 9


@unique
class OperatorType(IntEnum):
    """操作者类型。"""

    OTHER = 0
    MANAGE = 1
    MOBILE = 2


@unique
class BusinessStatus(IntEnum):
    """操作状态。"""

    SUCCESS = 0
    FAIL = 1


@unique
class UserType(str, Enum):
    """用户类型。"""

    SYS_USER = "sys_user"
    APP_USER = "app_user"

    @classmethod
    def get_user_type(cls, value: str) -> "UserType":
        for item in cls:
            if item.value in (value or ""):
                return item
        raise ValueError(f"'UserType' not found By {value}")


@unique
class LoginType(str, Enum):
    """登录类型（携带 i18n 重试提示键）。"""

    PASSWORD = "password"
    SMS = "sms"
    EMAIL = "email"
    XCX = "xcx"

    @property
    def retry_limit_key(self) -> str:
        return {
            LoginType.PASSWORD: "user.password.retry.limit.exceed",
            LoginType.SMS: "sms.code.retry.limit.exceed",
            LoginType.EMAIL: "email.code.retry.limit.exceed",
            LoginType.XCX: "",
        }[self]


class DataBaseType(str, Enum):
    """数据库类型。"""

    MY_SQL = "MySQL"

    @classmethod
    def detect(cls, product_name: str | None) -> "DataBaseType":
        return cls.MY_SQL


class DataScopeType(str, Enum):
    """角色数据范围（值与角色表 data_scope 字段一致）。"""

    ALL = "1"
    CUSTOM = "2"
    DEPT = "3"
    DEPT_AND_CHILD = "4"
    SELF = "5"
    DEPT_AND_CHILD_OR_SELF = "6"

    @classmethod
    def find_code(cls, code: str | None) -> "DataScopeType | None":
        for item in cls:
            if item.value == code:
                return item
        return None


# ==================== Redis 键名 / 缓存名 ====================


class CacheNames:
    """Redis 键前缀与缓存名。"""

    # Redis key prefixes
    GLOBAL_REDIS_KEY = "global:"
    ONLINE_TOKEN_KEY = "online_tokens:"
    SYS_CONFIG_KEY = "sys_config:"
    SYS_DICT_KEY = "sys_dict:"
    PWD_ERR_CNT_KEY = "pwd_err_cnt:"
    CAPTCHA_CODE_KEY = "global:captcha_codes:"
    REPEAT_SUBMIT_KEY = "global:repeat_submit:"
    RATE_LIMIT_KEY = "global:rate_limit:"
    SOCIAL_AUTH_CODE_KEY = "global:social_auth_codes:"

    # pub/sub topics
    SSE_TOPIC = "global:sse"
    WEB_SOCKET_TOPIC = "global:websocket"

    # Redis 缓存组名格式：name#ttl#maxIdleTime#maxSize
    DEMO_CACHE = "demo:cache#60s#10m#20"
    SYS_CONFIG = "sys_config"
    SYS_DICT = "sys_dict"
    SYS_DICT_TYPE = "sys_dict_type"
    SYS_CLIENT = "global:sys_client#30d"
    SYS_USER_NAME = "sys_user_name#30d"
    SYS_NICKNAME = "sys_nickname#30d"
    SYS_DEPT = "sys_dept#30d"
    SYS_ROLE_CUSTOM = "sys_role_custom#30d"
    SYS_DEPT_AND_CHILD = "sys_dept_and_child#30d"
    ONLINE_TOKEN = "online_tokens"


@unique
class RedisInitKeyConfig(Enum):
    """系统内置 Redis 键名枚举（认证/会话相关）。"""

    ACCESS_TOKEN = {"key": "access_token", "remark": "登录令牌信息"}
    REFRESH_TOKEN = {"key": "refresh_token", "remark": "刷新令牌信息"}
    USER_SESSION = {"key": "user_session", "remark": "用户会话信息"}
    CAPTCHA_CODES = {"key": "captcha_codes", "remark": "图片验证码"}
    SYSTEM_CONFIG = {"key": "sys_config", "remark": "系统配置"}
    SYSTEM_DICT = {"key": "sys_dict", "remark": "数据字典"}
    PWD_ERR_CNT = {"key": "pwd_err_cnt", "remark": "密码错误次数"}
    REPEAT_SUBMIT = {"key": "global:repeat_submit", "remark": "防重提交"}
    RATE_LIMIT = {"key": "global:rate_limit", "remark": "接口限流"}

    @property
    def key(self) -> str:
        return self.value.get("key", "")

    @property
    def remark(self) -> str:
        return self.value.get("remark", "")
