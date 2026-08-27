# WalnutSeed 文档

项目文档按三条开发线组织：前端、Python 后端、Java 后端。每个目录都包含本路线所需的接口、权限、配置、部署和开发说明，进入对应目录即可开始工作。

## 三条开发线

### 前端

- [前端入口](./frontend/README.md)
- [接口契约](./frontend/01-接口契约.md)
- [权限与动态路由](./frontend/02-权限与动态路由.md)
- [接口加解密](./frontend/03-接口加解密.md)
- [国际化](./frontend/04-国际化.md)

### Python 后端

- [Python 后端入口](./python/README.md)
- [快速开始](./python/01-快速开始.md)
- [架构设计](./python/02-架构设计.md)
- [配置说明](./python/03-配置说明.md)
- [接口契约](./python/04-接口契约.md)
- [权限配置](./python/05-权限配置.md)
- [接口加解密](./python/06-接口加解密.md)
- [国际化](./python/07-国际化.md)
- [新增 CRUD 模块](./python/08-新增CRUD模块.md)
- [Alembic 迁移](./python/09-数据库迁移-Alembic.md)
- [Docker 部署](./python/10-Docker部署.md)
- [生产上线清单](./python/11-生产上线清单.md)

### Java 后端

- [Java 后端入口](./java/README.md)
- [快速开始](./java/01-快速开始.md)
- [架构设计](./java/02-架构设计.md)
- [配置说明](./java/03-配置说明.md)
- [接口契约](./java/04-接口契约.md)
- [权限配置](./java/05-权限配置.md)
- [接口加解密](./java/06-接口加解密.md)
- [国际化](./java/07-国际化.md)
- [新增 CRUD 模块](./java/08-新增CRUD模块.md)
- [Flyway 迁移](./java/09-数据库迁移-Flyway.md)
- [Docker 部署](./java/10-Docker部署.md)
- [生产上线清单](./java/11-生产上线清单.md)

## 如何选择后端

| 项目 | Python | Java |
| --- | --- | --- |
| Web 框架 | FastAPI | Spring Boot 3 |
| 数据访问 | SQLAlchemy Async | MyBatis-Plus |
| 数据迁移 | Alembic | Flyway |
| 认证组件 | JWT + Redis 会话 | Sa-Token + JWT |
| 启动命令 | `uv run main.py run --env dev` | `mvn spring-boot:run` |
| 数据库 | `walnut_seed_python` | `walnut_seed_java` |

前端与两套后端共享接口形状和权限命名，但后端代码、数据库、迁移脚本和运行时配置相互独立。实际项目建议只选择一套后端作为主线。

## 常见问题

- [FAQ](./faq.md)
