# 常见问题 FAQ

> 更新日期：2026-08-19 · 适用版本：WalnutSeed v1.0

按场景收录高频问题。每条给**快速定位**与**处理方向**，深入的原理链接到对应文档。

## 开发环境

### 后端启动报「路由认证审计失败」

新写的接口没挂认证依赖。白名单（`WHITE_API_LIST_PATH`）之外的路由必须带 `AuthPermission` 或 `get_current_user`，这是刻意的 fail-fast。给接口补上 `auth: Annotated[AuthSchema, Depends(AuthPermission(permissions=[...]))]`；确属公开接口才加入白名单。详见 [Python 后端设计 · 2.3](./python/02-架构设计.md#23-启动路由认证审计fail-fast)。

### 前端请求 404 / 跨域

先确认三件事：① 后端真的起来了（`http://localhost:8011/docs` 能开）；② 前端 dev server 的 `/api` 代理指向后端 8011（`apps/web-antd/vite.config.ts`）；③ 请求路径前缀对（开发是 `/api`，生产是 `/prod-api`，后端路由本身不带这个前缀——由代理剥离）。跨域只在「前端直连后端、不走代理」时才会出现，走代理则同源。

### `uv sync` 很慢或失败

`pyproject.toml` 配了 tuna 镜像（`[[tool.uv.index]]`）。若你在海外或镜像不可达，可临时切官方源：`uv sync --index-url https://pypi.org/simple`。锁文件 `uv.lock` 已提交，正常应 `uv sync --frozen`。

### `pnpm install` 报 Node/pnpm 版本不匹配

前端要求 Node `^22.18.0 || ^24.0.0`、pnpm 11（`package.json` engines + `packageManager`）。用 nvm/fnm 切 Node 版本，`corepack enable` 或 `npm i -g pnpm@11`。注意仓库根有 `preinstall: npx only-allow pnpm`，**不能用 npm/yarn 装**。

## 数据库与迁移

### 启动报「表已存在」

对未 stamp 的存量库直接跑了 `upgrade`。存量库（旧 `create_all` 建的、结构已等同模型）应先 `uv run main.py stamp --env dev` 只写版本标记，再考虑后续迁移。Docker 环境更简单：删 `docker/volumes` 重建。详见 [Alembic 迁移 · 4](./python/09-数据库迁移-Alembic.md#4-存量库接入一次性)。

### 迁移脚本冲突 / 版本链分叉（multiple heads）

两人各自生成迁移、`down_revision` 指向同一父版本导致分叉。简单情况：把其中一个脚本的 `down_revision` 改成另一个的 `revision`，串成一条链。团队层面：迁移脚本随 PR 提交，合并前 rebase 时检查版本链。详见 [Alembic 迁移 · 5](./python/09-数据库迁移-Alembic.md#5-故障处理)。

### 改了模型但接口报表不存在 / 字段不存在

忘了生成或应用迁移。改 `model.py` 后要走 `revision`（生成）→ 审查 → `upgrade`（应用）。dev 虽会在启动时自动迁移（`DATABASE_AUTO_MIGRATE=True`），但失败只告警不阻断，建议显式 `upgrade` 第一时间暴露问题。

## Docker

### 两套 compose 编排端口冲突

`docker-compose.yml`（全栈）与 `docker-compose.middleware.yml`（仅中间件）经 include 共用中间件定义，容器名与宿主机端口（3307/6380/8333/8888）完全一致，**不能同时跑**。先 `down` 掉一套再起另一套。详见 [Docker 部署总览 · 1](./python/10-Docker部署.md#1-编排结构一份中间件定义多种用法)。

### 改了 `DB_PASSWORD` 不生效

`MYSQL_ROOT_PASSWORD` 只在 MySQL **首次初始化**时生效；已有 `docker/volumes/mysql` 数据卷时改 `.env` 不会改库内密码。需进容器 `ALTER USER` 同步，或删 `docker/volumes` 重新初始化（会清数据）。

### 后端容器一直重启 / 起不来

看 `docker logs walnut-backend-python`，常见两类：① **`JWT_SECRET_KEY` 未设置**——compose 用 `${VAR:?}` 强制，缺失直接报错；② **迁移失败**——entrypoint `set -e`，迁移不过容器退出。前者补密钥，后者修迁移脚本。详见 [生产清单 · 0](./python/11-生产上线清单.md#0-先看启动门禁不满足直接起不来)。

### `down` 之后数据还在 / 想彻底清空

`down` 只删容器与网络，中间件数据（绑定挂载 `docker/volumes/`）与后端数据（具名卷 `backend-data`）都保留。`down -v` 额外删具名卷（后端日志/上传），但**不影响绑定挂载**——要清中间件数据需手动删 `docker/volumes/`。

### 改了 nginx.conf 或前端代码不生效

前端镜像是构建期注入 nginx 配置与产物的，改后要重建：`docker compose -f docker/docker-compose.yml up -d --build frontend`。

## 权限与登录

### 登录被锁定怎么解除

密码错 5 次锁定 10 分钟（按「用户名 + IP」计数）。自然过期即可；急需解除可在「系统管理 → 登录日志」页解锁，或删 Redis 键 `pwd_err_cnt:<用户名>:<IP>`。注意锁的是「用户名+IP」组合，换 IP 或等过期都能恢复。

### 接口 403，但菜单可见

菜单（M/C）可见 ≠ 有按钮权限（F）。检查该角色的 `sys_role_menu` 是否勾了对应 F 行、前端传的权限串与接口 `AuthPermission(permissions=[...])` 是否逐字一致。前端只藏按钮，真正的拦截在后端。详见 [菜单与权限 · 5](./python/05-权限配置.md#5-常见排查)。

### 菜单不出现

① 角色没勾该菜单；② 菜单 `status` 停用 / `visible` 隐藏；③ C 菜单 `component` 路径与 `src/views/` 对不上（看浏览器 console「未找到对应组件」）。权限集合在**登录时**快照进会话，改完权限要**重新登录**才刷新。

### 列表数据比预期少

数据权限生效了：确认角色 `data_scope`（如"仅本人"只看自己创建的）。超管不受限。详见 [菜单与权限 · 4](./python/05-权限配置.md#4-数据权限行级)。

## 文件与加解密

### 上传被拒（400）

扩展名不在白名单 `ALLOWED_EXTENSIONS`（明确禁 html/htm/svg 等），或超过 `MAX_FILE_SIZE`（默认 10MB）。业务确需新类型再改配置，别放行可执行脚本类。

### 敏感接口加解密「没生效」

① 前端请求没加 `encrypt: true`（逐接口开关）；② 前后端密钥不配对（请求公钥 ↔ 后端解密私钥须同一对）；③ 密钥为空/无效被启动校验自动停用（看后端日志「已自动停用接口加解密」）。详见 [接口加解密 · 6](./python/06-接口加解密.md#6-联调与排查)。

## 其他

### 接口文档 `/docs` 生产要不要关

默认公开（在认证白名单内，无配置开关）。若不想暴露，在 nginx 层拦截 `/docs`、`/redoc`、`/openapi.json`。详见 [Python 生产清单](./python/11-生产上线清单.md#2-网络与代理必配)。

### 某些配置项改了没反应

`OPERATION_LOG_RETENTION_DAYS`、`REDIS_KEY_PREFIX`、`REDIS_DEFAULT_CACHE_TTL`、`WEBSOCKET_ALLOWED_ORIGINS` 这几项**已定义但代码未消费**，配了不生效。完整清单见 [生产清单 · 附录](./python/11-生产上线清单.md#附已定义但未接线的配置项)。
