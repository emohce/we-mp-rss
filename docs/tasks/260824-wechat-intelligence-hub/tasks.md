# 微信公众号智能聚合系统任务台账

Tool: Codex App
Date: 2026-08-24
Updated: 2026-08-30
Task: wechat-intelligence-hub

Documentation level: `controlled`

## Task State

`v3-local-verified / runtime-gated / unpushed`; WU-0..9 retain historical local/static acceptance only.
WU-10..16 acceptance is code/offline scope, not service or user-experience acceptance; the Redis incident impact remains open.

## Work Unit Ledger

| Work Unit | Version | Attempt | Surface | Runtime ID | State | Last Evidence | Blocker | Next Action |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| WU-0 Git/repositories | 1 | 1 | main | app-root | accepted | three repositories verified; branches isolated | none | retain safety refs |
| WU-1 Tiered foundation | 2 | 1 | main | app-root | accepted | portable DDL, leased jobs, outbox and storage-profile tests pass | none | retain live migration gate |
| WU-2 Collectors/rate | 1 | 1 | main | app-root | accepted | one-call provider, shared-source fanout, cursor and fail-closed tests pass | none | live providers remain disabled |
| WU-3 AI/feedback/digest | 1 | 1 | main | app-root | accepted | deterministic/fake CLI, tenant, feedback, digest and export tests pass | none | paid AI remains opt-in |
| WU-4 Floating UI | 1 | 1 | main | app-root | accepted | Vite production build and asset-reference checks pass | browser acceptance excluded | retain global drawer; no route added |
| WU-5 Migration/closeout | 1 | 1 | main | app-root | accepted | offline DDL, Compose parse, docs and split local commits verified | live acceptance excluded | hand off explicit runtime gates |
| WU-6 Connector revision | 1 | 1 | main | app-root | accepted | SupSub primary sources, generic registry and verification template reconciled | none | retain `researched` state |
| WU-7 SupSub adapter/canary | 1 | 0 | future | app-root | deferred-by-scope | D7 generic format/CLI-envelope fixtures exist; no install/login/vendor fixture | explicit external-action gate | obtain authorized supplier fixture/read-only canary |
| WU-8 Legacy documentation migration | 1 | 1 | main | app-root | accepted | donor/current source matrix, index, link and statement checks pass | runtime gaps remain explicit | keep core docs canonical |
| WU-9 CodeNote + AI-DB initialization | 1 | 1 | main | app-root | accepted | project audit OK; resolver 2/2; catalog tests 14/14; AI-DB 15/15 populated | live DB/runtime excluded | keep staging inspection and mutation gates explicit |
| WU-10 Correctness plan | 1 | 1 | main | app-root | accepted | RAW-006, exact manifest, code-link/diff checks | none | local commit then WU-11 |
| WU-11 Versioned schema | 1 | 1 | main | app-root | accepted | 43 focused tests; frozen offline SQL, no startup DDL | live mutation excluded | local schema batch and DBA handoff |
| WU-12 Fresh collection | 1 | 1 | main | app-root | accepted | 53 focused tests; head/backfill, fenced page transaction, durable budgets | live providers excluded | local collector batch |
| WU-13 Digest reconciliation | 1 | 1 | main | app-root | accepted | 60 focused tests; frozen cohort, partial/late revisions, stable/revocable share | live delivery excluded | local digest batch |
| WU-14 Unified preference/content | 1 | 1 | main | app-root | accepted | 71 focused tests; shared ranking, corrections/rules/filters, FTS and content/export | live S3/PG query plans excluded | local coupled API/query/content batch |
| WU-15 Floating workspace | 1 | 1 | main | app-root | accepted | 73 backend + 8 UI state tests; scoped TS/SFC scripts and production build | browser/runtime excluded; served assets sync in WU-16 | one state owner, inline reader and explicit import |
| WU-16 Connectors/operations | 1 | 1 | main | app-root | accepted-local | 91 guarded backend + 10 UI tests; types/build; 129 files/15 references | runtime/canary/browser excluded; prior Redis impact unverified | final local batch, then separate runtime gates |

## Execution Journal

