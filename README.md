# Walnut-Seed-Fastapi

[English](./README.en.md) | **简体中文**

现代化全栈应用脚手架：FastAPI（Python 3.12）后端 + Vue3（vben/antdv-next）前端，开箱即用地构建管理类系统。

## 特性

内置基础设施，直接支撑真实的管理类业务：

- **统一响应信封** —— 全部接口统一返回 `{"code", "msg", "data"}`
- **认证与授权** —— JWT 登录、RBAC 菜单/按钮权限、行级数据权限（fail-closed）
- **默认加固** —— 限流、防重提交（幂等）、接口加解密（RSA + AES）、XSS 过滤
- **缓存与异步原语** —— Redis 缓存/CRUD 辅助、SSE 与 WebSocket 支持
- **文件存储（OSS）** —— 任意 S3 兼容对象存储（默认 SeaweedFS），可切阿里云 OSS
- **i18n** —— 按请求头 `Accept-Language` 自动生效（zh_CN/en_US，业务消息逐步迁移中）
- **数据库迁移** —— Alembic 作为 Schema 唯一事实来源（不再使用启动时 `create_all`）
- **种子数据** —— 完整后台基线：user / role / menu / dept / post / dict / config / notice / client / social / log
- **运维友好** —— 健康/存活/就绪探针、Loguru 结构化日志、Typer CLI、全端点冒烟脚本

## 技术栈

| 端 | 技术 |
| --- | --- |
| 后端 | Python 3.12、FastAPI 0.138、SQLAlchemy 2.0（async）、Alembic、Redis（redis.asyncio）、PyJWT、Loguru、Typer/Uvicorn；依赖管理 uv；接口加解密 cryptography（RSA + AES），可选国密 gmssl |
| 前端 | Vue 3.5、Vben 5.7.0、antdv-next 1.3.0（替代已停止维护的 ant-design-vue）；pnpm 11.2.2 + turbo monorepo；Node.js `^22.18.0 \|\| ^24.0.0` |
| 存储 | MySQL 8（数据库仅支持 MySQL）、Redis 7、SeaweedFS（S3 兼容对象存储，可切阿里云 OSS） |

## 文档

详细教程与设计说明位于 [`docs/`](./docs/README.md)：

- **[从零新增一个业务模块](./docs/guide/new-crud-module.md)** —— 端到端开发教程（五件套 → 迁移 → 菜单权限 → 前端页面）
- 开发指南：菜单与权限、Alembic 迁移、接口加解密、i18n
- 架构说明与部署运维手册

在本脚手架上做二次开发，建议从这里开始。

## 目录结构

```
walnut-seed-fastapi/
  walnut-backend/    # Python 后端（FastAPI + SQLAlchemy 2.0 异步 + Redis）
  walnut-frontend/   # Vue3 前端 monorepo（pnpm + turbo），主应用位于 apps/web-antd/
  docker/            # compose 编排与容器配置
  data/              # 运行时产物（不入 git，自动创建）：logs/、upload/
```

### 后端结构

```
walnut-backend/
  main.py                  # typer CLI（run/revision/upgrade/downgrade/stamp/current/history）+ create_app
  pyproject.toml           # uv 依赖与工具配置
  alembic.ini              # 数据库迁移配置
  docker-entrypoint.sh     # 容器启动入口：先 alembic upgrade 再启动应用
  banner.txt               # 启动 Banner
  env/                     # .env.dev / .env.example 环境配置
  app/
    init_app.py            # lifespan + register_*
    config/                # setting.py / path_conf.py
    common/                # constant / enums / response / request / dataclasses
    core/                  # 基础设施：database / migrate / redis_crud / security / dependencies /
                           # permission / middlewares / exceptions / logger / base_model /
                           # base_schema / base_crud / router_class / validator / idempotent /
                           # rate_limiter / sse / websocket / file_storage / encrypt
    utils/                 # 工具：common / string / date / ip / xss / sql / import /
                           # excel / snowflake / i18n / banner
    api/v1/                # 业务模块（module_*）
                           #   module_system：user/role/menu/dept/post/dict/config/notice/client/social/log
                           #   module_web：auth/captcha/register
                           #   module_common：health / file
                           #   module_resource：SSE / WebSocket
    seed/                  # 种子数据（initialize.py + sql/）
    i18n/                  # messages_zh_CN / messages_en_US
    alembic/               # env.py / script.py.mako / versions/（迁移脚本）
  static/                  # swagger-ui / redoc / image
  scripts/                 # 开发脚本（smoke_all.py 全端点冒烟、密钥生成器）
  tests/                   # pytest
```

