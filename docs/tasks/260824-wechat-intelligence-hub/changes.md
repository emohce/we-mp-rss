# Changes：微信公众号智能聚合系统

Updated: 2026-08-25

## 1. 概览

| 批次 | 提交 | 文件数 | 核心说明 |
| --- | --- | --- | --- |
| Governance baseline | `a1efa5b` | 8 | 建立受控需求、计划、研究与回滚基线。 |
| Durable foundation | `7bbe683` | 14 | 增加分档存储、租户模型、租约任务、outbox 和内容存储适配层。 |
| Intelligence backend | `426c9c1` | 30 | 增加采集、限频、AI/反馈/日报/导出、v2 API 和离线迁移契约。 |
| Floating workspace | `754b846` | 237 | 增加全局右侧浮窗、API 绑定和经验证的生产构建产物。 |
| Documentation closeout | `13057d4` | 12 | 同步 README、运维架构、研究、验证、错误记忆和交接边界。 |
| Provider integration revision | `fd666a7` | 12 | 增加通用连接器注册表、SupSub 核验和 RAW-003。 |
| Legacy documentation migration | `5a94de0` | 13 | 增加总索引、旧项目迁移矩阵和 RAW-004，并同步所有当前权威。 |
| CodeNote / AI-DB initialization | `0947b3c` + `f2987dd` | 38 | 保留上游指南，登记新核心身份，增加项目路由、知识/状态枢纽、非空 AI-DB 与 RAW-005。 |

## 2. 交付物清单

| 对象 | 类型 | 核心说明 |
| --- | --- | --- |
| `docs/tasks/260824-wechat-intelligence-hub/` | 新增 | Controlled 任务的唯一过程台账。 |
| `docs/research/wechat-collection-landscape.md` | 新增 | 采集路线、限制、许可证和采用决策。 |
| `docs/intelligence-hub.md` | 新增 | 架构档位、租户/采集边界、API、配置和迁移手册。 |
| `core/intelligence/` | 新增/修改 | 可移植模型、持久任务/outbox、采集器、分析、反馈、日报和测试。 |
| `apis/intelligence.py` / `jobs/intelligence.py` | 新增 | 认证 v2 API、公开摘要页和可控后台 Worker。 |
| `web_ui/src/components/intelligence/IntelligenceHub.vue` | 新增 | 不增加路由的统一智能浮窗。 |
| `compose/` / `tools/intelligence_schema.py` | 新增 | Distributed 示例和只读/离线数据库交接工具。 |
| `docs/integrations/` | 新增 | 通用连接器能力、风险、生命周期、事实源和供应商核验模板。 |
| `docs/research/supsub-integration.md` | 新增 | SupSub 当前价格/能力/CLI 边界、采用顺序和未关闭门禁。 |
| `docs/README.md` | 新增 | 核心仓库的需求、架构、研究、迁移、连接器和过程文档唯一入口。 |
| `docs/migrations/wechat-download-api.md` | 新增 | 逐项标记旧行为的当前实现状态、数据映射、安全不变量和许可证边界。 |
| `docs/tasks/260824-wechat-intelligence-hub/` | 更新 | 增加 RAW-004、Spec revision 4、WU-8 及对应验证/交接证据。 |
| `docs/intelligence-hub.md` / `docs/research/wechat-collection-landscape.md` | 更新 | 收敛旧行为状态并纠正 MCP/批量导出的实现表述。 |
| `ReadMe.md` / `README.zh-CN.md` | 更新 | 暴露需求、调研和迁移文档总入口。 |
| `AGENTS.md` / `CLAUDE.md` / `vibe/rules/` | 新增/更新 | CodeNote 短适配器与项目规则；不复制全局 owner 正文。 |
| `vibe/specs/` / `vibe/knowledge/` | 新增 | 当前任务路由、技术地图、ADR/错误记忆入口。 |
| `vibe/ai-db/` | 新增 | 15 个非空规则、模板和稳定 DB 记忆文件；不含凭据或执行授权。 |
| CodeNote project catalog / local binding / status | 更新 | `we-mp-rss` 独立稳定身份、本机路径与当前状态；保留旧项目条目。 |
| CodeNote error memory | 更新 | 复用 unittest 记录并新增 zsh 数组陷阱；未吸收其他任务的 Skill/rule-state 漂移。 |

## 3. 逐批清单

- `a1efa5b`：8 个文档/规则文件，487 行新增。
- `7bbe683`：14 个文件，1,455 行新增、41 行删除。
- `426c9c1`：30 个文件，5,448 行新增、44 行删除。
- `754b846`：237 个文件，2,349 行新增、1,776 行删除；主要为构建哈希资源换代。
- `13057d4`：12 个文件，341 行新增、54 行删除。
- `fd666a7`：12 个文档文件，增加通用连接器与 SupSub 需求/研究同步。
- `5a94de0`：13 个文档文件，315 行新增、30 行删除。
- `0947b3c`：29 个文件、814 行新增（AGENTS/CLAUDE/vibe 骨架）；`f2987dd`：9 个文件、159 行新增、26 行删除（台账同步）。核心仅规则/文档；CodeNote 仅项目索引/状态/测试断言/错误记忆/生成清单；
  `workspace.local.json` 为本机不跟踪绑定，所有业务代码、数据库和运行时均排除。

## 4. 明确没做的

