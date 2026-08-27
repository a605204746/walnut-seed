import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import create_async_engine

from app.config.path_conf import ALEMBIC_VERSION_DIR
from app.config.setting import settings
from app.core.base_model import MappedBase
from app.utils.import_util import ImportUtil

# 确保 alembic 版本目录存在
ALEMBIC_VERSION_DIR.mkdir(parents=True, exist_ok=True)

# 自动发现所有模型（新进程内首次导入即注册到 MappedBase.metadata；
# 注意不要清空 metadata——若模型模块已被导入，清空会导致 autogenerate 对比空目标而误删全部表）
found_models = ImportUtil.find_models(MappedBase)
print(f"[alembic] found {len(found_models)} models")

alembic_config = context.config

if alembic_config.config_file_name is not None:
    # disable_existing_loggers=False：应用内执行迁移时，避免禁用 uvicorn 等已创建的日志器
    fileConfig(alembic_config.config_file_name, disable_existing_loggers=False)

target_metadata = MappedBase.metadata
alembic_config.set_main_option("sqlalchemy.url", settings.ASYNC_DB_URI)


def run_migrations_offline() -> None:
    url = alembic_config.get_main_option("sqlalchemy.url")
    if url is None:
        raise ValueError("数据库URL未正确配置，请检查环境配置文件")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    url = alembic_config.get_main_option("sqlalchemy.url")
    if url is None:
        raise ValueError("数据库URL未正确配置，请检查环境配置文件")
    connectable = create_async_engine(url, poolclass=pool.NullPool)

    async def run_async_migrations() -> None:
        async with connectable.connect() as connection:
            await connection.run_sync(do_run_migrations)
        await connectable.dispose()

    def do_run_migrations(connection: Connection) -> None:
        def process_revision_directives(context, revision, directives) -> None:
            script = directives[0]
            all_empty = all(ops.is_empty() for ops in script.upgrade_ops_list)
            if all_empty:
                directives[:] = []
                print("[alembic] 未检测到模型变更，不生成迁移文件")
            else:
                print("[alembic] 检测到模型变更，生成迁移文件")

        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
            transaction_per_migration=True,
            process_revision_directives=process_revision_directives,
        )
        with context.begin_transaction():
            context.run_migrations()

    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
