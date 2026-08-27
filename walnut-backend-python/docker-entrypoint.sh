#!/bin/sh
# 生产策略：应用启动前确保数据库存在并显式执行 Alembic 迁移。
# 失败即快速失败（set -e），绝不带着过期 schema 对外服务；
# 多副本部署时迁移在滚动发布前统一执行，避免应用内自动迁移的竞争。
# （建库逻辑与 Java 后端 JDBC URL 的 createDatabaseIfNotExist=true 对齐：
#   中间件的 MYSQL_DATABASE 仅在数据卷首次初始化时生效，换库名/重建卷后由此兜底。）
set -e

echo "[entrypoint] ensuring database exists..."
python - <<'PYEOF'
import os

import pymysql

conn = pymysql.connect(
    host=os.environ.get("DATABASE_HOST", "127.0.0.1"),
    port=int(os.environ.get("DATABASE_PORT", "3306")),
    user=os.environ.get("DATABASE_USER", "root"),
    password=os.environ.get("DATABASE_PASSWORD", ""),
    charset="utf8mb4",
)
db = os.environ.get("DATABASE_NAME", "walnut_seed_python")
with conn.cursor() as cur:
    cur.execute(
        f"CREATE DATABASE IF NOT EXISTS `{db}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
    )
conn.commit()
conn.close()
print(f"[entrypoint] database ensured: {db}")
PYEOF

echo "[entrypoint] applying alembic migrations..."
python main.py upgrade --env prod

exec "$@"
