# Intelligence v3 schema handoff

Date: 2026-08-30
State: static-verified / execution-blocked

## Goal and scope

Continue [WU-11](../../../../../docs/tasks/260824-wechat-intelligence-hub/plan.md#active-v3-remediation):
freeze the 24-table v2 baseline and add ten v3 tables, six columns and search/index support without touching a
user database. Existing articles/content/feedback remain in place. No credential or infrastructure migration.

## Sources and decision

- [Project DB rules](../../../rules.md) and [connection registry](../../../project-memory/connection_registry.md)
  retain the human-execution boundary. The environment is pending, not inferred from local configuration.
- [Frozen baseline](../../../../../migrations/intelligence/versions/int_v2_20260824.py#L1) and
  [v3 delta](../../../../../migrations/intelligence/versions/int_v3_20260830.py#L1) are independent of mutable models.
- [Offline renderer](../../../../../core/intelligence/migration.py#L136) uses Alembic SQL mode. Online migration
  is intentionally unavailable. [SQL/result handoff](sql.md) is the sole manual gate.
- [Alembic offline documentation](https://alembic.sqlalchemy.org/en/latest/offline.html) supports SQL generation
  and explicit start:end ranges; installed Alembic 1.16.5 was used without upgrading dependencies.

## Verification and recovery

Focused checks cover model metadata, both offline dialects, missing-file inspection, version readiness and lazy
engine setup. [Evidence](verify.md) is not a live migration receipt. Recovery/logging/backup and a registered
staging route are blocked; no destructive downgrade is supplied. New backend/worker release follows DBA
schema/version postcheck, never the reverse.
