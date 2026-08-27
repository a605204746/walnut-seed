# Alembic 迁移实战

> 更新日期：2026-08-19 · 适用版本：WalnutSeed v1.0
> 基础命令与执行时机见 [Python 后端入口](./README.md)，本文聚焦机制原理与实战细节。

本项目 Schema 的唯一事实来源是 `walnut-backend-python/app/alembic/versions/` 下的迁移脚本，**没有**启动时 `create_all`。这篇教程讲清楚：迁移是怎么跑起来的、日常工作流怎么走、出了问题怎么救。

## 1. 迁移是怎么跑起来的

理解机制能帮你排查 90% 的迁移问题。整体是「一套配置、两条触发路径」：

### 1.1 统一入口：`build_alembic_config()`

`app/core/migrate.py` 提供 CLI 与应用启动**共用**的配置构建：

```python
def build_alembic_config() -> Config:
    """构建 Alembic 配置（绝对路径，CWD 无关）。"""
    cfg = Config(str(BASE_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BASE_DIR / "app" / "alembic"))
    cfg.set_main_option("prepend_sys_path", str(BASE_DIR))
    return cfg
```

要点：

- 路径全部用 `BASE_DIR` 拼绝对值，**与你在哪个目录执行命令无关**；
- `alembic.ini` 里的 `sqlalchemy.url` 只是占位符，真实数据库 URL 由 `env.py` 从 `settings.ASYNC_DB_URI` 注入——**配置以代码为准**。

### 1.2 模型自动发现（新增模型无需手工注册）

`app/alembic/env.py` 在构建 `target_metadata` 前先扫描模型：

```python
found_models = ImportUtil.find_models(MappedBase)   # rglob("**/model.py") 逐个 import
target_metadata = MappedBase.metadata
alembic_config.set_main_option("sqlalchemy.url", settings.ASYNC_DB_URI)
```

`ImportUtil.find_models`（`app/utils/import_util.py`）递归找出所有 `model.py` 并 import，触发 ORM 注册。**所以你新增的业务模型只要放在 `model.py` 里、继承 `BaseEntity`，autogenerate 就能自动看到它**，不需要在任何地方手工登记。

约束/索引命名约定（`NAMING_CONVENTION`，定义于 `app/core/base_model.py`）挂在 `MappedBase.metadata` 上，随 `target_metadata` 自动生效——这就是生成脚本里约束名形如 `op.f("pk_sys_client")` 的原因。

### 1.3 两条触发路径

| 环境 | 触发点 | 失败行为 |
| --- | --- | --- |
| dev（本机） | `lifespan` 启动时按 `DATABASE_AUTO_MIGRATE=True` 自动执行 | 仅告警，不阻断启动 |
| prod（Docker） | `docker-entrypoint.sh` 在应用启动前显式执行 | `set -e` 快速失败，绝不带病上线 |

**dev 路径**（`app/init_app.py` 的 `lifespan`）：

```python
try:
    from app.core.base_model import MappedBase
    from app.utils.import_util import ImportUtil

    ImportUtil.find_models(MappedBase)          # 兜底：确保模型全部注册
    if settings.DATABASE_AUTO_MIGRATE:
        from app.core.migrate import upgrade_to_head
        await upgrade_to_head()
        logger.info("✅ Alembic 迁移已应用到 head")
    from app.seed.initialize import InitializeData
    await InitializeData().init_db()            # 迁移后播种
except Exception as e:
    logger.warning("⚠️ 数据库初始化跳过/失败: {}", e)
```

整个块被 try/except 包住——本地库随起随建，失败不该挡住开发。测试里 `tests/conftest.py` 会强制 `DATABASE_AUTO_MIGRATE=false`，避免测试动真库。

**prod 路径**（`docker-entrypoint.sh`，全文就这几行）：

```sh
set -e
echo "[entrypoint] applying alembic migrations..."
python main.py upgrade --env prod
exec "$@"
```

生产关掉自动迁移（`DATABASE_AUTO_MIGRATE` 默认 `False`），由 entrypoint 前置显式执行——**多副本部署时迁移只跑一次、无竞争**，失败则容器直接退出，不带着过期 Schema 对外服务。

> `upgrade_to_head()` 用 `asyncio.to_thread` 把同步的 Alembic 命令丢进工作线程，因为 `env.py` 内部会 `asyncio.run` 自建事件循环（不能在运行中的 loop 里嵌套调用），且用的是自建 `NullPool` 引擎，与应用连接池零共享。这套机制你不用碰，知道"迁移跑在独立线程+独立连接"即可。

## 2. 标准工作流演练

以「给文章表加一列 `author`」为例，完整走一遍。

**① 改模型**（`app/api/v1/module_blog/article/model.py`）：

```python
author: Mapped[str | None] = mapped_column(String(50), default=None, nullable=True, comment="作者")
```

**② 生成迁移**：

```bash
cd walnut-backend-python
uv run main.py revision --env dev -m "文章表新增作者"
```

底层是 `command.revision(cfg, autogenerate=True, message=...)`。命令会先 `_apply_env()` 设置 `ENVIRONMENT=dev` 并重建配置（`reload_settings()`），再惰性导入 `build_alembic_config`——所以 `--env` 决定了迁移连的是哪个库。控制台会打印 `[alembic] 检测到模型变更，生成迁移文件`，新脚本落在 `app/alembic/versions/`。

> 如果模型没实际变更，`process_revision_directives` 钩子会清空指令、**不生成空迁移文件**，控制台打印 `[alembic] 未检测到模型变更，不生成迁移文件`。

