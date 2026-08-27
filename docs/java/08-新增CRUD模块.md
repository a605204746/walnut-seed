# Java 新增 CRUD 模块

Java 新业务模块应遵守现有 `module/system` 的分层风格，并保持 [Java 接口契约](./04-接口契约.md) 不变。

## 推荐步骤

1. 在对应业务域创建 Entity、DTO/VO、Mapper、Service、Controller。
2. 为表结构新增 Flyway 版本脚本，见 [Flyway 迁移](./09-数据库迁移-Flyway.md)。
3. Controller 统一使用项目响应封装，并接入 Sa-Token 权限校验和操作日志。
4. 为列表接口实现分页、排序和必要的数据权限过滤。
5. 在 `sys_menu` 中增加菜单、按钮权限，并确认权限串与前端逐字一致。
6. 在 `walnut-frontend/apps/web-antd/src/views/` 增加页面和 API 类型。
7. 使用 Java 单元测试、前端构建和接口冒烟测试验证。

可以参考现有 `SysPostController`、`SysPostService`、`SysPostMapper` 等岗位管理模块。
