# 从零新增一个业务模块

> 更新日期：2026-08-19 · 适用版本：WalnutSeed v1.0 · 预计耗时：首次 1~2 小时，熟练后 20 分钟

本教程以新增一个「博客管理」域下的**文章管理**模块为例，端到端走完脚手架的标准开发流程：

```
后端五件套 → 路由注册 → 数据库迁移 → 菜单与权限 → 前端页面 → 验证
```

完成后你将拥有：

- `/blog/article` 下的增删改查、分页查询接口（带认证、权限、操作日志、防重提交）
- `blog_article` 数据表（Alembic 迁移生成）
- 前端「博客管理 → 文章管理」页面（列表 + 搜索 + 新增/编辑/删除）

> 示例代码可直接照抄，模块名按你的业务替换即可。参考原型：`module_system/post`（岗位管理），它是最接近本教程形态的现有模块。

## 0. 前置准备

确保开发环境已就绪（详见根目录 [README「快速开始」](../../README.md#快速开始)）：

```bash
docker compose -f docker/docker-compose.middleware.yml up -d   # 中间件
cd walnut-backend && uv sync && uv run main.py run --env dev   # 后端能正常启动
cd walnut-frontend && pnpm install && pnpm dev:antd            # 前端能登录
```

## 1. 创建后端模块包

业务模块统一放在 `walnut-backend/app/api/v1/module_*/`。新建包目录：

```
walnut-backend/app/api/v1/module_blog/
  __init__.py                 # 内容："""博客管理模块。"""
  article/
    __init__.py               # 空文件即可
    model.py                  # ORM 模型
    schema.py                 # Pydantic 入参/出参
    crud.py                   # 数据访问层
    service.py                # 业务逻辑
    controller.py             # 路由
```

下面按**依赖方向自底向上**逐个编写。

### 1.1 model.py —— ORM 模型

继承 `BaseEntity`：自动获得雪花主键 `id` 和 `create_by/create_dept/create_time/update_by/update_time` 审计字段（写入时由 CRUDBase 从登录上下文自动填充）。需要逻辑删除时再混入 `SoftDeleteMixin`（加 `del_flag` 字段），树形表混入 `TreeEntityMixin`——本例都不需要。

```python
"""文章的域模型。"""

from datetime import datetime

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base_model import BaseEntity


class ArticleModel(BaseEntity):
    """文章表 blog_article"""

    __tablename__ = "blog_article"
    __table_args__ = {"comment": "文章表"}

    title: Mapped[str] = mapped_column(String(100), nullable=False, comment="文章标题")
    content: Mapped[str | None] = mapped_column(Text, default=None, nullable=True, comment="文章内容")
    status: Mapped[str] = mapped_column(String(1), default="0", nullable=False, comment="状态（0草稿 1已发布）")
    publish_time: Mapped[datetime | None] = mapped_column(DateTime, default=None, nullable=True, comment="发布时间")
```

约定：表名带域前缀（`blog_article`），每个列写 `comment`（会进入数据库和迁移脚本，是文档的一部分）。

### 1.2 schema.py —— 入参/出参模型

四类 schema，注意两个关键点：

1. **查询参数与写参用 camelCase alias**（前端按驼峰传参），配合 `populate_by_name=True`；
2. **出参模型用 `alias_generator=to_camel` + `from_attributes=True`**，序列化时 `model_dump(by_alias=True, mode="json")` 直接得到驼峰 JSON。

```python
"""文章的入参/出参模型。"""

from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic.alias_generators import to_camel

from app.core.base_schema import PageQueryParam
from app.core.validator import DateTimeStr


class ArticleQueryParam(PageQueryParam):
    """文章列表查询参数（GET）。pageNum/pageSize/orderByColumn/isAsc 由基类提供。"""

    title: str | None = Field(default=None, description="文章标题")
    status: str | None = Field(default=None, description="状态（0草稿 1已发布）")
    begin_time: DateTimeStr | None = Field(default=None, alias="beginTime", description="创建时间起")
    end_time: DateTimeStr | None = Field(default=None, alias="endTime", description="创建时间止")


class ArticleCreateSchema(BaseModel):
    """新增文章入参。"""

    model_config = ConfigDict(populate_by_name=True)

    title: str | None = Field(default=None, validate_default=True, description="文章标题")
    content: str | None = Field(default=None, description="文章内容")
    status: str | None = Field(default=None, description="状态（0草稿 1已发布）")

    @field_validator("title")
    @classmethod
    def check_title(cls, value: str | None) -> str:
        if value is None or not value.strip():
            raise ValueError("文章标题不能为空")
        if len(value) > 100:
            raise ValueError("文章标题长度不能超过100个字符")
        return value


class ArticleUpdateSchema(ArticleCreateSchema):
    """修改文章入参。"""

    id: int | None = Field(default=None, validate_default=True, description="文章ID")

    @field_validator("id")
    @classmethod
    def check_id(cls, value: int | None) -> int:
        if value is None:
            raise ValueError("文章ID不能为空")
        return value


class ArticleOutSchema(BaseModel):
    """文章出参。"""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True, alias_generator=to_camel)

    id: int | None = Field(default=None, description="文章ID")
    title: str | None = Field(default=None, description="文章标题")
    content: str | None = Field(default=None, description="文章内容")
    status: str | None = Field(default=None, description="状态（0草稿 1已发布）")
    publish_time: DateTimeStr | None = Field(default=None, description="发布时间")
    create_time: DateTimeStr | None = Field(default=None, description="创建时间")
```

> `validate_default=True` + 校验器抛 `ValueError` 是本项目的必填校验惯用法：字段允许 JSON 缺省（默认 None），但校验器强制非空，错误会被全局异常处理转成 `code=400` 的信封响应。

### 1.3 crud.py —— 数据访问层

`CRUDBase` 已提供 `create / get / get_by / list_all / page / update / delete / delete_batch`（含审计字段填充、分页排序与注入防护）。简单模块**可以一行查询都不写**：

```python
"""文章的数据访问层。"""

from app.api.v1.module_blog.article.model import ArticleModel
from app.core.base_crud import CRUDBase


class ArticleCrud(CRUDBase[ArticleModel]):
    """文章 CRUD。通用能力由 CRUDBase 提供，按需补充定制查询。"""
```

需要唯一性校验、联表统计等定制查询时在此补充（参考 `module_system/post/crud.py` 的 `exists_by_name` 写法：一律用 SQLAlchemy select 表达式，不拼字符串）。

### 1.4 service.py —— 业务逻辑

Service 由 controller 按请求实例化，持有 `auth`（当前登录上下文）与 `db`（会话）：

```python
"""文章业务逻辑。"""

from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.module_blog.article.crud import ArticleCrud
from app.api.v1.module_blog.article.model import ArticleModel
from app.api.v1.module_blog.article.schema import (
    ArticleCreateSchema,
    ArticleOutSchema,
    ArticleQueryParam,
    ArticleUpdateSchema,
)
from app.core.base_schema import AuthSchema
from app.utils.string_util import is_not_blank


class ArticleService:
    """文章服务。"""

    def __init__(self, auth: AuthSchema, db: AsyncSession) -> None:
        self.auth = auth
        self.db = db
        self.crud = ArticleCrud(ArticleModel, auth, db)

    # ---------------- 查询条件 ----------------
    async def _build_conditions(self, req: ArticleQueryParam) -> list[Any]:
        conditions: list[Any] = []
        if is_not_blank(req.title):
            conditions.append(ArticleModel.title.like(f"%{req.title}%"))
        if is_not_blank(req.status):
            conditions.append(ArticleModel.status == req.status)
        if req.begin_time is not None and req.end_time is not None:
            conditions.append(ArticleModel.create_time.between(req.begin_time, req.end_time))
        return conditions

    # ---------------- 查询 ----------------
    async def page_list(self, req: ArticleQueryParam) -> dict:
        """分页查询文章列表。"""
        conditions = await self._build_conditions(req)
        result = await self.crud.page(req, *conditions)
        rows = [ArticleOutSchema.model_validate(a).model_dump(by_alias=True, mode="json") for a in result["rows"]]
        return {"rows": rows, "total": result["total"]}

    async def get_by_id(self, article_id: int) -> dict | None:
        """按文章ID查询。"""
        article = await self.crud.get(article_id)
        if article is None:
            return None
        return ArticleOutSchema.model_validate(article).model_dump(by_alias=True, mode="json")

    # ---------------- 写入 ----------------
    async def insert_article(self, req: ArticleCreateSchema) -> bool:
        """新增文章（发布状态自动打发布时间）。"""
        data = req.model_dump(exclude_none=True)
        if data.get("status") == "1":
            data["publish_time"] = datetime.now()
        article = await self.crud.create(ArticleModel(**data))
        return article.id is not None

    async def update_article(self, req: ArticleUpdateSchema) -> bool:
        """修改文章（仅更新非空字段）。"""
        article = await self.crud.get(req.id)
        if article is None:
            return False
        data = req.model_dump(exclude_none=True, exclude={"id"})
        if data.get("status") == "1" and article.publish_time is None:
            data["publish_time"] = datetime.now()
        for field, value in data.items():
            setattr(article, field, value)
        await self.crud.update(article)
        return True

    async def delete_by_ids(self, article_ids: list[int]) -> int:
        """批量删除文章。"""
        return await self.crud.delete_batch(article_ids)
```

要点：

- 业务规则（唯一性冲突、状态约束等）在 service 层判断，用 `ServiceException` 抛出（HTTP 200 + `code=500` 信封）；
- 出参一律经 `OutSchema` 转换，**不要**把 ORM 对象直接返回给 controller；
- 跨模块引用模型时用**函数内惰性导入**，避免循环依赖（参考 post service 中对 `DeptModel` 的用法）。

### 1.5 controller.py —— 路由

```python
"""文章管理（URL 前缀 /blog/article）。"""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.module_blog.article.schema import ArticleCreateSchema, ArticleQueryParam, ArticleUpdateSchema
from app.api.v1.module_blog.article.service import ArticleService
from app.common.enums import BusinessType, HttpStatus
from app.common.response import EnvelopeResponse, ErrorResponse, SuccessResponse
from app.core.base_schema import AuthSchema
from app.core.dependencies import AuthPermission, db_getter
from app.core.exceptions import ServiceException
from app.core.idempotent import RepeatSubmit
from app.core.router_class import OperationLogRoute, log
from app.utils.string_util import str2list

ArticleRouter = APIRouter(route_class=OperationLogRoute, prefix="/article", tags=["文章管理"])

DbSession = Annotated[AsyncSession, Depends(db_getter)]


def _parse_ids(ids: str) -> list[int]:
    """解析路径中的ID串。"""
    try:
        id_list = [int(item) for item in str2list(ids)]
    except ValueError:
        raise ServiceException("文章ID格式有误", code=HttpStatus.BAD_REQUEST)
    if not id_list:
        raise ServiceException("文章ID不能为空", code=HttpStatus.BAD_REQUEST)
    return id_list


@ArticleRouter.get("/list", summary="获取文章列表")
async def list_article(
    params: Annotated[ArticleQueryParam, Depends()],
    db: DbSession,
    auth: Annotated[AuthSchema, Depends(AuthPermission(permissions=["blog:article:list"]))],
) -> SuccessResponse:
    return SuccessResponse(data=await ArticleService(auth, db).page_list(params))


@ArticleRouter.get("/{article_id}", summary="根据文章编号获取详细信息")
async def get_article(
    article_id: int,
    db: DbSession,
    auth: Annotated[AuthSchema, Depends(AuthPermission(permissions=["blog:article:query"]))],
) -> SuccessResponse:
    return SuccessResponse(data=await ArticleService(auth, db).get_by_id(article_id))


@ArticleRouter.post("", summary="新增文章", dependencies=[Depends(RepeatSubmit())])
@log(title="文章管理", business_type=BusinessType.INSERT)
async def add_article(
    req: ArticleCreateSchema,
    db: DbSession,
    auth: Annotated[AuthSchema, Depends(AuthPermission(permissions=["blog:article:add"]))],
) -> EnvelopeResponse:
    return SuccessResponse() if await ArticleService(auth, db).insert_article(req) else ErrorResponse()


@ArticleRouter.put("", summary="修改文章", dependencies=[Depends(RepeatSubmit())])
@log(title="文章管理", business_type=BusinessType.UPDATE)
async def update_article(
    req: ArticleUpdateSchema,
    db: DbSession,
    auth: Annotated[AuthSchema, Depends(AuthPermission(permissions=["blog:article:edit"]))],
) -> EnvelopeResponse:
    return SuccessResponse() if await ArticleService(auth, db).update_article(req) else ErrorResponse()


@ArticleRouter.delete("/{article_ids}", summary="删除文章")
@log(title="文章管理", business_type=BusinessType.DELETE)
async def delete_article(
    article_ids: str,
    db: DbSession,
    auth: Annotated[AuthSchema, Depends(AuthPermission(permissions=["blog:article:remove"]))],
) -> EnvelopeResponse:
    return SuccessResponse() if await ArticleService(auth, db).delete_by_ids(_parse_ids(article_ids)) > 0 else ErrorResponse()
```

逐项说明（每一条都是项目约定，新模块照做）：

| 元素 | 作用 |
|---|---|
| `route_class=OperationLogRoute` | 写操作异步落库操作日志（`sys_oper_log`） |
| `AuthPermission(permissions=[...])` | **必须挂**。鉴权 + 注入登录上下文；权限串约定 `域:实体:操作` |
| `@log(title=..., business_type=...)` | 标记操作日志的业务标题与类型 |
| `RepeatSubmit()` | 写接口防重提交（幂等），加在 POST/PUT 上 |
| `SuccessResponse / ErrorResponse` | 统一信封；业务校验失败抛 `ServiceException` 而非返回 ErrorResponse 之外的东西 |

⚠️ **路由认证审计**：启动时会扫描全部路由，白名单外的路由缺少认证依赖将**直接启动失败**。所以每个新路由都必须带 `AuthPermission`（或 `get_current_user`）依赖——这是刻意的 fail-fast，别绕过。

## 2. 注册路由

共两处。

**① `app/api/v1/router.py`** —— 导入并装配（路由装配的单一组合根）：

```python
from app.api.v1.module_blog.article.controller import ArticleRouter

# ==================== blog ====================
blog_router = APIRouter(prefix="/blog")
blog_router.include_router(ArticleRouter)

__all__ = [..., "blog_router"]   # 记得加入 __all__
```

**② `app/init_app.py` 的 `register_routers`** —— 挂载到应用：

```python
def register_routers(app: FastAPI) -> None:
    from app.api.v1.router import blog_router, common_router, ...

    app.include_router(blog_router)
    ...
```

最终 URL：`/blog/article/list`、`/blog/article/{id}` 等（若 API 带全局前缀则相应叠加，以启动后 Swagger 为准）。

## 3. 数据库迁移

模型写完**不要**手工建表，走 Alembic：

```bash
cd walnut-backend
uv run main.py revision --env dev -m "新增文章表"
```

打开 `app/alembic/versions/` 下新生成的脚本**人工审查**（重点看列类型、nullable、comment 是否符合预期），然后应用：

```bash
uv run main.py upgrade --env dev
```

dev 环境启动时也会按 `DATABASE_AUTO_MIGRATE=True` 自动迁移，但显式 upgrade 能第一时间暴露脚本问题。迁移细节与常见坑见 [Alembic 迁移实战](./alembic-migration.md)。

## 4. 菜单与权限

权限串（`blog:article:list` 等）必须与 `sys_menu` 中按钮型菜单的 `perms` 一致，否则有接口没入口、或有入口调不动。两种方式任选：

### 方式 A：管理端界面配置（日常开发推荐）

用 `admin` 登录 → **系统管理 → 菜单管理**，依次创建：

1. **目录**「博客管理」：类型 M，路由地址 `blog`
2. **菜单**「文章管理」：类型 C，父级选博客管理，路由地址 `article`，组件路径 `blog/article/index`（对应前端视图文件，见第 5 步），权限标识 `blog:article:list`
3. **按钮**×4：类型 F，父级选文章管理，权限标识分别为 `blog:article:query` / `blog:article:add` / `blog:article:edit` / `blog:article:remove`

然后 **系统管理 → 角色管理** 为目标角色勾选新菜单与按钮（超级管理员默认全量，无需勾选）。

### 方式 B：种子 SQL（随版本分发、开箱即有）

在 `app/seed/sql/mysql_data.sql` 追加（ID 自选，避开已有值；`INSERT IGNORE` 保证幂等）：

```sql
-- 博客管理（目录）
INSERT IGNORE INTO sys_menu (id, menu_name, parent_id, order_num, path, component, query_param, is_frame, is_cache, menu_type, visible, status, perms, icon, create_dept, create_by, create_time, update_by, update_time, remark) VALUES (2000, '博客管理', 0, 5, 'blog', NULL, '', 1, 0, 'M', '0', '0', '', 'ant-design:read-outlined', 103, 1, NOW(), NULL, NULL, '博客目录');
-- 文章管理（菜单）
INSERT IGNORE INTO sys_menu (id, menu_name, parent_id, order_num, path, component, query_param, is_frame, is_cache, menu_type, visible, status, perms, icon, create_dept, create_by, create_time, update_by, update_time, remark) VALUES (2001, '文章管理', 2000, 1, 'article', 'blog/article/index', '', 1, 0, 'C', '0', '0', 'blog:article:list', 'ant-design:file-text-outlined', 103, 1, NOW(), NULL, NULL, '文章管理菜单');
-- 按钮权限
INSERT IGNORE INTO sys_menu (id, menu_name, parent_id, order_num, path, component, query_param, is_frame, is_cache, menu_type, visible, status, perms, icon, create_dept, create_by, create_time, update_by, update_time, remark) VALUES (2002, '文章查询', 2001, 1, '', '', '', 1, 0, 'F', '0', '0', 'blog:article:query', '#', 103, 1, NOW(), NULL, NULL, '');
INSERT IGNORE INTO sys_menu (id, menu_name, parent_id, order_num, path, component, query_param, is_frame, is_cache, menu_type, visible, status, perms, icon, create_dept, create_by, create_time, update_by, update_time, remark) VALUES (2003, '文章新增', 2001, 2, '', '', '', 1, 0, 'F', '0', '0', 'blog:article:add', '#', 103, 1, NOW(), NULL, NULL, '');
INSERT IGNORE INTO sys_menu (id, menu_name, parent_id, order_num, path, component, query_param, is_frame, is_cache, menu_type, visible, status, perms, icon, create_dept, create_by, create_time, update_by, update_time, remark) VALUES (2004, '文章修改', 2001, 3, '', '', '', 1, 0, 'F', '0', '0', 'blog:article:edit', '#', 103, 1, NOW(), NULL, NULL, '');
INSERT IGNORE INTO sys_menu (id, menu_name, parent_id, order_num, path, component, query_param, is_frame, is_cache, menu_type, visible, status, perms, icon, create_dept, create_by, create_time, update_by, update_time, remark) VALUES (2005, '文章删除', 2001, 4, '', '', '', 1, 0, 'F', '0', '0', 'blog:article:remove', '#', 103, 1, NOW(), NULL, NULL, '');
```

> 种子数据只在**数据库首次初始化**时写入。已有库要生效，需手工执行这几条 SQL 或走方式 A。

## 5. 前端

前端菜单/路由完全由后端 `sys_menu` 驱动：菜单的组件路径 `blog/article/index` 会被动态解析为 `src/views/blog/article/index.vue`（见 `src/router/access.ts` 的 `import.meta.glob('../views/**/*.vue')`）。因此只需补 API 层与视图。

### 5.1 API 层

新建 `apps/web-antd/src/api/blog/article/`，参考 `src/api/system/post/` 的形态：

`model.d.ts`：

```typescript
export interface Article {
  id?: number;
  title?: string;
  content?: string;
  status?: string;
  publishTime?: string;
  createTime?: string;
}
```

`index.ts`：

```typescript
import type { Article } from './model';

import type { ID, IDS, PageQuery } from '#/api/common';

import { request } from '#/utils/http';

enum Api {
  articleList = '/blog/article/list',
  root = '/blog/article',
}

/** 获取文章列表 */
export function articleList(params?: PageQuery) {
  return request.get<Article[]>(Api.articleList, { params });
}

/** 查询文章详情 */
export function articleInfo(articleId: ID) {
  return request.get<Article>(`${Api.root}/${articleId}`);
}

/** 新增文章 */
export function articleAdd(data: Article) {
  return request.post(Api.root, data);
}

/** 修改文章 */
export function articleUpdate(data: Article) {
  return request.put(Api.root, data);
}

/** 删除文章 */
export function articleRemove(articleIds: IDS) {
  return request.delete(`${Api.root}/${articleIds}`);
}
```

> `request` 封装已处理响应信封解包（直接拿到 `data`）、JWT 与 clientid 头、错误提示，无需重复处理。类型 `ID/IDS/PageQuery` 见 `src/api/common.d.ts`。

### 5.2 视图

**最快的路径是复制结构最接近的现有模块再改**（列表 + 抽屉表单形态）：

```bash
cd apps/web-antd/src
cp -r views/system/post views/blog/article
```

然后对 `views/blog/article/` 做替换适配：

| 文件 | 改什么 |
|---|---|
| `index.vue` | 换成 `articleList/articleInfo/articleAdd/articleUpdate/articleRemove` 等 API；权限点改为 `blog:article:*`；字段换成 title/status/publishTime |
| `data.ts` | 列表列（columns）与搜索/表单字段定义，字段名用驼峰（与出参 alias 一致） |
| `post-drawer.vue` | 重命名为 `article-drawer.vue`，表单域换成文章的字段 |

字典、状态标签等可复用现有组件（参考 post 对状态列的渲染）。若文章正文需要富文本，可接入 `src/components/tiptap/` 或 `tinymce/`。

完成后无需注册任何前端路由——菜单配置好后刷新登录即可出现。

## 6. 验证

按顺序自查：

1. **后端启动**：`uv run main.py run --env dev` 无审计/迁移报错，日志出现「路由认证审计通过」；
2. **Swagger**：浏览器打开 `http://localhost:8011/docs`，能看到「文章管理」tag 与 5 个接口；
3. **权限闭环**：先不带 token 调 `GET /blog/article/list` 应 401；登录后调用正常返回信封 `{"code":200,...}`；用无该权限的普通角色调用应 403；
4. **前端页面**：登录后左侧出现「博客管理 → 文章管理」，完成一次 查询 → 新增 → 编辑 → 删除 全流程；
5. **操作日志**：系统管理 → 操作日志 中能看到刚才的增删改记录（`@log` 生效）；
6. **冒烟**（可选）：`uv run python -m scripts.smoke_all` 全端点回归，确认没改坏别处。

## 7. 完成清单

- [ ] `module_blog/article/` 五件套 + 两个 `__init__.py`
- [ ] `router.py` 装配 + `init_app.py` 挂载
- [ ] Alembic 迁移脚本已生成、审查并 upgrade
- [ ] 菜单与按钮权限已配置，角色已勾选
- [ ] 前端 API 层 + 视图页面
- [ ] 第 6 步验证全部通过
- [ ] ruff 检查：`uv run ruff check . && uv run ruff format .`

## 常见坑

| 现象 | 原因与处理 |
|---|---|
| 启动失败「路由认证审计失败」 | 新路由忘挂 `AuthPermission`；确属公开接口才加入 `WHITE_API_LIST_PATH` |
| 启动失败「表不存在」 | 忘了生成/应用迁移；`upgrade --env dev` |
| 前端菜单不出现 | `sys_menu` 未插入或角色未勾选；component 路径与实际视图文件不一致 |
| 菜单出现但页面空白/404 | component 拼写与 `src/views/` 下的文件路径对不上（大小写敏感） |
| 接口 403 | 权限串与菜单 `perms` 不一致，或角色未勾选对应按钮 |
| 查询参数收不到 | QueryParam 字段忘写 camelCase alias（前端按驼峰传） |
| 返回 JSON 是下划线字段 | OutSchema 序列化忘了 `by_alias=True` |
| 重复点击产生多条数据 | 写接口没加 `RepeatSubmit()` |

## 下一步

- 需要导出 Excel？参考 post 的 `/export` 接口 + `ExcelUtil.export_excel_response`
- 需要字典联动？参考 `src/components/dict/` 与字典管理模块
- 数据权限（行级过滤）如何接入，见 [菜单与权限配置 · 第 4 节](./menu-permission.md#4-数据权限行级)
