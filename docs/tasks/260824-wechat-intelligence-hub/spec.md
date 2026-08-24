# 微信公众号智能聚合系统 Controlled Spec

Tool: Codex App
Date: 2026-08-24
Task: wechat-intelligence-hub

Documentation level: `controlled`

## Task Documentation Sync Group

- Group key: `dsg:we-mp-rss:wechat-intelligence-hub-v1`
- Group owner: this `spec.md`
- Task-root discovery prefix: `docs/tasks/260824-wechat-intelligence-hub/`
- Durable document members: raw requirement, spec, plan, tasks, verify, handoff, changes and research evidence.
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
    "docs/tasks/260824-wechat-intelligence-hub",
    "docs/research/wechat-collection-landscape.md"
  ],
  "dependencies": ["core/intelligence", "apis/intelligence.py", "web_ui/src"],
  "validators": [],
  "git_scope_prefixes": ["docs/tasks/260824-wechat-intelligence-hub", "docs/research"]
}
```

## Requirement

- `we-mp-rss` 是唯一可运行核心；`Wechat2RSS` 仅作公开行为参考。
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

## Success Criteria

- v2 API、跨 SQLite/PostgreSQL 模型、Redis/MQTT 适配层、采集状态机、AI/反馈服务、日期摘要、
  单篇导出和浮窗 UI 可构建并有聚焦测试。
- 任何采集失败都不会提前推进游标或无限扩张队列。
- 用户无法通过文章、搜索、导出、摘要、RSS 或 MCP 读取其他工作区数据。
- 旧 v1 行为仍可运行；新实现不复制 AGPL 或未授权的第三方源码。
- 所有实现按主题拆为本地提交，不推送，不调用真实微信或付费接口。

## Constraints

- 不写入旧 SQLite，不迁移凭据，不运行收费 Docker，不部署或切换服务。
- 实际数据库迁移、真实微信调用、AIDATA 计费、Webhook/邮件投递和代理切换需要独立门禁。
- Lite 限定单后端进程；Standard/Distributed 支持多个 API/Worker 实例，以数据库幂等键、租约和
  outbox 保证一致性。
- Redis 和 MQTT 可以降级或暂时离线，但不得成为文章、游标、反馈或计费状态的唯一保存位置。
- 过滤只能折叠或排序，不能静默删除文章。

## Prior Task Overlap

- Relationship: `reference-only`
- Prior authority and verified state: `wechat-download-api/czz-main` 保存旧行为与文档，未迁移业务源码。
- Document governance: 本任务文档只存在于核心仓库。
- Execution logic verification / residual gates: 旧库 AGPL；仅可做行为和数据映射。
- Traceability and net-new delta: 从单用户下载 API 收敛到核心仓库的多用户智能聚合系统。

## Requirement Versioning

```yaml
spec_id: WXI-001
spec_revision: 2
status: confirmed
raw_sources: [RAW-001, RAW-002]
targets:
  - canonical_manifest: this-spec
    base_full_version: upstream-f54aba5
    result_full_version: czz-main-v1
delta:
  - requirement_id: WXI-STORAGE
    operation: modify
    before: global article state and optional external infrastructure
    after: SQLite-first tenant-scoped state and durable jobs
    raw_refs: [RAW-001]
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
memory_used: []
memory_updates: []
open_questions: []
```

## Requirement Change Review

- Bounded scan scope / owners: upstream models, APIs, scheduler, Vue routes, README and security guidance.
- Visible added: AI topics, feedback learning, dated digests, single-article multi-format export, tenant state,
  durable rate limits, PostgreSQL production profile, Redis coordination and MQTT event transport.
- Visible changed: SQLite-only is superseded by tiered storage; read/favorite state becomes per-user; management
  moves into floating panels.
- Visible removed/superseded: unbounded subscription backfill and new independent management pages.
- Classification: `direct-conflict` resolved by the later explicit current request; RAW-002 supersedes RAW-001's
  SQLite-only interpretation while preserving SQLite Lite compatibility.
- Decision status: `explicit-current-request`.
- Decision source: approved current plan.
- Post-sync rescan: pending until closeout.

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
