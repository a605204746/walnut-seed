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
    mvn -B -ntp clean package -DskipTests

# ==============================
# Stage 2: 运行阶段
# ==============================
FROM bellsoft/liberica-openjdk-rocky:25.0.4-cds

# 统一运行时目录：日志与临时文件均位于 /walnut-backend/server 下
# 日志目录经 compose 绑定挂载到宿主机 docker/volumes/logs（见 docker-compose 中 backend.volumes 注释）
RUN mkdir -p /walnut-backend/server/logs \
    /walnut-backend/server/temp

WORKDIR /walnut-backend/server

# LOG_PATH 供 logback-plus.xml 使用，保证日志写入被挂载出来的目录
# JVM_GC 默认 ZGC（低延迟）；内存敏感环境可经 compose/.env 覆盖为 -XX:+UseG1GC（JDK25 禁止同传两个 GC 参数，故参数化而非用 JAVA_OPTS 追加）
# SERVER_PORT 与 Python 后端/前端代理保持一致（8011）
ENV SERVER_PORT=8011 LANG=C.UTF-8 LC_ALL=C.UTF-8 JAVA_OPTS="" JVM_GC="-XX:+UseZGC" \
    LOG_PATH=/walnut-backend/server/logs

EXPOSE ${SERVER_PORT}

# 复制构建阶段产物（jar 名称与 pom.xml 中 <finalName>walnut-backend</finalName> 保持一致）
COPY --from=builder /build/target/walnut-backend.jar ./app.jar

SHELL ["/bin/bash", "-c"]

ENTRYPOINT java -Djava.security.egd=file:/dev/./urandom -Dserver.port=${SERVER_PORT} \
           -XX:+HeapDumpOnOutOfMemoryError ${JVM_GC} ${JAVA_OPTS} \
           -jar app.jar
