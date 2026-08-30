# Database System Map

Last verified: 2026-08-25
Evidence: `code + document`; no live infrastructure

```text
FastAPI / jobs / provider workers
  -> SQLAlchemy engine and transactions
     -> Lite: SQLite
     -> Standard/Distributed: PostgreSQL
  -> durable collection jobs, cursors, rate-limit ledger and outbox
  -> content identity -> local or S3-compatible object store

Optional acceleration/transport
  -> Redis: cache, leases, coordination and wakeups
  -> MQTT: collector/delivery event transport

Authority
  SQL database + outbox = durable truth
  Redis/MQTT = rebuildable/optional infrastructure, never sole truth
```

## Source Owners

- Engine/startup: `core/db.py`.
- v2 profiles: `core/intelligence/settings.py`.
- v2 models: `core/intelligence/models.py`.
- schema contract: `core/intelligence/migration.py`.
- Redis/MQTT/outbox: `core/intelligence/events.py`, `core/intelligence/outbox.py`.
- content objects: `core/intelligence/storage.py`.
- deployment example: `compose/docker-compose.intelligence.yaml`.

## Mutation Boundary

- Engine setup is lazy and performs no compatibility DDL. Explicit legacy initialization can create files/tables;
  intelligence schema changes use the frozen offline migration chain and remain DBA-gated.
- Offline DDL rendering does not connect; applying it is a DB mutation.
- Redis/MQTT connectivity is not DB acceptance and cannot prove durable state correctness.
