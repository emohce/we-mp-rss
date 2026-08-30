# We-MP-RSS Technical Details

Tool: Codex App
Date: 2026-08-25

## Sync Rule

Update when a maintained entrypoint, storage contract, integration boundary, key workflow or focused verification route changes. Database-specific facts also update [AI-DB project memory](../ai-db/project-memory/README.md).

## Request And Work Path

```text
main.py
  -> web.py / FastAPI
  -> apis/ and views/
  -> core/ legacy services and core/intelligence/ v2 services
  -> SQLAlchemy database (durable truth)
  -> optional Redis coordinator/cache
  -> durable outbox -> optional MQTT transport
  -> jobs/ scheduled collection, analysis, digest and delivery

web_ui/src/
  -> global layout
  -> IntelligenceHub floating drawer
  -> authenticated v2 APIs
```

## Module Index

| Boundary | Mechanism | Source | Current note | Evidence |
| --- | --- | --- | --- | --- |
| Runtime entry | FastAPI with job/init flags | `main.py`, `web.py` | init paths can mutate configured DB | code, 2026-08-25 |
| Legacy DB | SQLAlchemy engine/session | `core/db.py` | lazy engine, no compatibility DDL; explicit legacy initialization only | code + focused test, 2026-08-30 |
| Infrastructure profiles | lite/standard/distributed | `core/intelligence/settings.py` | SQLite; PostgreSQL+Redis; optional MQTT | code + document, 2026-08-25 |
| Durable v2 model | `int_*` SQLAlchemy tables | `core/intelligence/models.py` | workspace, collection, AI, feedback, digest, export, jobs, outbox | code, 2026-08-25 |
| Schema handoff | frozen Alembic chain and read-only inspection | `core/intelligence/migration.py`, `tools/intelligence_schema.py` | revision `int_v3_20260830`; applied-version/uniqueness readiness | code + offline test, 2026-08-30 |
| Eventing | coordinator + durable outbox | `core/intelligence/events.py`, `core/intelligence/outbox.py` | MQTT transports events; DB owns state | code + test receipt |
| Content | SHA-256 local/S3 object store | `core/intelligence/storage.py` | DB stores object identity, not provider URL as sole truth | code, 2026-08-25 |
| v3 content path | immutable object binding and hash-checked fallback | `core/intelligence/content.py`, `core/intelligence/collection_state.py` | body-bearing pages bind objects; legacy columns retained | disposable tests, 2026-08-30 |
| Personal relevance | shared SQL ranking and approval/revocation | `core/intelligence/ranking.py`, `core/intelligence/preferences.py` | inbox/digest parity, feedback-first, all-history evidence | disposable tests, 2026-08-30 |
| Local search | persisted search documents and native indexes | `core/intelligence/search.py` | SQLite FTS5; PostgreSQL GIN with literal fallback | SQLite fixture + PostgreSQL SQL compilation, 2026-08-30 |
| APIs | tenant-aware v2 endpoints | `apis/intelligence.py` | article/analysis/feedback/digest/download | code + test receipt |
| UI | Vue floating management | `web_ui/src/components/intelligence/IntelligenceHub.vue` | global drawer; no extra management route | code + build receipt |
| Operators | profile/config/compose docs | `config.example.yaml`, `compose/docker-compose.intelligence.yaml`, `docs/intelligence-hub.md` | real services remain deployment-gated | document + static parse |

## Known Runtime Boundary

- Engine construction is lazy; explicit legacy initialization and schema application remain mutations. Do not
  treat server startup as read-only or metadata existence as proof of a completed migration.
- The Controlled verification used disposable databases and offline DDL; it did not inspect or mutate a user database.
- PostgreSQL, Redis, MQTT and provider connectivity remain unverified in an authorized staging environment.
- Current batch-export/MCP/provider gaps remain classified in the [migration matrix](../../docs/migrations/wechat-download-api.md).
