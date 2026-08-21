# 整体架构

> 更新日期：2026-08-19 · 适用版本：WalnutSeed v1.0

本文给出 WalnutSeed 的全景视图：模块如何划分、一个请求如何流过系统、前后端按什么契约协作、横切能力挂在哪里。机制细节（响应信封、异常映射、中间件实现）见 [后端设计](./backend-design.md)。

## 1. 模块划分

### 1.1 仓库三大块

```
walnut-seed-fastapi/
  walnut-backend/    # FastAPI 后端（本文主角）
  walnut-frontend/   # Vue3 monorepo（pnpm + turbo），主应用 apps/web-antd/
  docker/            # 两套 compose 编排 + nginx 配置（见部署文档）
```

### 1.2 后端业务域（app/api/v1/module_*）

| 模块 | 路由前缀 | 职责 |
|---|---|---|
| `module_web` | `/auth` | 面向前端的认证域：登录/登出/注册/验证码/租户 |
| `module_system` | `/system`（日志在 `/monitor`） | 后台管理域：user/role/menu/dept/post/dict/config/notice/client/social/log 共 11 个子模块 |
| `module_common` | `/common` | 公共能力：健康检查（check/live/ready）、文件上传下载 |
| `module_resource` | `/resource` | 实时通道：SSE、WebSocket |
| （文件内联访问） | `/upload/{key}` | 上传文件流式回源，挂在应用根路径 |

业务子模块统一「五件套」结构（controller/service/crud/model/schema），新增模块的完整步骤见 [从零新增一个业务模块](../guide/new-crud-module.md)。

**路由装配只有一个组合根**：`app/api/v1/router.py` 集中维护所有前缀与注册顺序（如 `ProfileRouter` 必须先于 `UserRouter` 注册，避免 `/user/{userId}` 吞掉 `/user/profile`），`init_app.register_routers` 只从它导入。

### 1.3 基础设施层

```
app/core/        基础设施（database / security / dependencies / permission /
                 middlewares / exceptions / base_model / base_crud / router_class /
                 idempotent / rate_limiter / sse / websocket / file_storage / encrypt）
app/config/      setting.py（配置唯一事实源）/ path_conf.py
app/common/      constant / enums / response / request
app/utils/       工具集（i18n / snowflake / excel / xss / ...）
app/seed/        种子数据（initialize.py + sql/）
```

## 2. 一个请求的生命周期

```
浏览器
  │  /prod-api/system/user/list（生产 nginx）或 /api/...（dev vite 代理）
  ▼
nginx / vite 代理（剥离前缀）
  ▼
┌─────────────────── 中间件栈（从外到内）───────────────────┐
│ HTTPSRedirect(条件) → TrustedHost(仅prod) → CORS → Locale │
│ → ApiDecrypt(条件，请求解密) → XSS(条件) → RequestLog     │
│ → GZip → CorrelationId                                     │
└────────────────────────────────────────────────────────────┘
  ▼
路由匹配（OperationLogRoute）
  ▼
依赖解析：db_getter（请求级事务）→ get_current_user（JWT→Redis 会话→AuthSchema）
          → AuthPermission（鉴权）→ 可选 RateLimiter / RepeatSubmit
  ▼
参数校验（pydantic；失败 → 信封 code=400）
  ▼
端点执行：controller → service（业务编排）→ crud（数据访问）
  ▼
显式 return SuccessResponse / ErrorResponse（无全局自动包装）
  ▼
OperationLogRoute 后处理：挂 response.background 后台任务写操作日志
  ▼
异常路径：全局异常处理器把异常转成信封响应（HTTP 200 + body.code）
  ▼
响应向外穿回中间件栈（响应加密、GZip、请求日志记耗时、CORS 头）
```

几个关键设计点：

- **一个请求一个事务**：`db_getter` 里 `async with session, session.begin()`，端点内不显式 commit，异常自动回滚；
- **认证上下文**：JWT 的 `sub` 是会话 ID，真实权限数据在 Redis 会话（`user_session:<会话ID>`）里，每次请求重建 `AuthSchema(user, permissions, roles, menu_ids)` 并注入依赖链（controller → service → crud 逐层传递）；
- **fail-safe 启动哲学**：数据库初始化、Redis、OSS 桶失败都只告警降级不阻断启动；但**密钥安全与路由认证审计在 prod 一律 fail-fast**（详见 [生产上线清单](../deployment/production-checklist.md)）。

启动时序（`lifespan`）：重建日志 → 接线操作日志消费者 → 数据库（模型发现 → 按配置自动迁移 → 幂等播种）→ Redis 连接 → OSS 桶自举 → SSE/WebSocket 的 Redis topic 订阅。

## 3. 前后端协作契约

| 契约 | 约定 |
|---|---|
| 响应信封 | `{"code": int, "msg": str, "data": T \| null}`；code 200 成功 / 500 失败 / 601 警告 |
| HTTP 状态 | 业务错误几乎都返回 HTTP 200，前端按 `body.code` 分支（401 跳登录）；仅路由级 404/405 与健康探针 503 用真实状态码 |
| 分页 | `{"rows": [...], "total": N}` |
| 认证 | `Authorization: Bearer <jwt>` + `clientid` 请求头 |
| JSON 规则 | 日期时间 `yyyy-MM-dd HH:mm:ss`；超 JS 安全整数的雪花 ID 自动转字符串 |
| 菜单/路由 | 后端 `sys_menu` 驱动：`GET /system/menu/getRouters` 返回菜单树，前端动态解析 `component` → `src/views/*.vue` |
| 权限点 | `GET /system/user/getInfo` 返回 `permissions`（perms 集合），前端 `v-access:code` 消费，与后端 `AuthPermission` 逐字一致 |
| 语言 | 前端注入 `Accept-Language`，后端 i18n 按请求头选 zh_CN/en_US |

详见根目录 [README「后端接口契约」](../../README.md#后端接口契约) 与 [菜单与权限配置](../guide/menu-permission.md)。

## 4. 横切能力的挂载点

所有横切能力都是**显式挂载、无魔法**——每处都有明确的挂载位置和开关：

| 能力 | 挂载方式 | 开关/配置 |
|---|---|---|
| 缓存 | 显式 cache-aside（`RedisUtils`，无注解缓存） | Redis 键前缀集中在 `CacheNames` |
| 限流 | `Depends(RateLimiter(time, count, limit_type))` | 按路由声明，Redis 故障 fail-closed |
| 防重提交 | `Depends(RepeatSubmit(interval))` | 按路由声明 |
| 操作日志 | `route_class=OperationLogRoute` + `@log(title, business_type)` | `OPERATION_RECORD_METHOD` 控制记录哪些方法 |
| 接口加解密 | 请求方向中间件自动；响应方向 `@api_encrypt(response=True)` | `API_DECRYPT_ENABLED` + RSA 密钥 |
| 数据权限 | service 层调 `Permission(...).filter_query()` | 角色 `data_scope` |
| SSE/WebSocket | `module_resource` 端点 + Redis pub/sub 跨实例 | `SSE_ENABLED` / `WEBSOCKET_ENABLED` |
| i18n | `LocaleMiddleware` + `MessageUtils.message` | `Accept-Language` 请求头 |

各能力的用法与边界在对应的开发教程里有详细说明（见 [docs 索引](../README.md)）。