`app/api/v1/module_*` 下的业务子模块统一按五件套组织：

| 文件 | 职责 |
|---|---|
| `controller.py` | 路由定义与入参校验入口 |
| `service.py` | 业务逻辑编排 |
| `crud.py` | 数据访问层（基于 `app/core/base_crud.py`） |
| `model.py` | SQLAlchemy ORM 模型 |
| `schema.py` | Pydantic 请求/响应模型 |

日志统一写入仓库根目录 `data/logs/`（walnut-seed.log，按天轮转，保留 30 天）。

## 快速开始

```bash
git clone https://gitee.com/shendudian/walnut-seed-fastapi.git
cd walnut-seed-fastapi
```

前置：Docker Desktop（含 compose）；本机原生开发另需 `uv`（Python 3.12）、Node.js `^22.18.0 || ^24.0.0` 与 pnpm 11。

### 方式一：仅中间件 + 本机应用（日常开发推荐）

中间件（MySQL/Redis/SeaweedFS）跑在 Docker，后端/前端在本机原生运行（热重载最流畅、好调试）。

先启动中间件（MySQL localhost:3307，root/walnut123，库 walnut_seed_fastapi；Redis localhost:6380；SeaweedFS S3 API localhost:8333，filer UI `http://localhost:8888`）：

```bash
docker compose -f docker/docker-compose.middleware.yml up -d
```

然后启动应用：

```bash
# 后端
cd walnut-backend
uv sync
uv run main.py run --env dev   # http://localhost:8011

# 前端（新终端）
cd walnut-frontend
pnpm install
pnpm dev:antd                  # http://localhost:8010
```

连接信息在 `walnut-backend/env/.env.dev`，已指向 Docker 中间件。前端 dev server 默认运行于 `http://localhost:8010`，将 `/api` 代理到 `http://localhost:8011`。

### 方式二：生产/全栈

```bash
cp docker/.env.example docker/.env    # 然后设置 JWT_SECRET_KEY（必填，见下）
docker compose -f docker/docker-compose.yml up -d --build
```

启动后访问 `http://localhost:8010`，初始账号 `admin / admin123`（**生产使用前必须改密**）。

包含 MySQL 8 + Redis 7 + 后端 + 前端(nginx)；启动时后端容器先执行 Alembic 迁移（upgrade head）再写入种子数据。全部服务带 restart 策略与健康检查，后端容器以非 root 用户运行；`JWT_SECRET_KEY` 必须在 `docker/.env` 提供（编排以 `:?` 强制，缺失或为空直接启动失败）。

> 两套编排经 `include` 共用中间件定义且端口互斥，**不能同时运行**。停止均为对应的 `docker compose -f <文件> down`；中间件数据保留在 `docker/volumes`（全栈与中间件共用），删除该目录即清空重来；全栈编排的后端运行数据（日志等）使用具名卷 `backend-data`（`down` 保留，`down -v` 删除）。中间件编排使用非默认端口（MySQL 3307 / Redis 6380），一般不与宿主机自装的 MySQL/Redis（3306/6379）冲突。

### 常用开发命令

后端（在 `walnut-backend/` 下）：

```bash
uv sync                                     # 安装依赖（含 dev）
cp env/.env.example env/.env.dev            # 首次：拷贝环境配置（默认已提供 MySQL + 本地 Redis）
uv run main.py run --env dev                # 启动（裸跑 uv run main.py 等价于此命令，默认 dev；DATABASE_AUTO_MIGRATE=True 时启动自动迁移）
uv run pytest                               # 测试
uv run python -m scripts.smoke_all          # 全端点冒烟（需本地 Redis 与已初始化的数据库）
uv run ruff check .                         # 代码检查
uv run ruff format .                        # 代码格式化
```

前端（在 `walnut-frontend/` 下，使用 pnpm）：

```bash
pnpm install      # 安装依赖
pnpm dev:antd     # 开发服务
pnpm build:antd   # 构建生产包
```