| Event ID | Local Time | Work Unit | Actor | Event | Prior -> Resulting State | Trigger / Evidence | Root Decision / Next Action |
| --- | --- | --- | --- | --- | --- | --- | --- |
| E-001 | 2026-08-24 | WU-0 | app-root | accepted | planned -> accepted | legacy branch split; core/reference clones verified | start WU-1 |
| E-002 | 2026-08-24 | WU-0 | app-root | fallback | full clone -> shallow clone | full history was ~199 MB and transferring slowly; current tree SHA preserved | continue on verified `f54aba5` |
| E-003 | 2026-08-24 | WU-1 | app-root | user steering | SQLite-only -> tiered infrastructure | RAW-002 explicitly allows advanced DB, Redis and MQTT | revise Spec to PostgreSQL/Redis/MQTT profiles before code |
| E-004 | 2026-08-24 | WU-1 | app-root | recovered failure | in-memory SQLite API fixture failed -> package-safe engine setup | `sqlite://` was incorrectly routed through service pool options | broaden dialect detection; preserve file-only directory creation |
| E-005 | 2026-08-24 | WU-1..3 | app-root | contract hardening | global topics/accounts/windows -> workspace topics, shared credentials and continuous 24h digest window | focused tests exposed tenant and scheduling ambiguity | accept corrected contracts |
| E-006 | 2026-08-24 | WU-1..3 | app-root | accepted | implemented -> accepted | 39 focused backend tests; three 460-line dialect DDL outputs; Compose config passes | create backend commit `426c9c1` |
| E-007 | 2026-08-24 | WU-4 | app-root | accepted | implemented -> accepted | Vite production build; 14 index assets present; `dist/assets` equals `static/assets` | create UI commit `754b846` |
| E-008 | 2026-08-24 | WU-5 | app-root | accepted | verification -> accepted | research/operator/task docs reconciled; live/data gates unchanged | create final documentation batch without push |
| E-009 | 2026-08-24 | WU-6 | app-root | requirement revision | accepted v2 -> additive connector requirements | RAW-003 requests SupSub and future service integrations | preserve `we-mp-rss` core and define one connector lifecycle |
| E-010 | 2026-08-24 | WU-6 | app-root | accepted | researched -> accepted documentation scope | public pricing, official CLI source/docs and unresolved contract gaps recorded | keep SupSub runtime `researched` |
| E-011 | 2026-08-25 | WU-8 | app-root | requirement revision | scattered donor evidence -> RAW-004 / Spec revision 4 | user requests full document and research migration into the core directory | reuse Controlled task; migrate semantics, not source/data |
| E-012 | 2026-08-25 | WU-8 | app-root | doc drift correction | implied v1 MCP / undifferentiated legacy feature set -> explicit states | current core has RSS and partial bulk export but no MCP runtime | accept matrix; retain MCP and export gaps as planned/partial |
| E-013 | 2026-08-25 | WU-8 | app-root | accepted | documentation sync -> accepted | index, migration matrix, source boundary, local links, diff and sensitive-pattern checks | create one local docs commit; no push |
| E-014 | 2026-08-25 | WU-9 | app-root | requirement revision | accepted revision 4 -> RAW-005 / revision 5 | user requests CodeNote rules and AI-DB synchronization into the new core | reuse Controlled task; initialize project-local routes and memory |
| E-015 | 2026-08-25 | WU-9 | app-root | implemented | absent -> local initialization | old adapter's no-AI-DB constraint rejected; current code/docs used to populate DB memory | run project/catalog/link/secret/static boundary audits |
| E-016 | 2026-08-25 | WU-9 | app-root | accepted | verification -> accepted | CodeNote project audit, exact resolver routes, catalog tests, populated workspace, JSON/link/diff/secret boundaries; no DB/runtime action | keep reviewable; commit only on a new explicit current-message request |
| E-017 | 2026-08-25 | WU-9 | app-root | accepted | verified-uncommitted -> committed | user renewed commit authorization; three local batches created, then history rebuilt to drop a host absolute path from `vibe/specs/PROJECT_STATUS.md` | keep `44198c3`/`0947b3c`/`f2987dd` local; safety refs retained; no push |
| E-018 | 2026-08-30 | WU-10..15 | app-root | accepted-local | RAW-006 -> six scoped batches | `71367de`, `26b983c`, `201869f`, `4a10003`, `b8932bf`, `9543624`; focused evidence below | preserve both pre-existing dirty hunks; no push |
| E-019 | 2026-08-30 | WU-16 | app-root | isolation incident | direct legacy function import -> Redis-connected queue startup | source chain confirmed; test process exited; possible status writes not inspected | disclose; deny further infrastructure I/O; no cleanup |
| E-020 | 2026-08-30 | WU-16 | app-root | accepted-local | isolated source contract -> guarded offline suite | 91 tests, zero denied I/O attempts, no legacy runtime imports; 10 UI tests/build and artifact equality | local final batch only; Redis impact remains separate gate |

## Checklist

- [x] Complete WU-10..16 code/offline scope; six preceding local commits and this final D7 batch.
- [x] Preserve pre-existing verify/changes hunks; retain intended external-action gates and disclose the Redis isolation breach.
- [x] Synchronize current documentation without promoting static evidence to live acceptance.
- [ ] Independently inspect possible Redis status effects only after a new, exact read-only authorization.

- [x] Inspect current implementation and rules.
- [x] Apply scoped backend changes.
- [x] Apply scoped frontend changes.
- [x] Verify behavior and offline migration DDL.
- [x] Reconcile implementation and documentation.
- [x] Create coherent local commits without push.
- [x] Record final document impact and residual runtime gates.
- [x] Verify SupSub public price, capability, CLI, authentication and high-risk operation boundaries.
- [x] Add a reusable provider registry and verification template for later integrations.
- [x] Keep CLI installation, OAuth, purchase, external writes and quota use unexecuted.
- [x] Reconcile the old README and implementation notes against current core source instead of copying claims.
- [x] Add a canonical documentation index and legacy capability/data migration matrix.
- [x] Correct MCP to `planned` and retain batch export as `partial-current` until its remaining contract is built.
- [x] Keep AGPL source, credentials, runtime data and old repository-only governance documents out of the core.
- [x] Preserve upstream `AGENTS.md` guidance while adding CodeNote adapters and project-local rule routes.
- [x] Populate AI-DB route/schema/business memory and handoff templates without connecting to a database.
- [x] Pass the CodeNote project/catalog/link/JSON/secret/static-boundary audit and accept WU-9.
