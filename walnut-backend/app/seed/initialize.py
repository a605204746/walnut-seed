"""种子数据初始化脚本。

在数据库迁移（Alembic upgrade）完成后调用：若系统表为空，则加载 ``app/seed/sql`` 下
MySQL 方言的种子数据（mysql_data.sql），完成默认管理员、角色、菜单、部门、
岗位、字典、参数、客户端等初始数据写入。
"""

from sqlalchemy import text

from app.config import path_conf
from app.core.database import async_engine
from app.core.logger import logger


class InitializeData:
    async def init_db(self) -> None:
        """初始化数据库基础数据（幂等：已有数据时跳过）。"""
        try:
            async with async_engine.connect() as conn:
                result = await conn.execute(text("SELECT COUNT(*) FROM sys_user"))
                count = result.scalar() or 0
            if count > 0:
                logger.debug("系统表已存在数据，跳过种子数据初始化")
                return
        except Exception as e:
            logger.warning("种子数据初始化前置检查失败（表可能未创建）: {}", e)
            return

        sql_file = path_conf.SCRIPT_DIR / "mysql_data.sql"
        if not sql_file.exists():
            logger.warning("种子数据文件不存在，跳过初始化: {}", sql_file)
            return

        statements = [line.strip().rstrip(";") for line in sql_file.read_text(encoding="utf-8").splitlines() if line.strip().upper().startswith("INSERT")]
        try:
            async with async_engine.begin() as conn:
                for stmt in statements:
                    # 转义冒号，避免 SQLAlchemy text() 将 ':roleId' 等误判为绑定参数
                    await conn.execute(text(stmt.replace(":", "\\:")))
            logger.info("✅ 种子数据初始化完成（{} 条）", len(statements))
        except Exception as e:
            logger.error("❌ 种子数据初始化失败: {}", e)
