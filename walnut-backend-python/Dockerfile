# 后端镜像：两阶段构建（builder 装依赖 → 运行层只留 venv+代码，不含 uv/uvx）

# ==============================
# Stage 1: 依赖构建（uv 按 uv.lock 冻结安装生产依赖）
# ==============================
FROM python:3.12-slim AS builder

# uv 固定版本（与本机开发版本一致，保证解析/安装行为可复现），不用 latest
COPY --from=ghcr.io/astral-sh/uv:0.11.2 /uv /usr/local/bin/

WORKDIR /app

# 先装生产依赖（利用层缓存，代码变更不触发重装）
COPY pyproject.toml uv.lock ./
# 缓存挂载：wheel 缓存留在镜像层外，重建更快、层更小
# --compile-bytecode：安装期预编译 .pyc，容器重建后首次 import 免现场编译
RUN --mount=type=cache,id=uv,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project --compile-bytecode

# ==============================
# Stage 2: 运行层（python + venv + 代码，无 uv；非 root 运行）
# ==============================
FROM python:3.12-slim

# 专用低权限运行用户（固定 uid 1000，便于卷属主对齐）
RUN useradd --create-home --uid 1000 appuser

# 运行时数据目录：后端代码把日志/上传写到"后端目录的上一级"的 data/，
# 容器内 WORKDIR=/app 即落在 /data（见 app/config/path_conf.py 与 compose 挂载）。
# 先建好并归属 appuser：本地 Docker 绑定挂载时需确保宿主机目录对 uid 1000 可写。
RUN mkdir -p /data && chown appuser:appuser /data

WORKDIR /app

# 仅拷贝构建好的 venv，直接以其 python 运行
COPY --from=builder /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"

COPY --chown=appuser:appuser . .

# 启动入口：先执行 Alembic 迁移（upgrade head），成功后再启动应用
COPY --chmod=755 --chown=appuser:appuser docker-entrypoint.sh ./
ENTRYPOINT ["./docker-entrypoint.sh"]

# 配置全部经 compose 环境变量注入（env/ 目录不进镜像）
ENV ENVIRONMENT=prod \
    PYTHONUNBUFFERED=1

# 非 root 运行：缩小容器被攻破后的影响面（健康检查在 compose 层定义，不在此重复）
USER appuser

EXPOSE 8011

CMD ["python", "main.py", "run", "--env", "prod"]
