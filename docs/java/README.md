# Java 后端

Java 后端位于 `walnut-backend-java/`，技术栈为 Java 25、Spring Boot 3、MyBatis-Plus、Sa-Token、Redisson 和 Flyway。

## 开发启动

```bash
cd walnut-backend-java
mvn spring-boot:run
mvn test
mvn package
```

公共中间件先启动：

```bash
docker compose -f docker/docker-compose.middleware.yml up -d
```

## 代码入口

- `src/main/java/com/walnut/seed/`：应用源码。
- `module/web/`：登录、验证码、文件和健康检查。
- `module/system/`：用户、角色、菜单、部门、字典、配置、公告、日志等管理模块。
- `common/`：响应、Sa-Token、Redis、OSS、SSE、WebSocket 等基础设施。
- `src/main/resources/db/migration/`：Flyway 建表和种子脚本。
- `src/main/resources/application-*.yml`：环境配置。

## Java 文档

- [快速开始](./01-快速开始.md)
- [架构设计](./02-架构设计.md)
- [配置说明](./03-配置说明.md)
- [接口契约](./04-接口契约.md)
- [权限配置](./05-权限配置.md)
- [接口加解密](./06-接口加解密.md)
- [国际化](./07-国际化.md)
- [新增 CRUD 模块](./08-新增CRUD模块.md)
- [Flyway 迁移](./09-数据库迁移-Flyway.md)
- [Docker 部署](./10-Docker部署.md)
- [生产上线清单](./11-生产上线清单.md)

本目录内容只针对 Java 后端；前端和 Python 后端请从 [文档总入口](../README.md) 进入对应目录。
