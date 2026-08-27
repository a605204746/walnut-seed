"""Alembic 迁移辅助：构建配置与程序化 upgrade。

- CLI（main.py）与应用启动（init_app lifespan）共用同一入口；
- 路径一律取绝对路径（path_conf.BASE_DIR），不依赖调用方 CWD。
"""

import asyncio

from alembic import command
from alembic.config import Config

from app.config.path_conf import BASE_DIR


def build_alembic_config() -> Config:
    """构建 Alembic 配置（绝对路径，CWD 无关）。"""
    cfg = Config(str(BASE_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BASE_DIR / "app" / "alembic"))
    cfg.set_main_option("prepend_sys_path", str(BASE_DIR))
    return cfg


async def upgrade_to_head() -> None:
    """在应用事件循环内执行 ``alembic upgrade head``。

    Alembic 命令层是同步 API，且 env.py 内部通过 ``asyncio.run`` 自建事件循环，
    无法在运行中的事件循环里直接调用 —— 委托给工作线程执行。
    env.py 使用自建的 NullPool 引擎，与应用连接池零共享，线程内运行安全。
    """
    await asyncio.to_thread(command.upgrade, build_alembic_config(), "head")
