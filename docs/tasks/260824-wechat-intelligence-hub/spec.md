# 微信公众号智能聚合系统 Controlled Spec

Tool: Codex App
Date: 2026-08-24
Updated: 2026-08-25
Task: wechat-intelligence-hub

Documentation level: `controlled`

## Task Documentation Sync Group

- Group key: `dsg:we-mp-rss:wechat-intelligence-hub-v1`
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
  "group_key": "dsg:we-mp-rss:wechat-intelligence-hub-v1",
  "group_owner": "docs/tasks/260824-wechat-intelligence-hub/spec.md",
  "documents": [
    "docs/README.md",
    "docs/tasks/260824-wechat-intelligence-hub",
    "docs/migrations",
    "docs/integrations",
    "docs/research/wechat-collection-landscape.md",
    "docs/research/supsub-integration.md",
    "AGENTS.md",
    "CLAUDE.md",
    "vibe"
  ],
  "dependencies": ["core/intelligence", "apis/intelligence.py", "web_ui/src"],
  "validators": ["local-markdown-links", "provider-evidence-freshness", "codenote-project-audit", "project-catalog-resolution"],
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
spec_revision: 5
status: confirmed
raw_sources: [RAW-001, RAW-002, RAW-003, RAW-004, RAW-005]
targets:
  - canonical_manifest: this-spec
    base_full_version: upstream-f54aba5
    result_full_version: czz-main-v4
delta:
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

- Write isolation: clean `czz-main`; task paths only.
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
