# 微信公众号智能聚合系统任务台账

Tool: Codex App
Date: 2026-08-24
Task: wechat-intelligence-hub

Documentation level: `controlled`

## Task State

`accepted`

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
| WU-7 SupSub adapter/canary | 1 | 0 | future | app-root | deferred-by-scope | no install/login/account fixture | explicit implementation and external-action gate | start with Feed/CLI read-only fixture |

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

## Checklist

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
