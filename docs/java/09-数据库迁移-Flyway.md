# Flyway 迁移

Java 后端的数据库结构由 `walnut-backend-java/src/main/resources/db/migration/` 下的版本化 SQL 管理，应用启动时由 Flyway 按版本顺序执行。

## 工作流

1. 修改 Entity、Mapper 或业务模型。
2. 新增递增版本脚本，例如 `V2__add_article_table.sql`。
3. 在本地启动 Java 后端，确认 Flyway 执行成功。
4. 检查 SQL 的索引、约束、初始数据和回滚策略。
5. 将脚本与代码放在同一个 Pull Request 中。

生产环境不要手工修改表结构。迁移失败时先查看应用日志和 Flyway 历史表，再修复脚本或补充后续迁移，不要直接删除历史脚本。

Python 后端使用 Alembic，流程见 [Alembic 迁移](../python/09-数据库迁移-Alembic.md)。
