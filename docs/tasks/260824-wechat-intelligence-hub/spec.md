# 微信公众号智能聚合系统 Controlled Spec

Tool: Codex App
Date: 2026-08-24
Updated: 2026-08-30
Task: wechat-intelligence-hub

Documentation level: `controlled`

## Task Documentation Sync Group

- Group key: `dsg:we-mp-rss:correctness-v3`
- Group owner: this `spec.md`
- Task-root discovery prefix: `docs/tasks/260824-wechat-intelligence-hub/`
- Durable document members: documentation index, raw requirement, spec, plan, tasks, verify, handoff, changes,
  legacy migration matrix, integration registry, research evidence, project adapters/rules/status/knowledge and AI-DB memory.
- Declared code/config dependencies: backend v2 modules, SQLAlchemy models, FastAPI router, Vue UI and config defaults.
- Linked authorities: repository `AGENTS.md`, upstream README and `SECURITY.md`.
- Excluded unrelated documents: upstream release notes and historical issue records.
- Lookup contract: only a future exact documentation receipt may reuse the synchronization gate.
- Shared-file stage ownership: App Root owns every change and stages only this task's paths.

```json documentation-sync-group-v1
{
  "schema": "documentation-sync-group-v1",
  "group_key": "dsg:we-mp-rss:correctness-v3",
  "group_owner": "docs/tasks/260824-wechat-intelligence-hub/spec.md",
  "documents": [
    "docs/tasks/260824-wechat-intelligence-hub/spec.md",
    "docs/tasks/260824-wechat-intelligence-hub/raw-requirement.md",
    "docs/tasks/260824-wechat-intelligence-hub/plan.md",
    "docs/tasks/260824-wechat-intelligence-hub/tasks.md",
    "docs/tasks/260824-wechat-intelligence-hub/verify.md",
    "docs/tasks/260824-wechat-intelligence-hub/handoff.md",
    "docs/tasks/260824-wechat-intelligence-hub/changes.md",
    "docs/intelligence-hub.md",
    "AGENTS.md",
    "vibe/rules/README.md",
    "vibe/rules/project.md",
    "vibe/rules/workflow.md",
    "vibe/rules/documentation.md",
    "vibe/specs/PROJECT_STATUS.md",
    "vibe/ai-db/README.md",
    "vibe/ai-db/rules.md",
    "vibe/ai-db/project-memory/schema_inventory.md",
    "vibe/ai-db/project-memory/handoff.md",
    "vibe/ai-db/project-memory/system_map.md",
    "vibe/knowledge/technical-details.md",
    "vibe/ai-db/ai-db-tasks/260830/0941-intelligence-v3/plan.md",
    "vibe/ai-db/ai-db-tasks/260830/0941-intelligence-v3/sql.md",
    "vibe/ai-db/ai-db-tasks/260830/0941-intelligence-v3/verify.md"
  ],
  "dependencies": ["core/db.py", "core/intelligence/models.py", "core/intelligence/migration.py", "core/intelligence/collector.py", "core/intelligence/collection_state.py", "core/intelligence/rate_limit.py", "core/intelligence/providers.py", "core/intelligence/jobs.py", "core/intelligence/workflow.py", "core/intelligence/daily.py", "core/intelligence/digests.py", "core/intelligence/services.py", "apis/intelligence.py", "jobs/intelligence.py", "tools/intelligence_schema.py", "migrations/intelligence/env.py", "migrations/intelligence/versions/int_v2_20260824.py", "migrations/intelligence/versions/int_v3_20260830.py", "web_ui/src/components/intelligence/IntelligenceHub.vue"],
  "validators": ["core/intelligence/test_migration.py", "core/intelligence/test_foundation.py", "core/intelligence/test_collection_state.py", "core/intelligence/test_workers.py", "core/intelligence/test_services.py", "core/intelligence/test_daily.py", "core/intelligence/test_api.py"],
  "git_scope_prefixes": ["AGENTS.md", "CLAUDE.md", "vibe", "docs/README.md", "docs/intelligence-hub.md", "docs/tasks/260824-wechat-intelligence-hub", "docs/migrations", "docs/integrations", "docs/research"]
}
```

