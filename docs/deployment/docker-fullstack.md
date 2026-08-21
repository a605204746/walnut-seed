# Docker 全栈部署

> 更新日期：2026-08-19 · 适用版本：WalnutSeed v1.0
> 基础启动命令已见于根目录 [README「Docker 编排」](../../README.md#docker-编排)，本文讲透编排结构、镜像构建、配置注入与运维操作。

一条命令起全栈（MySQL + Redis + SeaweedFS + 后端 + 前端 nginx）：

```bash
cp docker/.env.example docker/.env    # 先配好 JWT_SECRET_KEY（必填）
docker compose -f docker/docker-compose.yml up -d --build
# 访问 http://localhost:8010，初始账号 admin / admin123（生产必须改密）
```

## 1. 编排结构：一份中间件定义，两种用法

`docker/` 下两份编排，全栈经 `include` 复用中间件定义：

```yaml
# docker/docker-compose.yml（全栈）
name: walnut-seed-python
include:
  - docker-compose.middleware.yml    # 复用 mysql/redis/seaweedfs 定义
```

| 编排文件 | 场景 | 包含服务 |
|---|---|---|
| `docker-compose.yml` | 生产/全栈 | mysql + redis + seaweedfs + **backend + frontend** |
| `docker-compose.middleware.yml` | 仅中间件（应用本机跑） | mysql + redis + seaweedfs |

**为什么不能同时跑**：两份编排项目名相同（`walnut-seed-python`），中间件的 `container_name`（walnut-mysql / walnut-redis / walnut-seaweedfs）与宿主机端口映射完全一致，同时起必然冲突。反过来，正因容器名和数据卷一致，两种形态**互切不丢数据**。

### 1.1 全栈编排的服务与端口

| service | 镜像/构建 | 宿主机端口 |
|---|---|---|
| mysql | `mysql:8.0` | `3307:3306` |
| redis | `redis:7-alpine` | `6380:6379` |
| seaweedfs | `chrislusf/seaweedfs:4.41`（固定版本，防上游静默变更） | `8333`（S3 API）、`8888`（filer UI） |
| backend | `build: ../walnut-backend` | **不暴露**（仅容器网络，经 nginx 访问） |
| frontend | `build: ../walnut-frontend` | `8010:80` |

中间件用非默认端口（3307/6380），避免与宿主机自装的 MySQL/Redis（3306/6379）冲突。注意中间件端口映射定义在 middleware 文件里，**全栈模式下同样暴露到宿主机**——生产环境如不需要外部直连中间件，应在防火墙层面封禁。

> SeaweedFS 当前版本静态 `-s3.config` 身份不生效（上游 #4728/#8331），S3 网关默认信任访问者，8333/8888 只应置于内网/防火墙后。

**依赖链**（全部 `condition: service_healthy`）：`mysql/redis/seaweedfs → backend → frontend`。所有服务 `restart: unless-stopped`。frontend 等 backend 健康后才起，避免启动窗口内 `/prod-api/` 全 502。

## 2. 镜像构建

### 2.1 后端：多阶段 + 非 root

`walnut-backend/Dockerfile` 两阶段：

- **builder 阶段**：从 `ghcr.io/astral-sh/uv:0.11.2` 拷 uv 二进制，`uv sync --frozen --no-dev --no-install-project` 按 `uv.lock` 冻结安装生产依赖到 `.venv`（先拷 lock 文件利用层缓存）；
- **运行阶段**：`python:3.12-slim`，建固定 `uid 1000` 的 `appuser`，拷入 `.venv`，`ENTRYPOINT` 为 `docker-entrypoint.sh`，`USER appuser` 非 root 运行。

**`env/` 目录不进镜像**（`.dockerignore` 排除）——这就是"容器配置全走 compose 环境变量"的依据。入口脚本在应用启动前显式执行 Alembic 迁移：

```sh
set -e                                   # 迁移失败即快速失败，绝不带过期 schema 对外服务
python main.py upgrade --env prod
exec "$@"                                # 交棒给 CMD：python main.py run --env prod
```

### 2.2 前端：构建产物 + nginx 模板

`walnut-frontend/scripts/deploy/Dockerfile` 两阶段：node:22 里 `pnpm install --frozen-lockfile` + `pnpm run build:antd`（产物在 `apps/web-antd/dist`），再拷进 `nginx:stable-alpine`。

nginx 配置经 `additional_contexts` 注入：compose 里 `additional_contexts: { deploy: . }`（`.` 即 `docker/` 目录），Dockerfile 用 `COPY --from=deploy config/nginx.conf` 取 `docker/config/nginx.conf` 作为**模板**，启动时 `envsubst` 只替换 `${BACKEND_HOST} ${BACKEND_PORT}` 两个变量（显式限定，避免误伤 nginx 内置 `$uri` 等变量）后生成最终配置。

### 2.3 nginx 路由规则（docker/config/nginx.conf）

| location | 规则 | 说明 |
|---|---|---|
| `/` | SPA 静态，`try_files ... /index.html` | 入口 html `no-store` 禁缓存 |
| `/assets/` | 长缓存（`max-age=31536000, immutable`） | Vite 哈希产物 |
| `/upload/` | 反代后端，**保留前缀** | 上传文件由后端从对象存储流式回源 |
| `/prod-api/` | 反代后端，**剥掉前缀**（`proxy_pass http://server/;` 尾斜杠） | API 入口，对应前端 `VITE_GLOB_API_URL=/prod-api` |

`/prod-api/` 为长连接做了适配：`proxy_read_timeout 86400s`、`proxy_buffering off`、WebSocket `Upgrade` 头、`limit_conn` 阈值（SSE 长连接多，留余量）。另有 `client_max_body_size 100m`、`server_tokens off`、`nosniff`/`SAMEORIGIN` 等安全头（故意不加 CSP——vben 产物含内联脚本）。改 nginx 配置后需 `up -d --build frontend` 重新构建前端镜像。

## 3. 配置注入：docker/.env 变量插值

容器环境变量以 compose 为唯一入口，共用值经 `docker/.env` 插值统一管理（模板 `.env.example` 随仓库提交，`.env` 在 `.gitignore`）：

| 变量 | 插值方式 | 说明 |
|---|---|---|
| `JWT_SECRET_KEY` | **`${VAR:?}` 强制** | 缺失/为空直接启动失败；须 ≥32 字节，生成命令见 `.env.example` |
| `DB_PASSWORD` | `${VAR:-walnut123}` 兜底 | mysql root 密码与后端 `DATABASE_PASSWORD` 共用 |
| `DB_NAME` | `${VAR:-walnut_seed_python}` | 建库名 + 后端连接库名 |
| `BACKEND_PORT` | `${VAR:-8011}` | 后端监听 + nginx upstream + healthcheck 共用 |
| `OSS_ACCESS_KEY` / `OSS_SECRET_KEY` | `${VAR:-walnut}` / `${VAR:-walnut123}` | SeaweedFS S3 凭据 |

`backend.environment` 注入完整环境（`ENVIRONMENT=prod`、`DEBUG=False`、`DATABASE_HOST=mysql`、`REDIS_HOST=redis`、`OSS_S3_ENDPOINT=seaweedfs:8333`、`OSS_S3_URL_PREFIX=/upload` 等）——数据库/Redis/对象存储都用**容器网络服务名**直连。

后端侧：`settings` 虽声明读 `env/.env.{ENVIRONMENT}`，但镜像里没有 `env/`，文件不存在时静默跳过，**环境变量直接生效**。另有纵深防御：`SECRET_KEY` 代码默认是 `change-me` 占位值，prod 下 `validate_security_settings()` 对"为空/含 change-me/<32 字节"直接拒绝启动。

## 4. 数据持久化

| service | 挂载 | 类型 |
|---|---|---|
| mysql | `./volumes/mysql:/var/lib/mysql` | 绑定挂载（`docker/volumes/`） |
| redis | `./volumes/redis:/data` | 绑定挂载 |
| seaweedfs | `./volumes/seaweedfs:/data` | 绑定挂载 |
| backend | `backend-data:/data` | **具名卷** |

**后端为什么用具名卷而非绑定挂载**：容器以非 root 的 `appuser` 运行，Linux 上绑定挂载目录由 compose 以 root 创建、appuser 无写权限；具名卷首次挂载会**继承镜像内 `/data` 的属主**（Dockerfile 已 chown 给 appuser），非 root 进程即可写。

### 健康检查要点

- **mysql 探活用 `127.0.0.1` 而非 `localhost`**：mysql 镜像首次初始化时临时开启 `--skip-networking`，`localhost` 走 unix socket 会提前通过而 TCP 未就绪，导致后端先于数据库就绪而启动（后端连库执行迁移无重试，会直接失败）；
- **backend 用 python urllib** 探 `/common/health/check`（slim 镜像无 curl/wget）：该端点是**存活式探针**（不依赖 DB/Redis），就绪探针是 `/common/health/ready`（并发 `SELECT 1` + `redis.ping()`，任一失败 503）；`start_period: 60s` 为入口脚本的 Alembic 迁移留时间。两个探针路径都在免认证白名单里，无需 token。

**启动时序**：mysql healthy（TCP 就绪）→ backend 容器启动 → entrypoint 跑迁移 → `main.py run` 起 uvicorn → lifespan 幂等播种（`admin/admin123` 来源）→ backend healthcheck 通过 → frontend 启动。

## 5. 常用运维操作

| 操作 | 命令 |
|---|---|
| 查看后端日志 | `docker logs -f walnut-backend`（`PYTHONUNBUFFERED=1` 保证不缓冲） |
| 重启单服务 | `docker compose -f docker/docker-compose.yml restart backend` |
| 仅重建前端（改了 nginx/前端代码） | `docker compose -f docker/docker-compose.yml up -d --build frontend` |
| 仅重建后端 | `docker compose -f docker/docker-compose.yml up -d --build backend` |
| 停止（保留数据） | `docker compose -f docker/docker-compose.yml down` |
| 停止并删具名卷 | `docker compose -f docker/docker-compose.yml down -v`（清 backend-data：日志/上传） |
| 彻底清空中间件数据 | 手动删除 `docker/volumes/`（`down -v` **不影响**绑定挂载） |

注意：

- `down` 删容器与网络，但中间件数据（绑定挂载）与后端数据（具名卷 `backend-data`）都保留；`down -v` 只删具名卷，要清中间件数据需手动删 `docker/volumes/`。
- 项目名 `walnut-seed-python` 决定网络名与具名卷前缀（`walnut-seed-python_backend-data`）；**修改项目名会被视为新项目，旧卷不被沿用**。
- 重启 backend 会重跑 entrypoint 迁移——已在 head 时为空操作，幂等安全。
