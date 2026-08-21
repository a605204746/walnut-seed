import os
from functools import lru_cache
from typing import Any, Literal
from urllib.parse import quote_plus

from pydantic_settings import BaseSettings, SettingsConfigDict

from app.common.enums import EnvironmentEnum
from app.config.path_conf import ENV_DIR


class Settings(BaseSettings):
    """系统配置类（按运行环境加载 .env 文件中的配置项）。"""

    model_config = SettingsConfigDict(
        env_file=ENV_DIR / f".env.{os.getenv('ENVIRONMENT', 'dev')}",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True,  # 区分大小写
    )

    # ================================================= #
    # ******************* 项目环境 ******************* #
    # ================================================= #
    ENVIRONMENT: EnvironmentEnum = EnvironmentEnum.DEV

    # ================================================= #
    # ******************* 服务器配置 ****************** #
    # ================================================= #
    SERVER_HOST: str = "0.0.0.0"  # 允许访问的IP地址
    SERVER_PORT: int = 8011  # 服务端口

    # ================================================= #
    # ******************* API文档配置 ****************** #
    # ================================================= #
    DEBUG: bool = True  # 调试模式
    TITLE: str = "WalnutSeed 接口文档"  # 文档标题
    VERSION: str = "1.0.0"  # 版本号
    DESCRIPTION: str = "WalnutSeed 现代化全栈应用脚手架接口文档"  # 文档描述
    SUMMARY: str = "接口汇总"  # 文档概述
    DOCS_URL: str = "/docs"  # Swagger UI路径
    REDOC_URL: str = "/redoc"  # ReDoc路径
    # 路由前缀默认空串：前端代理会剥离 /api 前缀，
    # 路由保持 /auth/login、/system/...、/resource/sse 形式。
    ROOT_PATH: str = ""

    # ================================================= #
    # ******************** 日志配置 ******************** #
    # ================================================= #
    LOGGER_LEVEL: str = "DEBUG"  # 日志级别
    OPERATION_RECORD_METHOD: list[str] = ["POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"]  # 需要记录操作日志的请求方法

    # ================================================= #
    # ******************** 跨域配置 ******************** #
    # ================================================= #
    # CORS 策略：允许携带凭证、来源通配、预检缓存 1800 秒
    PROD_CORS_ORIGINS: str = ""  # 生产环境允许的域名列表，逗号分隔
    ALLOW_METHODS: list[str] = ["*"]
    ALLOW_HEADERS: list[str] = ["*"]
    ALLOW_CREDENTIALS: bool = True
    CORS_MAX_AGE: int = 1800
    CORS_EXPOSE_HEADERS: list[str] = ["X-Request-ID", "encrypt-key", "Content-Disposition", "download-filename"]
    # 生产环境是否强制 HTTP → HTTPS 重定向（真实 TLS 部署显式开启；docker-compose 等 HTTP 直连保持默认）
    HTTPS_REDIRECT: bool = False

    # ================================================= #
    # ******************* 登录认证配置 ****************** #
    # ================================================= #
    # 登录认证：token 通过 Authorization 请求头携带、Bearer 前缀、JWT 签名
    SECRET_KEY: str = "walnut-seed-change-me-32-bytes-min-jwt-secret-0123456789"  # JWT 签名密钥（≥32 字节，生产务必更换；prod 含 change-me/过短/为空直接拒绝启动）
    ALGORITHM: str = "HS256"  # JWT 算法
    TOKEN_NAME: str = "Authorization"  # 携带 token 的请求头
    TOKEN_PREFIX: str = "Bearer"  # token 前缀
    ACCESS_TOKEN_EXPIRE_SECONDS: int = 60 * 60 * 24 * 30  # token 超时（默认 30 天）
    TOKEN_SLIDING_EXPIRE: bool = True  # 是否启用滑动过期
    CLIENT_ID_HEADER: str = "clientid"  # 客户端ID请求头（校验与 token 内 clientid 一致）
    # 无需认证即可访问的接口白名单（支持 * 结尾前缀匹配）。
    # 启动路由审计（init_app.audit_routes_auth）以此为准：白名单外的路由必须携带认证依赖。
    WHITE_API_LIST_PATH: list[str] = [
        "/",  # 首页提示（仅欢迎文案）
        "/auth/login",
        "/auth/logout",  # 登出幂等，允许未登录调用（无效 token 静默忽略）
        "/auth/register",
        "/auth/code",
        "/auth/tenant/list",
        "/resource/sse/close",
        "/resource/websocket",  # WebSocket 端点内自行认证（token 校验失败即断开）
        "/common/health",
        "/common/health/*",
        "/upload/*",  # 上传文件内联访问（img 标签无法携带 token），响应强制 nosniff+attachment
        "/static*",  # 静态资源（Swagger UI 资源等）
        "/web*",  # SPA 前端静态托管
        "/docs*",  # Swagger UI（含 /docs/oauth2-redirect）
        "/redoc",
        "/openapi.json",
        "/favicon.ico",
    ]
    # 可信代理 IP 列表：仅当请求直连地址（对端地址）在此列表中时，
    # 才解析 X-Forwarded-For / X-Real-IP 等代理头；否则一律返回对端地址（防 IP 伪造）。
    TRUSTED_PROXY_IPS: list[str] = []
    # 安全放行路径（静态资源与接口文档，不经过认证）
    SECURITY_EXCLUDES: list[str] = [
        "/*.html",
        "/**/*.html",
        "/**/*.css",
        "/**/*.js",
        "/favicon.ico",
        "/error",
        "/*/api-docs",
        "/*/api-docs/**",
    ]

    # ================================================= #
    # ******************* 用户密码策略 ****************** #
    # ================================================= #
    PASSWORD_MAX_RETRY_COUNT: int = 5  # 密码最大重试次数
    PASSWORD_LOCK_TIME: int = 10  # 锁定时间（分钟）
    # 导入用户时的初始密码（sys_config 的 sys.user.initPassword 缺失时的回退值）。
    # 必须满足密码复杂度规则（大小写字母+数字+特殊字符，见 RegexConstants.PASSWORD）。
    USER_IMPORT_INIT_PASSWORD: str = "Walnut@123"

    # ================================================= #
    # ******************* 雪花ID配置 ****************** #
    # ================================================= #
    # 雪花算法机器位（0-1023）。多 worker/多副本部署必须显式配置且各实例互不相同；
    # 未配置时回退「本机 IP + 进程号」派生（启动时告警提示）。
    SNOWFLAKE_WORKER_ID: int | None = None

    # ================================================= #
    # ******************** 验证码配置 ******************* #
    # ================================================= #
    CAPTCHA_ENABLE: bool = True
    CAPTCHA_TYPE: str = "math"  # math | char
    CAPTCHA_NUMBER_LENGTH: int = 2  # math 模式运算数位数（1 位答案空间仅 19 种，2 位起才可防暴力猜解）
    CAPTCHA_CHAR_LENGTH: int = 4
    CAPTCHA_EXPIRE_SECONDS: int = 120  # 验证码有效期（2 分钟）

    # ================================================= #
    # ******************** 数据库配置 ******************* #
    # ================================================= #
    # SQL 日志：True=打印参数填充后的完整 SQL；debug=额外开启 SQLAlchemy 原生 echo；生产建议 False
    DATABASE_ECHO: bool | Literal["debug"] = True
    ECHO_POOL: bool | Literal["debug"] = False
    POOL_SIZE: int = 10
    MAX_OVERFLOW: int = 20
    POOL_TIMEOUT: int = 30
    POOL_RECYCLE: int = 1800
    POOL_PRE_PING: bool = True
    AUTOCOMMIT: bool = False
    AUTOFLUSH: bool = False
    EXPIRE_ON_COMMIT: bool = False

    # 数据库类型，开发默认 mysql
    DATABASE_TYPE: Literal["mysql"] = "mysql"
    DATABASE_HOST: str = "localhost"
    DATABASE_PORT: int = 3306
    DATABASE_USER: str = "root"
    DATABASE_PASSWORD: str = ""
    DATABASE_NAME: str = "walnut_seed_fastapi"
    # 启动时自动执行 Alembic 迁移（upgrade head）：dev 在 .env.dev 置 True；
    # prod 保持 False，由 docker-entrypoint 在应用启动前显式迁移（多副本部署无竞争）
    DATABASE_AUTO_MIGRATE: bool = False

    # ================================================= #
    # ******************** Redis配置 ******************* #
    # ================================================= #
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB_NAME: int = 0
    REDIS_USER: str = ""
    REDIS_PASSWORD: str = ""
    REDIS_KEY_PREFIX: str = ""  # Redis 键前缀（开发为空）
    REDIS_HEALTH_CHECK_INTERVAL: int = 20
    REDIS_DEFAULT_CACHE_TTL: int = 86400

    # ================================================= #
    # ******************** XSS配置 ******************** #
    # ================================================= #
    XSS_ENABLED: bool = True
    XSS_EXCLUDE_URLS: list[str] = ["/system/notice"]

    # ================================================= #
    # ******************* 接口加解密配置 ****************** #
    # ================================================= #
    # 接口加解密（RSA+AES 请求/响应体）
    API_DECRYPT_ENABLED: bool = True
    API_DECRYPT_HEADER_FLAG: str = "encrypt-key"
    # RSA 密钥对（base64 DER：公钥 SubjectPublicKeyInfo / 私钥 PKCS8）。
    # 默认留空：启动校验发现为空或无效时自动停用接口加解密（安全降级为明文）。
    # 严禁内置任何公开已知密钥（如 RuoYi 出厂密钥对）；用 scripts/gen_rsa_keys.py 生成。
    API_DECRYPT_PUBLIC_KEY: str = ""
    API_DECRYPT_PRIVATE_KEY: str = ""

    # ================================================= #
    # ******************* 字段加密配置 ****************** #
    # ================================================= #
    # 字段入库加解密（默认关闭）
    FIELD_ENCRYPT_ENABLED: bool = False
    FIELD_ENCRYPT_ALGORITHM: str = "BASE64"
    FIELD_ENCRYPT_ENCODE: str = "BASE64"
    FIELD_ENCRYPT_PASSWORD: str = ""
    FIELD_ENCRYPT_PUBLIC_KEY: str = ""
    FIELD_ENCRYPT_PRIVATE_KEY: str = ""

    # ================================================= #
    # ******************** SSE配置 ******************** #
    # ================================================= #
    SSE_ENABLED: bool = True
    SSE_PATH: str = "/resource/sse"

    # ================================================= #
    # ******************* WebSocket配置 ****************** #
    # ================================================= #
    WEBSOCKET_ENABLED: bool = False
    WEBSOCKET_PATH: str = "/resource/websocket"
    WEBSOCKET_ALLOWED_ORIGINS: str = "*"

    # ================================================= #
    # ******************** OSS配置 ******************** #
    # ================================================= #
    OSS_TYPE: Literal["s3", "aliyun"] = "s3"
    # 任意 S3 兼容对象存储（默认编排为 SeaweedFS）：endpoint 为 host:port，不带协议
    OSS_S3_ENDPOINT: str = "localhost:8333"
    OSS_S3_ACCESS_KEY: str = "walnut"
    OSS_S3_SECRET_KEY: str = "walnut123"
    OSS_S3_BUCKET_NAME: str = "walnut-seed"
    OSS_S3_SECURE: bool = False
    # 上传返回 url 的前缀：统一中性路径 /upload/{key}，跨环境可渲染
    # （本机 dev 由 vite 代理 /upload → 后端；docker 由 nginx 转发 /upload/ → 后端）
    OSS_S3_URL_PREFIX: str = "/upload"
    OSS_ALIYUN_ENDPOINT: str = ""
    OSS_ALIYUN_ACCESS_KEY_ID: str = ""
    OSS_ALIYUN_ACCESS_KEY_SECRET: str = ""
    OSS_ALIYUN_BUCKET_NAME: str = ""
    OSS_ALIYUN_URL_PREFIX: str = ""

    # ================================================= #
    # ******************* Gzip压缩配置 ******************* #
    # ================================================= #
    GZIP_MIN_SIZE: int = 1000
    GZIP_COMPRESS_LEVEL: int = 9

    # ================================================= #
    # ******************* 安全中间件配置 ****************** #
    # ================================================= #
    ALLOWED_HOSTS: list[str] = ["*"]
    OPERATION_LOG_RETENTION_DAYS: int = 90

    # ================================================= #
    # ***************** 静态/上传文件配置 ***************** #
    # ================================================= #
    STATIC_URL: str = "/static"
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB（上传分块累计计数，超限即中止）
    MAX_REQUEST_SIZE: int = 20 * 1024 * 1024  # 20MB
    # 允许上传的扩展名白名单（安全集）。禁止 html/htm/svg 等可执行脚本/标记类文件（存储型 XSS 面）。
    ALLOWED_EXTENSIONS: list[str] = [
        "jpg",
        "jpeg",
        "png",
        "gif",
        "bmp",
        "webp",
        "doc",
        "docx",
        "xls",
        "xlsx",
        "ppt",
        "pptx",
        "pdf",
        "txt",
        "zip",
        "rar",
        "7z",
    ]

    # ================================================= #
    # ***************** Swagger配置 ***************** #
    # ================================================= #
    SWAGGER_CSS_URL: str = "static/swagger/swagger-ui/swagger-ui.css"
    SWAGGER_JS_URL: str = "static/swagger/swagger-ui/swagger-ui-bundle.js"
    REDOC_JS_URL: str = "static/swagger/redoc/bundles/redoc.standalone.js"
    FAVICON_URL: str = "static/image/favicon.ico"

    # ================================================= #
    # ******************* 动态配置 ******************* #
    # ================================================= #
    @property
    def ALLOW_ORIGINS(self) -> list[str]:
        """根据环境动态返回 CORS 允许的域名列表。"""
        if self.ENVIRONMENT == EnvironmentEnum.PROD and self.PROD_CORS_ORIGINS:
            return [origin.strip() for origin in self.PROD_CORS_ORIGINS.split(",") if origin.strip()]
        return ["*"]

    @property
    def REDIS_URI(self) -> str:
        """构建 Redis 连接 URI。"""
        auth_part = ""
        if self.REDIS_USER and self.REDIS_PASSWORD:
            auth_part = f"{self.REDIS_USER}:{self.REDIS_PASSWORD}@"
        elif self.REDIS_PASSWORD:
            auth_part = f":{self.REDIS_PASSWORD}@"
        return f"redis://{auth_part}{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB_NAME}"

    @property
    def MIDDLEWARE_LIST(self) -> list[str | None]:
        # 中间件列表（注册时逆序叠加：下列第一项最终位于最外层，优先生效）
        # 执行顺序（从外到内）：
        #   HTTPSRedirect → TrustedHost → CORS → Locale → ApiDecrypt → XSS → RequestLog → GZip → CorrelationId → 业务路由
        MIDDLEWARES: list[str | None] = [
            "app.core.middlewares.CustomHTTPSRedirectMiddleware" if self.ENVIRONMENT == EnvironmentEnum.PROD and self.HTTPS_REDIRECT else None,
            "app.core.middlewares.CustomTrustedHostMiddleware" if self.ENVIRONMENT == EnvironmentEnum.PROD else None,
            "app.core.middlewares.CustomCORSMiddleware",
            "app.core.middlewares.LocaleMiddleware",
            "app.core.middlewares.ApiDecryptMiddleware" if self.API_DECRYPT_ENABLED else None,
            "app.core.middlewares.XssMiddleware" if self.XSS_ENABLED else None,
            "app.core.middlewares.RequestLogMiddleware",
            "app.core.middlewares.CustomGZipMiddleware",
            "app.core.middlewares.CorrelationIdMiddleware",
        ]
        return MIDDLEWARES

    @property
    def ASYNC_DB_URI(self) -> str:
        return f"mysql+aiomysql://{self.DATABASE_USER}:{quote_plus(self.DATABASE_PASSWORD)}@{self.DATABASE_HOST}:{self.DATABASE_PORT}/{self.DATABASE_NAME}?charset=utf8mb4"

    @property
    def DB_URI(self) -> str:
        return f"mysql+pymysql://{self.DATABASE_USER}:{quote_plus(self.DATABASE_PASSWORD)}@{self.DATABASE_HOST}:{self.DATABASE_PORT}/{self.DATABASE_NAME}?charset=utf8mb4"

    @property
    def FASTAPI_CONFIG(self) -> dict[str, Any]:
        return {
            "debug": self.DEBUG,
            "title": self.TITLE,
            "version": self.VERSION,
            "description": self.DESCRIPTION,
            "summary": self.SUMMARY,
            "docs_url": None,
            "redoc_url": None,
            "root_path": self.ROOT_PATH,
            "responses": {
                200: {"description": "成功"},
                400: {"description": "请求参数错误"},
                401: {"description": "未认证"},
                403: {"description": "未授权"},
                404: {"description": "资源不存在"},
                422: {"description": "请求参数验证错误"},
                500: {"description": "服务器内部错误"},
            },
        }


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    # 显式传 _env_file：model_config 的 env_file 在类定义时即固化，
    # 之后修改 ENVIRONMENT 环境变量不会改变它；实例化参数始终优先。
    # 文件不存在时 pydantic-settings 静默忽略（prod 镜像不含 env/ 目录，配置全走环境变量）。
    return Settings(_env_file=ENV_DIR / f".env.{os.getenv('ENVIRONMENT', 'dev')}")  # pyright: ignore[reportCallIssue]


def reload_settings() -> Settings:
    """清空缓存并按当前 ENVIRONMENT 重建配置（CLI 切换 --env 后调用）。"""
    get_settings.cache_clear()
    return get_settings()


settings = get_settings()
