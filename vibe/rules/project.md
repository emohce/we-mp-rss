# Project Rules

Tool: tool-neutral (Codex, Claude, Grok, and any CodeNote-routed agent)
Date: 2026-08-25

## Project Profile

- Name: `we-mp-rss`, the sole runnable core for the WeChat intelligence aggregation system.
- Upstream: `rachelos/we-mp-rss`; local implementation branch: `czz-main`.
- License: MIT. `ttttmr/Wechat2RSS` and `wechat-download-api` are reference/donor repositories only; do not copy incompatible or unapproved source.
- Backend: Python, FastAPI, SQLAlchemy 2, APScheduler, Playwright/Selenium-compatible WeChat drivers.
- Frontend: Vue 3, Vite, TypeScript, Arco Design and Ant Design Vue.
- Infrastructure profiles: SQLite Lite; PostgreSQL + Redis Standard; optional MQTT Distributed; local or S3-compatible content storage.
- Current requirement owner: [微信公众号智能聚合系统 Controlled Spec](../../docs/tasks/260824-wechat-intelligence-hub/spec.md).

## Runtime Layout

| Area | Path | Role |
| --- | --- | --- |
| Entry | `main.py`, `web.py` | FastAPI app, job/init flags and router registration |
| Domain/backend | `core/` | legacy models/services plus `core/intelligence/` v2 contracts |
| HTTP/UI handlers | `apis/`, `views/` | API and legacy view endpoints |
| Scheduled work | `jobs/` | article, account, intelligence and notification jobs |
| Provider/browser | `driver/` | WeChat/auth/browser drivers and anti-crawler behavior |
| Frontend | `web_ui/src/` | Vue source; intelligence UI is a global floating surface |
| Built UI | `static/` | generated/served production assets |
| Data/infrastructure | `core/db.py`, `core/intelligence/`, `compose/` | SQLAlchemy, profiles, Redis/MQTT and object storage |
| Product docs | `docs/` | current requirements, architecture, research and handoff |
| AI governance | `vibe/` | project rules, status, knowledge and AI-DB handoff |

## Business Invariants

- `we-mp-rss` remains the only runnable core; integrate new behavior through existing services rather than a second backend.
- Article metadata, tenant/workspace state, feedback, cursors, jobs, usage and outbox are durable database facts.
- Redis may accelerate cache, leases, rate limits and wakeups; MQTT may transport events. Neither is the only copy of authoritative state.
- Cursor advancement happens only after durable article/job state succeeds; collection must keep budgets, backoff and idempotency explicit.
- Topic filtering may fold, rank or explain articles but must not silently delete them.
- Explicit feedback can take effect immediately; inferred preference proposals require user approval before becoming durable rules.
- Core navigation stays compact; management capabilities use floating/drawer surfaces unless a separate page is explicitly approved.
- External services are provider-neutral connectors with provenance, secret references, quota/use ledgers and one-way read-first defaults.

## High-Risk Areas

- `config.yaml`, `.env`, `data/`, cookies, tokens, Access Keys, proxy, webhook and provider credentials.
- `core/db.py` can create a SQLite file, run `ALTER TABLE` compatibility changes and `metadata.create_all()` during normal application initialization. Starting the app with init enabled is therefore a database-mutation action.
- `tools/intelligence_schema.py inspect` opens a read-only inspection path by contract; `ddl` renders offline DDL. Neither output is execution approval.
- Migration scripts, `fix_db_now.py`, `fix_user_id.py`, `init_sys.py`, startup init flags and database repair utilities may mutate data/schema and require a separate user/DBA gate.
- Live WeChat collection, browser login, proxy switching, SupSub OAuth/purchase/deepread/share, external notification and paid/quota-consuming AI calls require explicit authorization.
- Deployment, publish, push and destructive cleanup remain separate gates.

## Local Policy

- Inspect the current requirement, relevant source and current status before implementation.
- Preserve existing upstream behavior and unrelated user changes; keep changes on task-owned paths/hunks.
- Do not log SQL parameters by default because article content, feedback and secrets may be present.
- Treat build/static checks as evidence only; they do not prove database, provider, browser, deployment or user-feel acceptance.
