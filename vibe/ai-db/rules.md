# We-MP-RSS AI-DB Rules

Tool: tool-neutral (Codex, Claude, Grok, and any CodeNote-routed agent)

## Authorities

- Global safety/workspace owner: [AI-DB Governance](../../../CzzProj/CodeNote/DevelopRef/调试工具/db/governance/README.md).
- SQL handoff prerequisites: [global prerequisite contract](../../../CzzProj/CodeNote/DevelopRef/调试工具/db/governance/sql-handoff-prerequisites.md).
- Project runtime constraints: [project rules](../rules/project.md).
- Current product/storage requirement: [Controlled Spec](../../docs/tasks/260824-wechat-intelligence-hub/spec.md).
- Stable route/schema memory: [project-memory/README.md](project-memory/README.md).

## Project Sources And Dialects

- Configuration route owner: `config.example.yaml` plus local-only `config.yaml`/environment variables.
- SQLAlchemy models: legacy `core/models/` and intelligence `core/intelligence/models.py`.
- Engine/startup behavior: `core/db.py`.
- Schema inspection/offline rendering: `core/intelligence/migration.py`, `tools/intelligence_schema.py`.
- Supported application dialect evidence: SQLite and PostgreSQL profiles; MySQL DDL rendering exists for portability checks but is not an accepted production profile for Intelligence Hub.
- Stable project-memory path: `vibe/ai-db/project-memory/`.

## Risk Objects

- All legacy application tables and every `int_*` table.
- Explicit legacy `core/db.py::create_tables()` and frozen intelligence migrations; connection setup no longer
  runs compatibility `ALTER TABLE` or explicit SQLite-file creation.
- Files under `migrations/`, `fix_db_now.py`, `fix_user_id.py`, `init_sys.py` and any startup `-init True` path.
- Tenant/workspace membership, article content/state, feedback/preference, collection cursor/job/rate-limit, digest/share/export, delivery and outbox data.
- Provider credentials, secret references and content that may contain personal or copyrighted data.

## Local SQL Policy

- Evidence labels are `code`, `document`, `test`, `live`, `IDEA DBTools`, `cache` or `inference`; code/model facts are not live schema proof.
- Do not include credentials or SQL parameter plaintext in logs/documents.
- Read-only inspection must use a registered environment route and an approved secret delivery mechanism; connection strings never enter Markdown.
- Mutation SQL is documentation-only for user/DBA execution. Keep DDL and DML separate and follow the global DryRun/real-execution, `ExpectedDatabase`, result and recovery contracts.
- Offline `ddl` rendering is allowed; applying rendered DDL is a separate mutation gate.
- App startup with initialization enabled is not a smoke-test shortcut because it can create/alter schema.
- Redis commands and MQTT publish operations are external runtime actions, not DB queries. Their connectivity or mutation requires the corresponding runtime gate.

## Recovery

- No accepted shared execution-ID recovery contract is currently registered for this repository.
- Until a DB task defines and verifies one, mutation recovery is `blocked` rather than inferred from SQLAlchemy rollback or a database backup assumption.
- Backups, maintenance window, executor/DBA authorization and release sequencing are environment-specific and must be recorded per task.
