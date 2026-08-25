# We-MP-RSS AI-DB Workspace

Tool: tool-neutral (Codex, Claude, Grok, and any CodeNote-routed agent)
Date: 2026-08-25

## Boundary

This directory is the project-local documentation workspace for database facts, routes, task plans, SQL handoffs and verification. It is not a database, credential store, connection manager, migration runner or execution authorization.

- Global authority: [CodeNote AI-DB Governance](../../../CzzProj/CodeNote/DevelopRef/调试工具/db/governance/README.md).
- Project-specific rules: [rules.md](rules.md).
- Stable database memory: [project-memory/README.md](project-memory/README.md).
- DB task rules/templates: [ai-db-tasks/rules.md](ai-db-tasks/rules.md), [ai-db-tasks/task-template.md](ai-db-tasks/task-template.md).
- Long-lived DB session rules/template: [ai-db-sessions/rules.md](ai-db-sessions/rules.md), [ai-db-sessions/session-template.md](ai-db-sessions/session-template.md).

## Current Project Mapping

- Application storage profiles: SQLite Lite; PostgreSQL + Redis Standard; PostgreSQL + Redis + MQTT Distributed.
- The SQL database and durable outbox are authoritative. Redis and MQTT are infrastructure components, not database-memory owners.
- Runtime model evidence is in `core/models/`, `core/intelligence/models.py` and `core/intelligence/migration.py`.
- Current schema contract: `intelligence-v2-20260824-1`, verified only by code/tests/offline rendering; no live user database was inspected in this initialization.
- No production/test connection route, host, username, secret or database mutation authorization is registered.

## New DB Work

- Create DB tasks at `ai-db-tasks/<yyMMdd>/<HHmm-task-id>/` with at least `plan.md`, `sql.md` and `verify.md` when execution/deploy risk exists.
- Agents may execute only separately authorized read-only SQL. DDL, DML, stored procedures, migrations, initialization, repairs, permission changes and app startup that mutates schema/data remain human/DBA actions.
- Mutation candidates must be placed in the task `sql.md` package with DryRun, exact scope, expected effects, postcheck, recovery and explicit human confirmation. A generated file is not execution approval.
- Never store passwords, tokens, cookies, personal article content or full connection strings in this directory.

## Transitional Paths

- Product architecture and operator guidance remain in [docs/intelligence-hub.md](../../docs/intelligence-hub.md).
- The existing Controlled requirement/process task remains in [docs/tasks/260824-wechat-intelligence-hub](../../docs/tasks/260824-wechat-intelligence-hub/spec.md).
- No legacy AI-DB task directory is adopted; future DB tasks use the canonical layout above.
