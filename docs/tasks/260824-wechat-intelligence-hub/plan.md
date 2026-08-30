# 微信公众号智能聚合系统执行计划

Tool: Codex App
Date: 2026-08-24
Updated: 2026-08-30
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
- 2026-08-25 deltas reuse the existing Controlled task: first synchronize the donor-document net delta, then
  initialize the core CodeNote route chain and a populated AI-DB documentation workspace. No runtime, database
  connection/mutation, credential, deployment or remote action is in scope.

## Summary

### Active v3 remediation

The current user confirmed D-1..D-7 and local commits. Reuse this task, baseline `d44a41e`; do not reset history,
change other worktrees or absorb the two pre-existing verify/changes hunks. Runtime remains gated.

| Batch / Work unit | Scope and invariant | Acceptance / fallback |
| --- | --- | --- |
| D-1 / WU-10 | Update requirement, plan, impact trace and incomplete v2 claims | Exact document manifest and links; preserve historic receipts |
| D-2 / WU-11 | Frozen Alembic revisions, explicit initialization, checkpoints/runs/usage | Offline two-dialect render and isolated schema contracts; no live migration |
| D-3 / WU-12 | Fresh-head polling, independent backfill, layered durable budgets, enqueue-only subscription | Fake multi-day provider and lease/rate regressions; collector may remain disabled |
| D-4 / WU-13 | Daily source barrier, partial digests, late revisions and revisioned outbox | Fake-clock schedule/coverage/reconciliation tests; visible partial status |
| D-5 / WU-14 | Shared ranking, topic rules, saved filters, local search/content/export | List/digest parity, explicit feedback and Markdown/storage regression tests |
| D-6 / WU-15 | One floating workspace state, inline reader, persisted filters/width, explicit import | Focused state tests, typecheck/build; real browser acceptance remains separate |
| D-7 / WU-16 | Capability-based read-only registry, fixture imports, operations status | Fixture and fail-closed contracts; no provider login, spend or external writes |

### Provisional VerificationImpactTrace (2026-08-30)

| Changed surface | Concrete consumer / affected boundary | Selected checks | Skipped / escalation |
| --- | --- | --- | --- |
| DB model and startup | collector, workflow, service queries, v2 API; legacy DB import | Frozen revision/offline DDL, no-startup-DDL test, isolated model/service tests | User DB and online migration never run; new consumer widens only its check |
| collection checkpoints and budgets | daily scheduler -> leased job -> provider -> persisted visibility | Fake pages across dates, retry/lease/cooldown/budget tests | Live WeChat/Redis excluded |
| digest run/revision | scheduled workflow -> digest -> share/outbox; list ranking shared | Coverage cutoff/late/idempotency and tenant tests | Email/webhook/MQTT network excluded |
| preference/search/download | feedback -> list/digest; detail -> local content/export | Shared ranking, local FTS contract and HTML-to-Markdown tests | Paid AI, historical data migration excluded |
| floating workspace | layout -> drawer -> API -> reader | UI state tests, affected semantic typecheck and production bundle | No backend/dev server launch; user-feel acceptance separate |
| connectors/status | registry -> local file -> identity/usage -> analysis/daily; operations projection | Format/CLI-envelope fixtures, scope/idempotency/budget tests | No vendor account, real content mapping, authentication or payment |
| offline import legacy consumers | connector article -> v1 force refresh / legacy repair selection | Exact source-function AST contract with socket/process/DB guard | Full legacy module startup excluded; import incident tracked in verify |
| no-transport outbox | publisher -> dispatcher claim -> lease acknowledgement/retry | Pending retention, expired lease CAS and attempt exhaustion | No broker/delivery acceptance; historical records not rewritten |
| served build artifacts | Vite dist -> additive static copy -> local index references | Byte equality for 129 generated files and 15 local references | No server/browser/deploy; old cached assets retained |

- Strategy: `main-only`, work budget `U`, child count `0`; coupled contracts and current Full Access keep writes
  in Root. Each batch stays independently reviewable; split a batch further only for an atomicity/size boundary.
- Skills: orchestration (scope/acceptance), git-batch-commit-push (local-only, hunk ownership), doc-memory-closeout
  and document-code-link-audit (current-state synchronization). Use no unrequested global rule or memory writes.
- User-authorized exception: skip only the broken automatic rule-router validation for this turn; all loaded
  substantive rules and risk gates remain in force. No global rule repair is part of this task.
- Documentation impact: `requirement-canonical + project-current`, Root owns updates and stale-claim sweep.
- Full repository suite escalation: none. The intelligence package suite is in scope because all its persistence,
  worker, service and API consumers are affected; unrelated upstream suites are not selected.
- Execution closeout: WU-10..16 local code/offline scope complete; six prior batch commits plus this final batch.
  D7 uses the pre-import offline guard after a legacy import connected to Redis. Earlier Redis status impact is
  unverified and requires separate read-only authority; no cleanup or runtime startup is authorized here.
- D7 batching decision: the registered file-import/operations contract, its API/UI and served bundle must land
  together, including truthful outbox status and legacy no-fetch guards. Generated chunk references and direct
  evidence/incident owners exceed the ordinary size guideline but contain no independent feature or new SQL
  migration. Keep this one coupled seventh batch; preserve unrelated historical document hunks separately.

### Historical v2 plan

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
12. Preserve upstream contributor guidance while adding CodeNote adapters, project rules, a compact current-status
    router and knowledge routes registered to the new core identity.
13. Populate AI-DB environment/schema/business memory and task/session handoff templates without connecting to or
    modifying a database.

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
| WU-9 CodeNote + AI-DB initialization | app-root | rules/docs/catalog | main-only | WU-8 accepted + RAW-005 | core adapters/`vibe`; CodeNote stable catalog/local binding; no DB/runtime | audited project route, populated AI-DB memory and synchronized Controlled owners | app-root | remove only task-owned initialization files/entries |

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
- Blindly copying the old project's adapter would incorrectly suppress AI-DB, while copying CodeNote rule bodies or
  absolute paths would create drift. Routes must be short, relative-link audited and registered under a new identity.
- Schema/model code can be mistaken for live DB truth. AI-DB memory must label code/offline evidence and keep live
  route, mutation, recovery and production gates explicit.

## Verification

- Source evidence and `doc_drift`: README/config previously exposed SQLite/MySQL/PostgreSQL, an embedded Redis
  server and HTTP cascade without authoritative storage profiles or MQTT/outbox semantics; the current docs now
  define those boundaries and keep v1 behavior explicit.
- RAW-003 provider evidence is isolated in dated research and a reusable verification template; volatile prices and
  limits are not copied into runtime defaults.
- RAW-004 migration evidence is isolated in a repository index and capability matrix. Link, Git-boundary, keyword
  consistency and source-presence checks replace unrelated backend/frontend reruns for this docs-only delta.
- RAW-005 evidence uses the CodeNote project audit, workspace resolver/catalog checks, repository-local link/JSON
  validation, scoped secret scanning and DB-boundary statement checks; application or infrastructure startup is excluded.
- Final document impact and synchronization owner: `project-current`, App Root.