> 启用接口加密时，RSA 公私钥须与后端配置配对，且是**两对**密钥：前端请求加密密钥对应后端解密密钥，后端响应加密密钥对应前端解密密钥。见 `apps/web-antd/.env.development`。

## 后端接口契约

- 统一响应信封：`{"code": int, "msg": str, "data": T | null}`
  - `code` 200=成功、500=失败、601=警告；业务异常几乎都返回 HTTP 200，前端据 body.code 判断
- 分页载荷：`{"rows": [...], "total": N}`
- 错误码：认证模块使用 10000 段错误码（`AuthErrorCode`，如 10005 用户名或密码错误）；其余业务异常统一 HTTP 200 + `code=500`，参数校验错误 `code=400`，401/403/404/405 返回真实 HTTP 状态码（仍带信封体）
- 认证：`Authorization: Bearer <jwt>` + `clientid` 请求头
- JSON 规则：日期时间 `yyyy-MM-dd HH:mm:ss`、超出 JS 安全整数范围的大整数转字符串

## 安全机制

- **密钥治理**：JWT 签名密钥生产环境强制校验（占位符 / 过短 / 未设置直接拒绝启动）；接口加解密 RSA 密钥不内置任何默认值——密钥缺失或无效时加密层自动停用并告警（绝不静默使用默认密钥），已知公开泄露的密钥直接拒绝。生成工具：`uv run python scripts/gen_rsa_keys.py`（RSA 密钥对）、`scripts/gen_secret_key.py`（SECRET_KEY）
- **路由认证审计**：启动时扫描全部路由，白名单（`WHITE_API_LIST_PATH`）之外的路由缺少认证依赖即启动失败（fail-fast），杜绝漏挂依赖导致的接口裸奔
- **数据权限 fail-closed**：数据权限组件异常时拒绝访问而非放行；无角色用户仅可见本人数据
- **登录防护**：登录接口限流（每 IP 10 次/分钟）；失败锁定按「用户名 + IP」计数（防恶意锁定他人账号）；用户不存在与密码错误统一文案（防账号枚举）
- **可信代理**：`TRUSTED_PROXY_IPS` 列表内的来源才解析 `X-Forwarded-For` 等转发头，反向代理部署须按拓扑配置，否则限流与审计日志按直连地址计
- **文件上传**：扩展名白名单（`ALLOWED_EXTENSIONS`）+ 大小限制（`MAX_FILE_SIZE`）；上传文件访问统一附带 `Content-Disposition: attachment` 与 `nosniff`，防存储型 XSS
- **日志脱敏**：写日志前自动剔除密码类字段（`EXCLUDE_PROPERTIES`：`password` / `oldPassword` / `newPassword` / `confirmPassword`）

## 文件存储（OSS）

默认 **SeaweedFS**（任意 S3 兼容对象存储，基于 minio SDK，配置层为通用 `OSS_S3_*` 命名）；可切 `OSS_TYPE=aliyun` 用阿里云 OSS（需自行安装 `oss2`）。
Docker 编排已内置 seaweedfs 服务（单容器 `server -s3`：S3 API 8333；filer UI `http://localhost:8888`）。
注意：当前 SeaweedFS 版本静态 `-s3.config` 身份不生效（上游 #4728/#8331），S3 网关默认信任访问者——编排仅把 8333/8888 暴露给内网/宿主机调试，生产外网部署请置于防火墙/代理之后；后端仍按配置发送 AK/SK（网关兼容接受）。

- 上传对象 key 规则：`{yyyy/MM/dd}/{uuid}.{ext}`，桶由后端启动时自动创建
- 上传返回 url 形如 `/upload/{key}`（中性路径，跨环境可渲染），经 `GET /upload/{key}` 由后端从对象存储流式返回：
  - 本机开发：vite 代理 `/upload` → 后端 8011
  - Docker 编排：nginx `location /upload/` 转发 → 后端
- 相关配置见 `walnut-backend/env/.env.example` 的 "OSS 文件存储" 段

## 数据库迁移（Alembic）

Schema 的唯一事实来源是 `walnut-backend/app/alembic/versions/` 下的迁移脚本，**不再使用启动时 `create_all`**。

### 执行时机

