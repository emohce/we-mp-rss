# 微信公众号智能聚合系统执行计划

Tool: Codex App
Date: 2026-08-24
Task: wechat-intelligence-hub

Documentation level: `controlled`

## Plan-Mode Gate

- Plan level: `controlled`
- Task artifact for this run: this Controlled ledger plus research evidence.
- Plan packet before first edit complete: `yes`
- Prior-task overlap decision: `new-task`, with legacy repository as reference-only donor.
- Documentation impact: `project-current`
- Required owners for first sync: task ledger, README/config documentation and API/UI behavior docs.
- Verification map: absent — dynamic impact analysis.
- Provisional `VerificationImpactTrace` completed before verification commands: `yes`
- Provisional changed/affected surfaces: SQLAlchemy metadata, storage profiles, Redis/MQTT adapters, v2 service/API,
  scheduler-safe collector state, Vue router/layout, exports and docs.
- Selected focused checks: backend unit/API tests, Python compile, dialect compilation, fake Redis/MQTT contracts,
  affected Vue type/build, migration dry-run and route/link checks.
- Verification-command provenance: `incoming-plan-reconciled`
- Full-suite escalation trigger: `none`; unrelated upstream suites remain excluded.

## Summary

1. Establish tenant-safe portable SQLAlchemy models, PostgreSQL production storage, SQLite Lite compatibility,
   content-addressed storage and durable jobs/outbox.
2. Add Redis coordination for caches, locks, rate budgets and queue wakeups; add optional MQTT transport for
   distributed collectors and deliveries, with database-backed replay.
3. Add provider adapters, cursor-safe collection, rate-limit state and daily schedule policy.
4. Add AI analysis adapters, immutable feedback, approval-gated preferences and dated digests.
5. Add v2 APIs, single/bulk exports, delivery outbox and tenant-scoped feeds/MCP contract.
6. Replace navigation-heavy UX with an inbox, date archive and right-side floating panels.
7. Provide a read-only legacy migration inspector and keep all live/data gates closed.

## Delegation Decision

- Interactive strategy: `main-only`
- Automation lane: `not-applicable`
- Reason: user did not request subagents; one clean branch and coupled backend/frontend contracts favor a single owner.
- Root-owned decisions: architecture, Git, security gates, documentation and acceptance.
- Duplicate guard: one implementation path in `we-mp-rss`; no parallel business code in donor repositories.
- Expected observable delegation benefit and metric: not applicable; usage unavailable.

## Execution Topology

| Work Unit | Owner | Surface | Mode | Depends On | Allowed / Excluded Scope | Output Contract | Verification Owner | Fallback |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| WU-1 Foundation | app-root | backend | main-only | docs | SQLAlchemy profiles, durable DB state, Redis/MQTT adapters; no user DB | schema and unit tests | app-root | SQLite Lite/v1 untouched |
| WU-2 Collection | app-root | backend | main-only | WU-1 | fake providers only | durable state machine | app-root | collector disabled |
| WU-3 Intelligence | app-root | backend | main-only | WU-1 | local CLI adapters; no secrets | topics/feedback/digests | app-root | deterministic analysis |
| WU-4 Experience | app-root | frontend | main-only | WU-1..3 API | Vue source/build only | inbox and floating panels | app-root | retain v1 routes |
| WU-5 Closeout | app-root | docs/tests | main-only | WU-1..4 | no deploy/push/data mutation | evidence and local commits | app-root | explicit residual gates |

## Sidecar Strategy

- Start Explorer: not applicable; Root has direct clean-repository evidence.
- Closeout Reviewer: main-only diff review, because user did not request delegation.
- Fallback: stop at the smallest unverified boundary and keep v1 available.

## Risks

- Upstream global read/favorite fields may leak state unless every v2 query uses the new association table.
- SQLite Lite requires short transactions and one writer; PostgreSQL mode still requires idempotent claims and
  database leases because Redis/MQTT delivery is at-least-once.
- Redis/MQTT outages must fall back to database polling/outbox replay rather than lose tasks or advance cursors.
- AI CLI output is untrusted; strict JSON parsing and deterministic fallback are mandatory.
- Direct URL download requires host allowlists, redirect checks and path-safe export names.

## Verification

- Source evidence and `doc_drift`: README/config currently expose SQLite/MySQL/PostgreSQL, an embedded Redis
  server and HTTP cascade, but do not define authoritative storage profiles or MQTT/outbox semantics; synchronize them.
- Final document impact and synchronization owner: `project-current`, App Root.
