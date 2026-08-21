# WalnutSeed 文档

> 项目文档索引。项目介绍、技术栈与快速启动见根目录 [README（中文）](../README.md) / [README（英文）](../README.en.md)，本目录聚焦「怎么在上面做开发」。

## 推荐阅读路径

- **第一次接触项目** → 根目录 README 快速开始 → [从零新增一个业务模块](./guide/new-crud-module.md)
- **日常开发** → `guide/` 开发教程按需查阅
- **部署上线** → `deployment/`
- **想改框架本身** → `architecture/` 了解设计理由再动手

## 开发教程（guide/）

| 文档 | 内容 | 状态 |
|---|---|---|
| [从零新增一个业务模块](./guide/new-crud-module.md) | 端到端教程：五件套 → 路由注册 → 迁移 → 菜单权限 → 前端页面 → 验证 | ✅ 完整 |
| [菜单与权限配置](./guide/menu-permission.md) | 菜单/按钮/数据三层权限的配置与排查 | ✅ 完整 |
| [Alembic 迁移实战](./guide/alembic-migration.md) | 迁移机制、工作流演练、存量库接入、故障处理 | ✅ 完整 |
| [接口加解密配置](./guide/api-encryption.md) | RSA+AES 混合加密原理、两对密钥配对、前后端配置与排查 | ✅ 完整 |
| [i18n 使用](./guide/i18n.md) | Accept-Language 机制、新增消息、接入现状与边界 | ✅ 完整 |

## 架构说明（architecture/）

| 文档 | 内容 | 状态 |
|---|---|---|
| [整体架构](./architecture/overview.md) | 模块划分、请求生命周期、前后端契约、横切能力挂载点 | ✅ 完整 |
| [后端设计](./architecture/backend-design.md) | 响应信封与异常映射、认证链路、中间件栈、数据层约定 | ✅ 完整 |

## 部署运维（deployment/）

| 文档 | 内容 | 状态 |
|---|---|---|
| [Docker 全栈部署](./deployment/docker-fullstack.md) | 编排结构、镜像构建与 nginx、配置注入、持久化与健康检查、运维操作 | ✅ 完整 |
| [生产上线清单](./deployment/production-checklist.md) | 启动门禁、密钥与账号、网络与代理、运行参数、上线后验证 | ✅ 完整 |

## 常见问题

- [FAQ](./faq.md) —— 开发与部署中的高频问题（✅ 完整，持续补充）

---

## 文档约定

- 每篇文档头部标注**更新日期**，内容落后于代码时请同步修订或更新标注
- 教程类文档以「可验证的终点」收尾：读者按步骤做完后能自查结果
- 与根 README 重复的内容（端口表、命令清单）此处不再复制，直接链接
