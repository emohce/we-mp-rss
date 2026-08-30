# We-MP-RSS Project Status

Tool: Codex App
Date: 2026-08-30

## Purpose

Compact project-current router. Durable product requirements and execution evidence remain in their owning documents.

## Rule And Authority Links

- Project rules: [../rules/README.md](../rules/README.md)
- Documentation mapping: [../rules/documentation.md](../rules/documentation.md)
- Product/current docs: [../../docs/README.md](../../docs/README.md)
- Canonical requirement: [Controlled Spec](../../docs/tasks/260824-wechat-intelligence-hub/spec.md)
- Task plan and ledger: [plan](../../docs/tasks/260824-wechat-intelligence-hub/plan.md), [tasks](../../docs/tasks/260824-wechat-intelligence-hub/tasks.md)
- Verification and handoff: [verify](../../docs/tasks/260824-wechat-intelligence-hub/verify.md), [handoff](../../docs/tasks/260824-wechat-intelligence-hub/handoff.md)
- Database workspace: [../ai-db/README.md](../ai-db/README.md)

## Current Focus

- Repository: `we-mp-rss` (upstream `rachelos/we-mp-rss`), local branch `czz-main`, upstream baseline `f54aba5`.
- Current task: `wechat-intelligence-hub`, Controlled revision 6, WU-10..16 local code/offline remediation complete.
- Runtime state: v3 code/floating UI/connector contracts are present; authorized PostgreSQL/Redis/MQTT/provider/browser/deployment acceptance remains open.
- Documentation state: the core repository is the canonical home for original requirements, implementation research, migration mapping, connector decisions and current process evidence.
- Governance state: CodeNote adapters, project routes, knowledge hub and a populated AI-DB documentation workspace are initialized; no database operation was performed.

## Active Task Index

| Task | State | Authority | Verification | Main open gate |
| --- | --- | --- | --- | --- |
| WeChat intelligence core | `v3-local-verified / runtime-gated / unpushed` | [Spec](../../docs/tasks/260824-wechat-intelligence-hub/spec.md) | [v3 WU-10..16 evidence](../../docs/tasks/260824-wechat-intelligence-hub/verify.md) | live DB/provider/browser acceptance; Redis incident impact |
| SupSub adapter canary | `deferred-by-scope` | [research](../../docs/research/supsub-integration.md) | public evidence + generic format/CLI-envelope tests | actual supplier fixture/account and explicit external-action gate |
| CodeNote + AI-DB initialization | `committed-local / static-verified` | this hub + [AI-DB](../ai-db/README.md) | historical project/link/JSON/static audit | no live DB/runtime acceptance |

## Verification State

- Latest v3 evidence: 91 backend tests with pre-import I/O guards (zero attempts/legacy runtime imports), 10 UI
  state tests, affected TS/SFC checks and Vite build; frozen SQLite/PostgreSQL SQL render; 129 served files/15 references.
- Historical initialization passed CodeNote project audit, route resolution, catalog 14/14 and AI-DB 15/15. For
  this turn only, user D1 waives the broken automatic global router; scoped document/link/receipt checks remain.
- A prior legacy test import connected to Redis and started queue threads. Process exited; possible status writes
  were not inspected or restored. Guarded rerun proves isolation only, not absence of the earlier impact.
- Unverified: live WeChat/SupSub, actual user DB/schema, PostgreSQL/Redis/MQTT connectivity, browser/accessibility, notifications, deployment and push.

## Open Gates

- Any database mutation, application initialization that creates/alters tables, migration runner or data fix: user/DBA approval and AI-DB task package.
- Any provider login, credential write, paid/quota-consuming call, public share or external synchronization: explicit action-specific approval.
- Deployment/publish/push and subjective UI acceptance remain separate gates.
- Redis incident impact: exact, separately authorized read-only evidence before any recovery decision; no shared-key cleanup.

## Memory Routing

- Project knowledge: [../knowledge/README.md](../knowledge/README.md).
- Database memory: [../ai-db/project-memory/README.md](../ai-db/project-memory/README.md).
- Error memory: [../knowledge/error-memory/README.md](../knowledge/error-memory/README.md).
- New project record: [legacy import isolation](../../docs/knowledge/error-memory/legacy-job-import-runtime-side-effects.md); no global memory change in v3.
- Two reusable tool-routing recoveries were synchronized to CodeNote error memory: Python `unittest` absolute-path module resolution and zsh scalar file-list splitting.

## Governance Baseline

- Template propagation: accepted global baseline; this project keeps only local routes and does not copy CodeNote owner bodies.
- Codex evolution: `v3-route-accepted`; this initialization changes no Hook, supervisor, rollout or runtime-supervision owner.
- `w24-primary-objective-continuity-accepted`: project product work remains ahead of advisory governance lanes.
- `w28-documentation-impact-accepted`: current adapters, status, knowledge, AI-DB memory and Controlled owners are one synchronization group.
- `w30-standard-requirement-owner-accepted`: Standard requirement ownership remains raw requirement plus the Spec owner; this existing task remains Controlled.

## Next Update Trigger

Update this hub when the current task/revision, verified runtime state, open gates, canonical docs, CodeNote registration or memory routing changes.