## Requirement

- `we-mp-rss` 是唯一可运行核心；`Wechat2RSS` 仅作公开行为参考，`wechat-download-api` 仅作旧需求、
  行为、数据映射和实现研究来源。
- 存储采用分档架构：Lite 为 SQLite，Standard 为 PostgreSQL + Redis，Distributed 在 Standard
  之上增加 MQTT；生产推荐 Standard，不能再把 SQLite-only 作为架构上限。
- PostgreSQL 保存租户、文章元数据、反馈、游标、任务和 outbox；Redis 保存缓存、限频令牌、
  分布式锁和任务唤醒；MQTT 传递采集节点/投递事件。数据库任务与 outbox 始终是最终事实。
- 正文和导出使用内容寻址对象存储；Lite 使用本地文件，Standard/Distributed 可接 S3/MinIO。
- 全局文章去重，用户/工作区的订阅、状态、反馈、偏好、日报和投递隔离。
- 新订阅不触发无限历史抓取；采集游标、预算、退避和熔断均持久化。
- 每篇文章可下载；每日 06:30 采集、07:50 截止、08:00 生成按日期归档的摘要页。
- AI 识别文章与公众号主题，按用户兴趣过滤；明确反馈即时生效，推断规则需批准。
- 主要页面限定为登录、统一收件箱和日期摘要，管理能力使用浮窗。
- 外部托管聚合、Feed、付费 API、AI 增强和投递服务必须通过同一连接器注册表接入，按能力与风险
  分级；SupSub 是首个样板连接器，但不进入默认运行时。
- 连接器首版只读和单向同步优先，文章保留供应商来源与外部身份；订阅写回、按次计费、不可逆
  已读和公开分享需要逐项确认。
- 旧项目相关需求和调研必须在核心仓库建立可追溯映射，并明确 `implemented-current`、
  `partial-current`、`planned`、`reference-only` 或 `superseded`；不得把旧 README 当作当前完成证明。
- 保留核心现有 RSS/Atom/JSON/Markdown Feed、通知、图片代理和异步批量导出；新增能力在现有路径上
  收敛，不复制旧项目源码或创建第二套后台。
- Intelligence Hub 的批量导出需补齐日期/时间窗/增量范围和统一审计，并保证默认只读本地持久化
  内容、不隐式触发微信或付费调用；远程图片补全必须显式展示网络与预算行为。
- MCP 保留为后续需求。当前核心源码没有 MCP 运行入口；未来实现必须使用当前用户/工作区权限或
  受限 Access Key，不能继承旧项目的无鉴权 HTTP 或单用户静态 Token 边界。
- 核心仓必须使用短 CodeNote 适配器和项目级 `vibe/` 路由，并在 CodeNote 稳定项目索引中登记；
  现有上游仓库指南继续保留，跨项目规则只链接 CodeNote 权威，不复制规则正文。
- 数据库事实、环境路由、schema 证据、SQL 候选与人类/DBA 交接统一进入 `vibe/ai-db/`。AI-DB
  是非空文档/记忆工作区，不是连接器或执行器；Agent 不执行 DDL、DML、迁移、初始化或数据修复。

## Success Criteria

### v3 correctness acceptance (RAW-006)

- 每日头部轮询从最新页开始；历史回补使用独立游标。失败/租约失效不推进检查点，不把限额等待
  计为供应商失败；来源、共享账户与进程总预算有持久化退让路径。
- 启动不再偷偷补列；迁移具有冻结的版本链、离线 SQL 与只读 schema 检查。存量数据库由人类/DBA
  执行，测试仅使用进程内隔离数据，不以自动迁移用户数据库完成验收。
- 日报以每日运行及来源快照追踪覆盖；截止仍未齐全时发布 partial 并解释原因；迟到文章可修订，
  摘要版本和 outbox 幂等键同步变化，同一输入重跑不重复发布。