| 对象 | 数量 | 核心说明 |
| --- | --- | --- |
| 真实微信/付费 API/AI CLI 调用 | 0 | 受凭据、计费和运行时门禁约束。 |
| 用户数据库迁移 | 0 | 只提供只读检查器和离线 DDL。 |
| Redis/MQTT 实际连接 | 0 | 只验证适配契约与 Compose 配置。 |
| 部署、推送和浏览器验收 | 0 | 均保留为独立门禁。 |
| SupSub 安装、登录、购买、同步、精读和分享 | 0 | 本轮仅扩充需求与公开证据。 |
| 旧 AGPL 源码、凭据、SQLite 数据和仓库专属治理文档复制 | 0 | 只迁移需求、行为研究、数据映射和采用决定。 |
| MCP、租户化 Feed、批量导出日期/增量/HTML/EPUB 补齐 | 0 | 已进入计划/部分实现清单，未伪装为本轮代码交付。 |
| 数据库连接、schema 检查、DDL/DML、迁移、初始化、修复 | 0 | AI-DB 仅建立文档记忆与 DBA 交接边界。 |
| FastAPI、Redis、MQTT、浏览器、Provider、部署和 push | 0 | 本轮是规则/文档静态初始化。 |
| 并发出现的 `tools/fix_db.py` 变更 | 0 owned | 非本任务改动；已由独立提交 `44198c3` 单独修复与验证，未并入本批次。 |

## 5. 用户可见行为变化

- 登录后全局显示 `AI 聚合` 浮动入口，而非继续扩张管理路由。
- 支持收件箱主题/相关度/状态过滤、单篇多格式下载、逐篇反馈、偏好建议和日期日报分享。
- 新后台任务默认关闭；未迁移数据库时不会自动采集或写入外部系统。

## 6. 顺手发现但未处理

- 上游 `tools/fix_db.py` 存在未终止字符串，导致仓库级 `compileall` 失败；本任务未改该文件。
- 前端依赖保留 10 个既有审计项，并有大包、直接 `eval` 和动态导入警告。
- 付费接口价格、微信权限和风控额度都不是稳定静态事实，正式启用前必须再次联网核验。
- SupSub 尚缺测试账号下的 Feed/OPML/API 字段、合同、配额与冲突证据，不能宣传为已集成。
- 当前核心未发现 MCP 入口；现有批量导出未覆盖旧项目的全部范围/格式/本地只读契约，迁移矩阵已
  将两者分别标为 `planned` 和 `partial-current`。
- 全仓 Markdown 深扫仍保留两个旧 Web UI 文档的 5 个失效链接和 `TROUBLESHOOTING_CASCADE.md`
  的 11 个重复标题；均非本轮文件，项目规则/本轮文档链接无新增问题。
- CodeNote master working view 另有一个由其他任务未跟踪 Skill 引起的确定性清单漂移；生成器产生的
  外来 hunk 已撤回，`rule-state.json` 恢复到本任务前内容。

## 7. 回归数字

- 后端：39/39 通过。
- 数据库：3 个方言 DDL 均成功生成，每份 460 行。
- 前端：Vite 生产构建通过；14/14 首页资源引用存在，构建资源树一致。
- 分布式配置：Compose 解析通过；真实基础设施未连接。
- CodeNote/AI-DB：项目审计通过，项目/路径解析 2/2，catalog 测试 14/14，AI-DB 结构 15/15。

## 8. v3 整改增量 (2026-08-30)

| 文件 | 本轮变化 |
| --- | --- |
| [raw-requirement](raw-requirement.md)、[Spec](spec.md) | RAW-006 明确七批实施与门禁，修正同步清单为确切文件 |
| [plan](plan.md)、[tasks](tasks.md) | WU-10..16 顺序、调用链验收范围和未完成状态 |
| [verify](verify.md)、[handoff](handoff.md) | 既有证据不等于 v3 验收，保留既存改动与当前恢复点 |
| [当前状态](../../../vibe/specs/PROJECT_STATUS.md) | 指向 revision 6；修正已提交初始化状态 |
| [运行说明](../../intelligence-hub.md) | 显式标记基础实现尚待补齐的链路 |
| [DB engine](../../../core/db.py#L28) | 删除连接时建文件/自动补列，显式初始化仅处理 legacy |
| [models](../../../core/intelligence/models.py#L470) | 独立检查点/运行/预算、日报覆盖/修订、过滤/搜索与来源用量表 |
| [migration](../../../core/intelligence/migration.py#L18)、[CLI](../../../tools/intelligence_schema.py#L1) | 严格 schema/version 检查与离线版本 SQL |
| [baseline](../../../migrations/intelligence/versions/int_v2_20260824.py#L1)、[delta](../../../migrations/intelligence/versions/int_v3_20260830.py#L1)、[env](../../../migrations/intelligence/env.py#L1) | 冻结版本定义；环境拒绝在线迁移 |
| [migration tests](../../../core/intelligence/test_migration.py#L1)、[job startup](../../../jobs/intelligence.py#L1) | 离线/就绪/启动回归和旧 schema 拒绝启动 |
| [DB package](../../../vibe/ai-db/ai-db-tasks/260830/0941-intelligence-v3/plan.md) | plan/sql/verify 人工执行、恢复与发布门禁 |
| [DB inventory](../../../vibe/ai-db/project-memory/schema_inventory.md)、[technical details](../../../vibe/knowledge/technical-details.md) | 同步新版本、启动事实及其路由/交接说明 |

未实施：真实数据库迁移、账号登录、收费调用、运行服务、部署、推送及全局规则修改。
