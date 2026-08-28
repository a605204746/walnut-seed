# ==============================
# Stage 1: 构建阶段（Maven 打包在镜像内完成，宿主机无需预先打包）
# ==============================
FROM maven:3.9-eclipse-temurin-25 AS builder

WORKDIR /build

# 构建上下文为本目录（见 docker-compose 中 backend.build: ../walnut-backend-java，
# 与 Python 后端服务同构）；依赖仓库镜像已在 pom.xml <repositories> 中声明（华为云），
# 无需额外 settings.xml
COPY pom.xml .
COPY src ./src

# --mount=type=cache: 缓存 Maven 本地仓库，重建镜像时不重复下载依赖
RUN --mount=type=cache,target=/root/.m2 \
    mvn -B -ntp package -DskipTests

# ==============================
# Stage 2: 运行阶段（alpine musl 变体比 noble 小 ~170MB；若镜像源不可达再回退 25-jre）
# ==============================
FROM eclipse-temurin:25-jre-alpine

# 非 root 运行（uid 1000，与 Python 后端 appuser 对齐；宿主机日志目录需对该 uid 可写）。
# alpine 无内置非 root 用户，busybox adduser 创建
RUN adduser -D -u 1000 appuser \
    && mkdir -p /walnut-backend/server/logs /walnut-backend/server/temp \
    && chown -R appuser:appuser /walnut-backend

WORKDIR /walnut-backend/server

# LOG_PATH 供 logback-plus.xml 使用，保证日志写入被挂载出来的目录
# JVM_GC 默认 ZGC（低延迟）；内存敏感环境可经 compose/.env 覆盖为 -XX:+UseG1GC（JDK25 禁止同传两个 GC 参数，故参数化而非用 JAVA_OPTS 追加）
# SERVER_PORT 与 Python 后端/前端代理保持一致（8011）
ENV SERVER_PORT=8011 LANG=C.UTF-8 LC_ALL=C.UTF-8 JAVA_OPTS="" JVM_GC="-XX:+UseZGC" \
    LOG_PATH=/walnut-backend/server/logs

EXPOSE ${SERVER_PORT}

# 复制构建阶段产物（jar 名称与 pom.xml 中 <finalName>walnut-backend</finalName> 保持一致）
COPY --from=builder --chown=appuser:appuser /build/target/walnut-backend.jar ./app.jar

# alpine 无 bash，用默认 sh（ENTRYPOINT 的 ${VAR} 展开在 sh 下同样生效）
SHELL ["/bin/sh", "-c"]
USER appuser

# HeapDumpPath 指向挂载目录：OOM 现场落在宿主机 docker/volumes/logs，容器重建后不丢
ENTRYPOINT java -Dserver.port=${SERVER_PORT} \
           -XX:+HeapDumpOnOutOfMemoryError -XX:HeapDumpPath=${LOG_PATH} \
           ${JVM_GC} ${JAVA_OPTS} \
           -jar app.jar