**③ 人工审查脚本**（这步不能省，见第 3 节 checklist）。加列场景生成内容大致：

```python
def upgrade() -> None:
    op.add_column("blog_article", sa.Column("author", sa.String(length=50), nullable=True, comment="作者"))

def downgrade() -> None:
    op.drop_column("blog_article", "author")
```

**④ 应用到本地库并验证**：

```bash
uv run main.py upgrade --env dev
```

注意 `upgrade` 命令**固定升到 head**（底层 `command.upgrade(cfg, "head")`），没有 `-r` 参数。

**⑤ 迁移脚本随代码一起提交**。生产由 entrypoint 自动应用，无需额外操作。

## 3. autogenerate 的盲区与审查 checklist

`env.py` 里开启了 `compare_type=True` 和 `compare_server_default=True`，但 autogenerate 仍有覆盖不到的场景，**生成的脚本必须人工过一遍**：

| 场景 | autogenerate 的表现 | 怎么办 |
|---|---|---|
| 数据迁移（回填、清洗） | 完全不生成 | 在 `upgrade()` 里手写 `op.execute(...)` |
| 列改名 | 识别成「删旧列 + 加新列」，数据丢失 | 改成 `op.alter_column` 改名，或先加列→迁数据→删旧列 |
| 表改名 | 同上，识别成删表+建表 | 手写 `op.rename_table` |
| 类型收窄（如 `String(100)`→`String(50)`） | 可能生成，但超长数据会导致执行失败 | 先校验/清洗存量数据再迁 |
| 索引微调、约束语义变化 | 视情况 | 对照需求确认 |

审查 checklist：

1. `upgrade()` 与 `downgrade()` 是否互为逆操作？
2. 有没有被误判成 drop+create 的改名？
3. 涉及 `op.execute` 的原始 SQL 在目标 MySQL 版本上可执行吗？
4. 约束/索引名是否符合 `NAMING_CONVENTION`（`ix_*`/`uq_*`/`pk_*`）？
5. 大表的 DDL 是否需要考虑锁表时长（必要时分批）？

## 4. 存量库接入（一次性）

旧版通过 `create_all` 建库、结构已等同模型的数据库，用 `stamp` 写入版本标记即可接入：

```bash
uv run main.py stamp --env dev     # 默认 stamp 到 head，可用 -r 指定版本
```

`stamp` **只写 `alembic_version` 表，不执行任何 DDL**。

⚠️ **切勿对未 stamp 的存量库直接 `upgrade`**——迁移会尝试创建已存在的表而失败。Docker 实例更简单的做法是删除 `docker/volumes` 重建。

**命名收敛导致的表面 diff**：旧库的约束/索引是数据库匿名命名的，stamp 后首次 `revision` 可能出现一批「索引/约束改名」的 diff（从匿名名改成 `NAMING_CONVENTION` 名）。这是收敛命名的正常现象——保留（推荐，命名从此可预测）或手工剪掉均可，但别误以为是模型不一致。

## 5. 故障处理

### MySQL DDL 不受事务保护

虽然 `env.py` 配了 `transaction_per_migration=True`，但 **MySQL 的 DDL 隐式提交、不受事务回滚保护**。迁移中途失败可能留下半应用的 Schema：

1. 用 `uv run main.py current --env dev` 看当前版本号，对照失败脚本判断应用到了哪一步；
2. 直接连库核对实际表结构；
3. 手工补齐/回退差异后，重新 `upgrade`，或用 `stamp -r <正确版本>` 把版本标记对齐到真实 Schema。

### 多分支版本链（multiple heads）

两人各自生成迁移、`down_revision` 指向同一个父版本时，版本链分叉，`upgrade` 会报 multiple heads。处理：

- 简单情况：把其中一个脚本的 `down_revision` 改成另一个的 `revision`，串成一条链；
- 或保留分支，用 `stamp -r` 明确指定目标（不推荐，易乱）。

建议团队层面规避：迁移脚本随 PR 提交，合并前 rebase 时顺手检查版本链是否分叉。

### 回退的风险边界

```bash
uv run main.py downgrade --env dev -r -1     # 回退一步
uv run main.py downgrade --env dev -r base   # 回退全部
```

`downgrade` 底层是 `command.downgrade(cfg, rev)`，默认 `-r -1`。**回退初始迁移（`51e22ab7d9b4_init_schema`）会删除全部表**——只在沙箱库操作。MySQL DDL 非事务，回退同样可能半途失败，处理思路同上。

## 6. 团队协作约定

- **迁移脚本与代码同 PR 提交**：改了 `model.py` 就必须带上对应的 `versions/` 脚本，否则他人拉代码后 Schema 对不上；
- **生产不手工动库**：一切 Schema 变更走迁移脚本，由 entrypoint 应用；
- **生成后必审查**：autogenerate 是起点不是终点（见第 3 节）；
- **合并前查版本链**：避免 multiple heads 带到主干。

## 相关命令速查

| 命令 | 作用 |
|---|---|
| `uv run main.py revision --env dev -m "描述"` | autogenerate 生成迁移 |
| `uv run main.py upgrade --env dev` | 升级到 head |
| `uv run main.py downgrade --env dev -r -1` | 回退一步（`-r base` 全部） |
| `uv run main.py stamp --env dev` | 仅写版本标记（存量库接入） |
| `uv run main.py current --env dev` | 查看当前版本 |
| `uv run main.py history --env dev` | 查看版本链 |