| 环境 | 时机 | 说明 |
| --- | --- | --- |
| dev（本机） | 应用启动时自动执行 | `.env.dev` 中 `DATABASE_AUTO_MIGRATE=True`；失败仅告警不阻断启动 |
| prod（Docker） | 容器启动前显式执行 | `docker-entrypoint.sh` 先 `upgrade head` 再启动应用，失败即快速失败 |

### 日常变更流程

1. 修改 `app/api/v1/**/model.py` 中的 ORM 模型；
2. `uv run main.py revision --env dev -m "变更描述"` —— autogenerate 对比模型与数据库生成迁移脚本；
3. **人工审查生成的脚本**（autogenerate 不能覆盖所有场景，如数据迁移、索引调整）；
4. `uv run main.py upgrade --env dev` 应用到本地库验证；
5. 迁移脚本随代码提交，生产由 entrypoint 自动应用。

### 其他命令

```bash
uv run main.py downgrade --env dev -r -1     # 回退一步（-r base 全部回退）
uv run main.py stamp --env dev               # 仅写版本标记不执行 DDL（存量库接入用）
uv run main.py current --env dev             # 查看当前版本
uv run main.py history --env dev             # 查看版本链
```

### 存量库接入（一次性）

旧版通过 `create_all` 建库、结构已等同模型的数据库，执行 `uv run main.py stamp --env dev`
写入 `alembic_version` 即可接入（不执行任何 DDL）。**切勿对未 stamp 的存量库直接 upgrade**
（会因表已存在而失败）。Docker 实例建议直接删除 `docker/volumes` 重建。

### 注意事项

- MySQL 的 DDL 不受事务保护（`transaction_per_migration` 对 DDL 无效）：迁移中途失败可能留下
  半应用的 schema，需人工核对数据库状态后重新 `upgrade` 或 `stamp`。
- 回退初始迁移会删除全部表，请在沙箱库操作。
- 约束/索引命名遵循 `app/core/base_model.py` 中的 `NAMING_CONVENTION`（`ix_*`/`uq_*` 等），
  旧库 stamp 后首次 autogenerate 可能出现索引改名的表面 diff，保留（收敛命名）或手工剪掉均可。

## 配置摆放

原则：**部署级配置进 `docker/`，应用级配置留在应用侧**；容器环境变量以 compose 为唯一入口，不另设 env 文件。

### 我想改 X，去哪改

| 想改什么 | 去哪改 | 说明 |
|---|---|---|
| 本地开发的后端行为（连库、密钥等） | `walnut-backend/env/.env.dev` | 只放差异项，其余走代码默认值 |
| 任何环境的配置项默认值 | `walnut-backend/app/config/setting.py` | 唯一事实源；改动影响所有环境 |
| Docker 部署的后端环境变量 | `docker/docker-compose.yml` 的 `backend.environment` | 环境变量优先于 env 文件 |
| 密码 / JWT 密钥 / 后端端口等共用值 | `docker/.env`（模板 `.env.example`） | compose 变量插值，一处改多处生效 |
| 中间件端口映射 / 健康检查 / 启动参数 | `docker/docker-compose.middleware.yml` | 两份编排共用这份定义 |
| 前端 nginx 路由 / 代理 / HTTPS | `docker/config/nginx.conf` | 构建期经 `additional_contexts` 注入前端镜像，改后需 `--build frontend` |
| 前端构建期变量（API 地址、RSA 公钥等）/ dev 代理 | `walnut-frontend/apps/web-antd/.env.*`、`vite.config.ts` | 构建时注入 / vite dev server 代理 |

### 配置加载优先级（后端）

```
真实环境变量（compose / shell 注入）
  > env/.env.{ENVIRONMENT} 文件（本地开发）
  > setting.py 代码默认值（兜底）
```

Docker 镜像不打包 `env/` 目录（见 `.dockerignore`），容器内配置全部来自 compose 环境变量；`docker/.env` 是 compose 的**变量插值文件**，与后端的 `env/` 目录是两套互不相干的机制。

## 首次部署清单

1. `cp docker/.env.example docker/.env`，**必须**设置 `JWT_SECRET_KEY`（编排以 `:?` 强制校验，缺失或为空直接启动失败）：
   `python -c "import secrets; print(secrets.token_hex(32))"`
2. 按需修改 `DB_PASSWORD`（注意：已有数据卷的 MySQL 密码不会因改此值而变，需同步 `ALTER USER`）
3. `docker compose -f docker/docker-compose.yml up -d --build`
