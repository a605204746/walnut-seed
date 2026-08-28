# syntax=docker/dockerfile:1
# ==============================
# Stage 1: 构建阶段
# ==============================
FROM node:22-slim AS builder

# 设置环境变量
ENV PNPM_HOME="/pnpm"
ENV PATH="$PNPM_HOME:$PATH"
# 增加内存限制以防止构建大型项目时 OOM
ENV NODE_OPTIONS=--max-old-space-size=8192
ENV TZ=Asia/Shanghai

# 启用 corepack 以使用 pnpm
# 无 TTY 构建时关闭下载确认提示，并走国内镜像加速 pnpm 下载
ENV COREPACK_ENABLE_DOWNLOAD_PROMPT=0
ENV COREPACK_NPM_REGISTRY=https://registry.npmmirror.com
RUN npm i -g corepack

WORKDIR /app

# 依赖清单先行：只拷 workspace manifests（含 .npmrc 的 npmmirror 源），业务源码变更时
# 命中层缓存、跳过 pnpm install 整层。--parents 保留相对路径（Dockerfile 1.7+ 语法），
# 新增 workspace 包时需同步补对应 glob。
COPY --parents \
    package.json pnpm-lock.yaml pnpm-workspace.yaml .npmrc \
    apps/*/package.json \
    internal/*/package.json \
    internal/lint-configs/*/package.json \
    packages/*/package.json \
    packages/@core/*/package.json \
    packages/@core/base/*/package.json \
    packages/@core/ui-kit/*/package.json \
    packages/effects/*/package.json \
    scripts/*/package.json \
    ./

# 安装依赖
# --frozen-lockfile: 确保使用 lock 文件中的版本
# --mount=type=cache: 缓存 pnpm 存储，加速后续构建
# --ignore-scripts: 跳过根 postinstall 的全量 stub 构建（本层只有 manifests 没有源码，跑了必失败；
#   stub 移至源码拷贝后单独执行，见下方）
RUN --mount=type=cache,id=pnpm,target=/pnpm/store \
    pnpm install --frozen-lockfile --ignore-scripts

# 复制项目文件（依赖层之后，仅业务源码变更影响本层起）
COPY . .

# 预构建内部包（stub）：turbo ^build 只调度 dependencies，而 @vben/vite-config 这类
# devDependency 的产物（exports 指向 dist/）不被其覆盖，须在此先行构建。
# （原先由 postinstall 完成；移到这里以保住上面的 install 层缓存）
RUN pnpm -r run --if-present stub

# 构建 web-antd 应用
# web-antd 只有 build:prod 脚本（没有 build），根脚本 build:antd 等价于
# turbo run build:prod --filter=@walnut-seed/web-admin，只构建需要的应用
RUN pnpm run build:antd

# ==============================
# Stage 2: 生产环境运行阶段
# ==============================
FROM nginx:stable-alpine AS production

# 后端服务地址（VM 部署默认 127.0.0.1:8011，Docker Compose 部署时通过环境变量传入）
ENV BACKEND_HOST=127.0.0.1
ENV BACKEND_PORT=8011

# 清理默认配置，以模板形式复制 Nginx 配置（启动时由 envsubst 渲染）
# nginx.conf 已统一移到仓库 docker/config/ 目录，经 compose additional_contexts(deploy) 注入；
# 单独 docker build 时需加 --build-context deploy=<仓库根>/docker
RUN rm -rf /etc/nginx/conf.d/default.conf
COPY --from=deploy config/nginx.conf /etc/nginx/nginx.conf.template

# 复制构建产物到 Nginx 目录
# Vite 默认构建输出在 apps/web-antd/dist
COPY --from=builder /app/apps/web-antd/dist /usr/share/nginx/html

# 暴露端口 (监听 80 端口)
EXPOSE 80

# 启动时先用 envsubst 渲染配置（只替换 ${BACKEND_HOST}/${BACKEND_PORT}，避免污染 nginx 内置变量）
CMD ["/bin/sh", "-c", "envsubst '${BACKEND_HOST} ${BACKEND_PORT}' < /etc/nginx/nginx.conf.template > /etc/nginx/nginx.conf && nginx -g 'daemon off;'"]