- 收件箱、日报共用相关度和已批准偏好规则；支持主题偏好、规则撤销及保存过滤，明确反馈优先。
- 阅读与下载只读可见本地内容；Markdown 为真正的 Markdown；新正文可进入内容寻址存储，旧正文
  保留兼容，不自动执行历史对象迁移。
- 浮窗使用单一可恢复视图状态，阅读与列表并排，过滤和宽度可保存；打开浮窗不自动导入全库。
- 连接器运行时只接受已注册且能力匹配的只读操作；Wechat2RSS、SupSub、充值 API 先通过离线
  fixture 验证，展示来源、任务/冷却/日报覆盖状态；不得把 fixture 通过写成真实供应商已接通。

以下 v2 条目为已交付基础，不代替以上新增回归验收。

- v2 API、跨 SQLite/PostgreSQL 模型、Redis/MQTT 适配层、采集状态机、AI/反馈服务、日期摘要、
  单篇导出和浮窗 UI 可构建并有聚焦测试。
- 任何采集失败都不会提前推进游标或无限扩张队列。
- v2 文章、搜索、导出、摘要与公开分享投影都执行工作区校验；现有 v1 RSS 继续按当前核心边界
  运行，不被描述为 v2 多租户能力。MCP 在实现和验证前保持 `planned`。
- 旧 v1 行为仍可运行；新实现不复制 AGPL 或未授权的第三方源码。
- 所有实现按主题拆为本地提交，不推送，不调用真实微信或付费接口。
- 新供应商在关闭 Feed/API 格式、认证、额度、合同和数据处理缺口前只能处于 `researched`，不能
  宣称已经集成或自动降级到该供应商。
- 文档索引与旧项目迁移矩阵能从每项原始需求追到当前权威、实现状态、证据和剩余门禁。
- CodeNote 项目审计、仓内链接和项目身份解析通过；AI-DB 能从存储档位追到环境路线、schema
  期望、核心关系、业务术语和未关闭门禁，且不含凭据或未授权执行记录。

## Constraints

- 不写入旧 SQLite，不迁移凭据，不运行收费 Docker，不部署或切换服务。
- 实际数据库迁移、真实微信调用、AIDATA 计费、Webhook/邮件投递和代理切换需要独立门禁。
- Lite 限定单后端进程；Standard/Distributed 支持多个 API/Worker 实例，以数据库幂等键、租约和
  outbox 保证一致性。
- Redis 和 MQTT 可以降级或暂时离线，但不得成为文章、游标、反馈或计费状态的唯一保存位置。
- 过滤只能折叠或排序，不能静默删除文章。
- 外部服务不得成为文章、反馈、用户状态、任务或用量账本的唯一事实源；带密钥 Feed URL、OAuth
  token 和本地 CLI 凭据只能通过 secret reference 使用。
- R2 外部写入、R3 额度消耗和 R4 不可逆/公开操作不能由无人值守计划任务隐式执行。
- CodeNote catalog 只保存稳定 Git 身份和仓内 authority routes；绝对路径仅进入本机不跟踪的
  workspace binding。AI-DB route 证据不构成连接、DryRun、执行、恢复、发布或生产授权。

## Prior Task Overlap

- Relationship: `reference-only`
- Prior authority and verified state: `wechat-download-api/czz-main@3e85bab` 保存旧行为与文档；应用
  README 与 `origin/main@043c2f9` 一致，3 个领先提交仅为治理/知识文档，未迁移业务源码。
- Document governance: 本任务文档只存在于核心仓库。
- Execution logic verification / residual gates: 旧库 AGPL；仅可做行为和数据映射。
- Traceability and net-new delta: 从单用户下载 API 收敛到核心仓库的多用户智能聚合系统，并新增
  [旧项目迁移矩阵](../../migrations/wechat-download-api.md)作为完整状态映射。

## Requirement Versioning

