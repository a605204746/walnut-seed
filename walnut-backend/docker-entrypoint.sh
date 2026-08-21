#!/bin/sh
# 生产策略：应用启动前显式执行 Alembic 迁移。
# 失败即快速失败（set -e），绝不带着过期 schema 对外服务；
# 多副本部署时迁移在滚动发布前统一执行，避免应用内自动迁移的竞争。
set -e

echo "[entrypoint] applying alembic migrations..."
python main.py upgrade --env prod

exec "$@"
