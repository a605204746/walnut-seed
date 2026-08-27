"""通用常量。"""


class Constants:
    """通用常量。"""

    UTF8 = "UTF-8"
    GBK = "GBK"
    WWW = "www."
    HTTP = "http://"
    HTTPS = "https://"
    SUCCESS = "0"
    FAIL = "1"
    LOGIN_SUCCESS = "Success"
    LOGIN_FAIL = "Error"
    LOGOUT = "Logout"
    REGISTER = "Register"
    CAPTCHA_EXPIRATION = 2  # 分钟
    TOP_PARENT_ID = 0
    ENCRYPT_HEADER = "ENC_"


class SystemConstants:
    """系统常量。"""

    NORMAL = "0"
    DISABLE = "1"
    YES = "Y"
    NO = "N"
    YES_FRAME = "0"
    NO_FRAME = "1"
    # 菜单类型
    TYPE_DIR = "M"
    TYPE_MENU = "C"
    TYPE_BUTTON = "F"
    LAYOUT = "Layout"
    PARENT_VIEW = "ParentView"
    INNER_LINK = "InnerLink"
    # 角色
    SUPER_ADMIN_ROLE_KEY = "superadmin"
    ADMIN_ROLE_KEY = "admin"
    SUPER_ADMIN_ID = 1
    # 部门
    ROOT_DEPT_ANCESTORS = "0"
    DEFAULT_DEPT_ID = 100
    # 日志脱敏需剔除的字段
    EXCLUDE_PROPERTIES = {"password", "oldPassword", "newPassword", "confirmPassword"}


class RegexConstants:
    """正则常量。"""

    DICTIONARY_TYPE = r"^[a-z][a-z0-9_]*$"
    PERMISSION_STRING = r"^$|^[a-zA-Z0-9_]+:[a-zA-Z0-9_*]+:[a-zA-Z0-9_*]+$"
    ID_CARD_LAST_6 = r"^(([0-2][1-9])|10|20|30|31)\d{3}[0-9Xx]$"
    QQ_NUMBER = r"^[1-9][0-9]\d{4,9}$"
    POSTAL_CODE = r"^[1-9]\d{5}$"
    ACCOUNT = r"^[a-zA-Z][a-zA-Z0-9_]{4,15}$"
    PASSWORD = r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$"
    STATUS = r"^[01]$"
    MOBILE = r"^1(3\d|4[4-9]|5[0-35-9]|6[67]|7[013-8]|8[0-9]|9[0-9])\d{8}$"
    EMAIL = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"


# API 日期 / 时间 / 日期时间统一展示格式
DATE_DISPLAY_FMT = "%Y-%m-%d"
TIME_DISPLAY_FMT = "%H:%M:%S"
DATETIME_DISPLAY_FMT = "%Y-%m-%d %H:%M:%S"