```yaml
spec_id: WXI-001
spec_revision: 6
status: confirmed
raw_sources: [RAW-001, RAW-002, RAW-003, RAW-004, RAW-005, RAW-006]
targets:
  - canonical_manifest: this-spec
    base_full_version: upstream-f54aba5
    result_full_version: czz-main-v3-correctness
delta:
  - requirement_id: WXI-CORRECTNESS
    operation: clarify
    before: v2 static foundations accepted without daily freshness and reconciliation regressions
    after: seven bounded remediation batches with versioned schema, fresh polling, digest coverage and shared ranking
    raw_refs: [RAW-006]
    confirmation: explicit
    canonical_location: spec.md
  - requirement_id: WXI-STORAGE
    operation: modify
    before: global article state and optional external infrastructure
    after: tiered tenant-scoped durable state with SQLite Lite, PostgreSQL plus Redis recommended, and optional MQTT
    raw_refs: [RAW-001, RAW-002]
    confirmation: explicit
    canonical_location: spec.md
  - requirement_id: WXI-UX
    operation: modify
    before: many independent management pages
    after: unified inbox with floating management surfaces
    raw_refs: [RAW-001]
    confirmation: explicit
    canonical_location: spec.md
  - requirement_id: WXI-INFRA
    operation: modify
    before: SQLite-only target with no Redis or MQTT correctness dependency
    after: tiered SQLite/PostgreSQL storage with Redis acceleration and MQTT distributed events
    raw_refs: [RAW-002]
    confirmation: explicit
    canonical_location: spec.md
  - requirement_id: WXI-CONNECTORS
    operation: add
    before: provider-specific collectors without a common external-integration lifecycle
    after: capability-based connector registry with provenance, sync cursors, usage ledger and verification receipts
    raw_refs: [RAW-003]
    confirmation: explicit
    canonical_location: docs/integrations/README.md
  - requirement_id: WXI-SUPSUB
    operation: add
    before: no SupSub adoption decision
    after: SupSub researched as an optional Feed, discovery, subscription-sync and quota-gated enrichment connector
    raw_refs: [RAW-003]
    confirmation: explicit
    canonical_location: docs/research/supsub-integration.md
  - requirement_id: WXI-LEGACY-DOCS
    operation: add
    before: legacy requirements and implementation research were distributed across a donor README and repository-only notes
    after: one core documentation index and migration matrix classify every relevant behavior, data mapping, rejection and implementation gap
    raw_refs: [RAW-001, RAW-004]
    confirmation: explicit
    canonical_location: docs/migrations/wechat-download-api.md
  - requirement_id: WXI-BULK-EXPORT
    operation: modify
    before: current core asynchronous five-format export and legacy seven-format local-read behavior were not reconciled
    after: extend the current exporter with date/window/incremental scope, audit and an explicit no-hidden-provider-call default
    raw_refs: [RAW-001, RAW-004]
    confirmation: explicit
    canonical_location: docs/migrations/wechat-download-api.md
  - requirement_id: WXI-MCP
    operation: modify
    before: RAW-001 named MCP while the Spec incorrectly implied a current v1 MCP runtime
    after: MCP remains planned and must be tenant/workspace authorized when implemented
    raw_refs: [RAW-001, RAW-004]
    confirmation: explicit
    canonical_location: spec.md
  - requirement_id: WXI-CODENOTE
    operation: add
    before: the core repository had only upstream general contribution guidance and no CodeNote project identity or route chain
    after: preserve upstream guidance while adding tool-neutral adapters, project rules, current status and knowledge routes registered by stable CodeNote identity
    raw_refs: [RAW-004, RAW-005]
    confirmation: explicit
    canonical_location: vibe/rules/README.md
  - requirement_id: WXI-AI-DB
    operation: add
    before: database architecture existed in code/docs without a CodeNote-governed project DB memory and handoff workspace
    after: a populated AI-DB workspace owns environment routing, expected schema, DB glossary/relations, task templates and explicit human/DBA mutation boundaries
    raw_refs: [RAW-002, RAW-005]
    confirmation: explicit
    canonical_location: vibe/ai-db/README.md
memory_used: [wechat-collection-research-and-supsub-baseline]
memory_updates: [project-error-memory:sqlite-memory-pool-routing, codenote-error-memory:python-unittest-absolute-file-path-module-resolution, codenote-error-memory:zsh-scalar-file-list-not-word-split]
open_questions: []
```

