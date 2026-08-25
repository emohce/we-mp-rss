# 微信公众号智能聚合系统执行计划

Tool: Codex App
Date: 2026-08-24
Updated: 2026-08-25
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
  scheduler-safe collector state, Vue router/layout, exports, provider-integration requirements and docs.
- Selected focused checks: backend unit/API tests, Python compile, dialect compilation, fake Redis/MQTT contracts,
  affected Vue type/build, migration dry-run, provider primary-source evidence and route/link checks.
- Verification-command provenance: `incoming-plan-reconciled`
- Full-suite escalation trigger: `none`; unrelated upstream suites remain excluded.
- 2026-08-25 delta: reuse the existing Controlled task and synchronize only the donor-document net delta; no runtime,
  database, credential, deployment or remote action is in scope.

## Summary

1. Establish tenant-safe portable SQLAlchemy models, PostgreSQL production storage, SQLite Lite compatibility,
   content-addressed storage and durable jobs/outbox.
2. Add Redis coordination for caches, locks, rate budgets and queue wakeups; add optional MQTT transport for
   distributed collectors and deliveries, with database-backed replay.
3. Add provider adapters, cursor-safe collection, rate-limit state and daily schedule policy.
4. Add AI analysis adapters, immutable feedback, approval-gated preferences and dated digests.
5. Add v2 APIs, single-article multi-format exports, delivery outbox and tenant-scoped public digest projection.
6. Replace navigation-heavy UX with an inbox, date archive and right-side floating panels.
7. Provide a read-only legacy migration inspector and keep all live/data gates closed.
8. Add one reusable connector capability/risk lifecycle for hosted aggregators, Feed services, paid APIs, AI
   enrichment and delivery platforms.
9. Treat SupSub as an optional secondary Feed/discovery/subscription/enrichment connector; keep runtime binding,
   OAuth, purchase, quota use and external writes behind later gates.
10. Require dated verification receipts so later services can be evaluated without creating incompatible paths.
11. Index all current product/research/process documents and reconcile the old download API behavior against actual
    core source as implemented, partial, planned, reference-only or superseded.

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
| WU-6 Connector revision | app-root | research/docs | main-only | accepted v2 | public evidence only | registry, template and SupSub adoption decision | app-root | no runtime binding |
| WU-7 SupSub canary | app-root | future adapter/runtime | main-only | WU-6 + user gate | test account, one-way read first | fixture contract then bounded canary | app-root | disable connector |
| WU-8 Legacy documentation migration | app-root | research/docs | main-only | accepted WU-1..6 | donor docs and read-only current source; no source/data copy | index, migration matrix and synchronized Controlled owners | app-root | preserve donor as reference-only |

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
- External aggregators can silently create a second truth, duplicate provider spend or cause sync loops unless every
  identity, direction, cursor and billable operation is persisted locally.
- SupSub CLI has external writes, quota-consuming AI work and public/non-revocable share behavior; command-level
  allowlists and risk gates are required before any adapter implementation.
- A legacy README can overstate current equivalence. Every migrated capability must be checked against the actual
  core source, and partial/planned work must remain visible rather than being collapsed into “migrated”.

## Verification

- Source evidence and `doc_drift`: README/config previously exposed SQLite/MySQL/PostgreSQL, an embedded Redis
  server and HTTP cascade without authoritative storage profiles or MQTT/outbox semantics; the current docs now
  define those boundaries and keep v1 behavior explicit.
- RAW-003 provider evidence is isolated in dated research and a reusable verification template; volatile prices and
  limits are not copied into runtime defaults.
- RAW-004 migration evidence is isolated in a repository index and capability matrix. Link, Git-boundary, keyword
  consistency and source-presence checks replace unrelated backend/frontend reruns for this docs-only delta.
- Final document impact and synchronization owner: `project-current`, App Root.
