# We-MP-RSS Project Status

Tool: Codex App
Date: 2026-08-25

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
- Current task: `wechat-intelligence-hub`, Controlled revision 5 after CodeNote/AI-DB initialization synchronization.
- Runtime state: v2 foundation/backend/floating UI are present; live PostgreSQL/Redis/MQTT/provider/browser/deployment acceptance remains open.
- Documentation state: the core repository is the canonical home for original requirements, implementation research, migration mapping, connector decisions and current process evidence.
- Governance state: CodeNote adapters, project routes, knowledge hub and a populated AI-DB documentation workspace are initialized; no database operation was performed.

## Active Task Index

| Task | State | Authority | Verification | Main open gate |
| --- | --- | --- | --- | --- |
| WeChat intelligence core | `implemented-local / runtime-gated / unpushed` | [Spec](../../docs/tasks/260824-wechat-intelligence-hub/spec.md) | [39-test/build/static receipt](../../docs/tasks/260824-wechat-intelligence-hub/verify.md) | staging DB, providers, browser and deployment |
| SupSub adapter canary | `deferred-by-scope` | [research](../../docs/research/supsub-integration.md) | public evidence only | fixture/account and explicit external-action gate |
| CodeNote + AI-DB initialization | `implemented-local / static-verified / uncommitted` | this hub + [AI-DB](../ai-db/README.md) | project/link/JSON/static audit | no live DB/runtime acceptance; commit needs a new explicit request |

## Verification State

- Latest accepted product evidence: 39 focused backend tests, offline three-dialect DDL render, Compose parse and Vue production build from the existing Controlled receipt.
- Current governance delta passed CodeNote project audit, exact project/path resolution, catalog 14/14, AI-DB 15/15, JSON/link and scoped secret checks; final staged diff remains the commit gate.
- Unverified: live WeChat/SupSub, actual user DB/schema, PostgreSQL/Redis/MQTT connectivity, browser/accessibility, notifications, deployment and push.

## Open Gates

- Any database mutation, application initialization that creates/alters tables, migration runner or data fix: user/DBA approval and AI-DB task package.
- Any provider login, credential write, paid/quota-consuming call, public share or external synchronization: explicit action-specific approval.
- Deployment/publish/push and subjective UI acceptance remain separate gates.

## Memory Routing

- Project knowledge: [../knowledge/README.md](../knowledge/README.md).
- Database memory: [../ai-db/project-memory/README.md](../ai-db/project-memory/README.md).
- Error memory: [../knowledge/error-memory/README.md](../knowledge/error-memory/README.md).
- Two reusable tool-routing recoveries were synchronized to CodeNote error memory: Python `unittest` absolute-path module resolution and zsh scalar file-list splitting.

## Governance Baseline

- Template propagation: accepted global baseline; this project keeps only local routes and does not copy CodeNote owner bodies.
- Codex evolution: `v3-route-accepted`; this initialization changes no Hook, supervisor, rollout or runtime-supervision owner.
- `w24-primary-objective-continuity-accepted`: project product work remains ahead of advisory governance lanes.
- `w28-documentation-impact-accepted`: current adapters, status, knowledge, AI-DB memory and Controlled owners are one synchronization group.
- `w30-standard-requirement-owner-accepted`: Standard requirement ownership remains raw requirement plus the Spec owner; this existing task remains Controlled.

## Next Update Trigger

Update this hub when the current task/revision, verified runtime state, open gates, canonical docs, CodeNote registration or memory routing changes.