## Requirement Change Review

- RAW-006: `compatible-update`, user-confirmed seven-batch implementation and local commits. Desired product,
  repository roles and external-action gates are unchanged. The old WU-1..9 receipts remain historical evidence;
  they do not establish v3 freshness, completeness, ranking parity or floating-reader acceptance.
- Affected owners: this Spec, plan/ledger/evidence/handoff, current architecture, AI-DB schema memory and current
  project status. No global rule or external account mutation is included.

- Bounded scan scope / owners: upstream models, APIs, scheduler, Vue routes, README/security guidance, old project
  README/technical details and current core RSS/export/notification/proxy/MCP source search.
- Visible added: AI topics, feedback learning, dated digests, single-article multi-format export, tenant state,
  durable rate limits, PostgreSQL production profile, Redis coordination, MQTT event transport, a generic connector
  lifecycle and a SupSub integration decision.
- Visible changed: SQLite-only is superseded by tiered storage; read/favorite state becomes per-user; management
  moves into floating panels; legacy features now carry explicit current implementation states; the false implication
  that current core already contains v1 MCP is corrected to `planned`.
- Visible removed/superseded: unbounded subscription backfill, new independent management pages, unauthenticated
  public HTTP inheritance and proxy/account/TLS-fingerprint routes described as limit-evasion mechanisms.
- Classification: `direct-conflict` resolved by the later explicit current request; RAW-002 supersedes RAW-001's
  SQLite-only interpretation while preserving SQLite Lite compatibility.
- Decision status: `explicit-current-request`.
- Decision source: approved current plan.
- Post-sync rescan: completed; storage, UX and infrastructure decisions match the implementation and operator docs.
- RAW-003 is additive: it expands future integration requirements without changing the accepted v2 runtime or
  authorizing a SupSub installation, login, purchase or protected API call.
- RAW-004 is additive documentation synchronization plus implementation-state clarification. It does not authorize
  legacy source copying, database migration, live calls or completion claims for partial/planned capabilities.
- RAW-005 is additive governance initialization. It keeps the Controlled Spec under `docs/tasks`, registers the new
  core without replacing the legacy project identity, and creates project-local AI-DB memory without authorizing a
  database connection, application initialization, DDL/DML, migration, data repair or live infrastructure.

## Execution Authority

- Control plane: `app-root`
- Sole decision owner: App Root Thread
- Allowed interactive execution surfaces: `main`
- Automation lane: `not-applicable`
- Surface-to-surface delegation: forbidden
- Documentation synchronization owner: App Root Thread
- Acceptance gate: focused code/build tests plus synchronized task, research and project docs.

## Execution Constraints

- Write isolation: explicitly requested `czz-main`; one Root writer, task paths/hunks only. Two pre-existing hunks
  in verify/changes are preserved and excluded from new commits. Other worktrees are inspection-only.
- High-risk gates: credentials, live WeChat, paid API, data migration, deployment and push remain excluded.
- DB/SQL boundary: schema/code/tests may use disposable SQLite and isolated test containers; no user database mutation.
- Fallback: keep v1 routes untouched and disable unfinished v2 background execution by configuration.

## Evidence

- Upstream baseline: `f54aba50cbf349ed7e4ee1dae8bfe9990d0c5894`.
- Reference baseline: `Wechat2RSS` `0416ecfb73e42e98b88b70e530609c406d3e5e42`.
- Research evidence: [wechat-collection-landscape.md](../../research/wechat-collection-landscape.md).
- SupSub evidence: [supsub-integration.md](../../research/supsub-integration.md).
- Connector authority: [integration registry](../../integrations/README.md).
- Documentation entry: [docs index](../../README.md).
- Legacy requirements and implementation research: [migration matrix](../../migrations/wechat-download-api.md).
- Project rule entry: [vibe/rules/README.md](../../../vibe/rules/README.md).
- AI-DB authority and stable memory: [vibe/ai-db/README.md](../../../vibe/ai-db/README.md),
  [project-memory](../../../vibe/ai-db/project-memory/README.md).
