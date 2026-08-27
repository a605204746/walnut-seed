import os
import sys
from typing import Annotated

import typer
import uvicorn
from alembic import command
from fastapi import FastAPI

from app.common.enums import EnvironmentEnum
from app.config.setting import settings
from app.utils.banner import worship

walnut_cli = typer.Typer()


def _apply_env(env: EnvironmentEnum) -> None:
    """切换运行环境：设置 ENVIRONMENT 并按新环境重建配置。

    必须重绑本模块的 ``settings`` 引用——各命令（含 run）读取的是
    本模块导入时的绑定，仅刷新 setting 模块内部对象不够。
    """
    global settings
    os.environ["ENVIRONMENT"] = env.value
    from app.config.setting import reload_settings

    settings = reload_settings()


def create_app() -> FastAPI:
    """创建 FastAPI 应用实例并完成日志、中间件、路由与静态资源注册。

    启动安全门禁（服务对外可用前执行）：
    - validate_security_settings：密钥校验先行（RSA 无效会停用 ApiDecryptMiddleware，须在中间件注册前）；
    - audit_routes_auth：路由注册完成后审计白名单外路由的认证依赖。
    """
    from app.init_app import (
        audit_routes_auth,
        lifespan,
        register_docs,
        register_exceptions,
        register_frontend,
        register_middlewares,
        register_routers,
        register_static,
        validate_security_settings,
    )

    validate_security_settings()
    app = FastAPI(**settings.FASTAPI_CONFIG, lifespan=lifespan)
    register_exceptions(app)
    register_middlewares(app)
    register_routers(app)
    register_static(app)
    register_docs(app)
    register_frontend(app)
    audit_routes_auth(app)
    return app


@walnut_cli.command(name="run", help="启动 WalnutSeed 后端, 运行 uv run main.py run --env=dev（默认 dev）")
def run(
    env: Annotated[EnvironmentEnum, typer.Option("--env", help="运行环境 (dev, prod)")] = EnvironmentEnum.DEV,
) -> None:
    """按指定环境加载配置并启动 uvicorn（开发环境开启 reload）。"""
    _apply_env(env)
    typer.secho(message=f"{worship()}", fg=typer.colors.GREEN)
    uvicorn.run(
        app="main:create_app",
        host=settings.SERVER_HOST,
        port=settings.SERVER_PORT,
        reload=env.value == EnvironmentEnum.DEV.value,
        factory=True,
        log_config=None,
        timeout_graceful_shutdown=5,
    )


@walnut_cli.command(name="revision", help="对比模型与数据库生成 Alembic 迁移脚本, 运行 uv run main.py revision --env=dev -m '描述'")
def revision(
    env: Annotated[EnvironmentEnum, typer.Option("--env", help="运行环境 (dev, prod)")] = EnvironmentEnum.DEV,
    message: Annotated[str, typer.Option("-m", "--message", help="迁移描述（生成文件名后缀）")] = "迁移脚本",
) -> None:
    """autogenerate 对比 ORM 模型与数据库差异，生成迁移脚本（生成后务必人工审查）。"""
    _apply_env(env)
    from app.core.migrate import build_alembic_config

    command.revision(build_alembic_config(), autogenerate=True, message=message)
    typer.echo("迁移脚本已生成，请人工审查后再提交。")


@walnut_cli.command(name="upgrade", help="应用 Alembic 迁移到最新版本, 运行 uv run main.py upgrade --env=dev")
def upgrade(
    env: Annotated[EnvironmentEnum, typer.Option("--env", help="运行环境 (dev, prod)")] = EnvironmentEnum.DEV,
) -> None:
    """执行 upgrade head：按版本链顺序应用所有未执行的迁移。"""
    _apply_env(env)
    from app.core.migrate import build_alembic_config

    command.upgrade(build_alembic_config(), "head")
    typer.echo("所有迁移已应用。")


@walnut_cli.command(name="downgrade", help="回退 Alembic 迁移, 运行 uv run main.py downgrade --env=dev -r -1")
def downgrade(
    env: Annotated[EnvironmentEnum, typer.Option("--env", help="运行环境 (dev, prod)")] = EnvironmentEnum.DEV,
    rev: Annotated[str, typer.Option("-r", "--revision", help="目标版本（-1 表示回退一步，base 表示全部回退）")] = "-1",
) -> None:
    """回退迁移（注意：回退初始迁移会删除全部表；MySQL DDL 非事务，失败需人工检查）。"""
    _apply_env(env)
    from app.core.migrate import build_alembic_config

    command.downgrade(build_alembic_config(), rev)
    typer.echo(f"已回退到 {rev}。")


@walnut_cli.command(name="stamp", help="标记存量数据库版本（不执行 DDL）, 运行 uv run main.py stamp --env=dev")
def stamp(
    env: Annotated[EnvironmentEnum, typer.Option("--env", help="运行环境 (dev, prod)")] = EnvironmentEnum.DEV,
    rev: Annotated[str, typer.Option("-r", "--revision", help="要标记的版本")] = "head",
) -> None:
    """仅写 alembic_version 不执行迁移：用于结构已等同模型的存量库一次性接入。"""
    _apply_env(env)
    from app.core.migrate import build_alembic_config

    command.stamp(build_alembic_config(), rev)
    typer.echo(f"已标记为 {rev}。")


@walnut_cli.command(name="current", help="查看数据库当前迁移版本, 运行 uv run main.py current --env=dev")
def current(
    env: Annotated[EnvironmentEnum, typer.Option("--env", help="运行环境 (dev, prod)")] = EnvironmentEnum.DEV,
) -> None:
    """显示数据库 alembic_version 中的当前版本。"""
    _apply_env(env)
    from app.core.migrate import build_alembic_config

    command.current(build_alembic_config(), verbose=True)


@walnut_cli.command(name="history", help="查看迁移版本历史, 运行 uv run main.py history --env=dev")
def history(
    env: Annotated[EnvironmentEnum, typer.Option("--env", help="运行环境 (dev, prod)")] = EnvironmentEnum.DEV,
) -> None:
    """列出全部迁移版本链。"""
    _apply_env(env)
    from app.core.migrate import build_alembic_config

    command.history(build_alembic_config(), verbose=True)


if __name__ == "__main__":
    # 裸跑（python main.py）或只带选项（如 --env prod）时等价于 run 命令，
    # 默认 dev 环境启动，方便 IDE 直接运行 main.py；--help 仍显示完整命令菜单
    if len(sys.argv) == 1 or (sys.argv[1].startswith("-") and sys.argv[1] not in {"--help", "-h"}):
        sys.argv.insert(1, "run")
    walnut_cli()
