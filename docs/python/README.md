# Python 后端

Python 后端位于 `walnut-backend-python/`，技术栈为 Python 3.12、FastAPI、SQLAlchemy 2.0 异步 ORM、Alembic、Redis 和 Uvicorn。

## 开发启动

```bash
cd walnut-backend-python
uv sync
uv run main.py run --env dev
uv run pytest
uv run ruff check .
```

公共中间件先启动：

```bash
docker compose -f docker/docker-compose.middleware.yml up -d
```

## 代码入口

- `main.py`：Typer CLI，提供运行和 Alembic 命令。
- `app/init_app.py`：应用生命周期、路由、中间件和异常装配。
- `app/api/v1/`：业务模块。
- `app/core/`：数据库、认证、权限、限流、加密、文件和实时通道。
- `app/seed/`：幂等种子数据。
- `tests/`：pytest 测试。

## Python 文档

- [快速开始](./01-快速开始.md)
- [架构设计](./02-架构设计.md)
- [配置说明](./03-配置说明.md)
- [接口契约](./04-接口契约.md)
- [权限配置](./05-权限配置.md)
- [接口加解密](./06-接口加解密.md)
- [国际化](./07-国际化.md)
- [新增 CRUD 模块](./08-新增CRUD模块.md)
- [Alembic 迁移](./09-数据库迁移-Alembic.md)
- [Docker 部署](./10-Docker部署.md)
- [生产上线清单](./11-生产上线清单.md)

本目录内容只针对 Python 后端；前端和 Java 后端请从 [文档总入口](../README.md) 进入对应目录。
