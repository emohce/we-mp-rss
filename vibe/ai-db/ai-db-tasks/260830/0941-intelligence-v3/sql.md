# Intelligence v3 SQL and execution boundary

> **EXECUTION STATUS**
> - Project/task: we-mp-rss / intelligence-v3; candidate: int_v2_20260824 → int_v3_20260830.
> - Target environment/route/database: pending / not registered / pending.
> - Environment evidence: pending; no connection. Routine/helper deployment: not deployed.
> - DryRun: not run; no same-environment receipt. Agent activity: NOT_MUTATED for user databases.
> - Real execution: not authorized. Recovery readiness: blocked; release: blocked.
> - Evidence: code + offline render + isolated model tests only. This document is not mutation authorization.

## Reference index

- [Project DB rules and global governance route](../../../rules.md).
- [Environment registry](../../../project-memory/connection_registry.md).
- [Task plan](plan.md), [verification](verify.md), [Controlled Spec](../../../../../docs/tasks/260824-wechat-intelligence-hub/spec.md).
- [Frozen baseline](../../../../../migrations/intelligence/versions/int_v2_20260824.py#L1),
  [delta](../../../../../migrations/intelligence/versions/int_v3_20260830.py#L1),
  [render-only tool](../../../../../tools/intelligence_schema.py#L1).
- [Recovery boundary](../../../project-memory/handoff.md): blocked; no accepted shared execution-ID recovery.
- [Release/runbook](../../../../../docs/intelligence-hub.md#迁移和验收边界).
- Error memory: not-applicable; no live migration failure was observed. Frozen-schema and missing-file checks are
  preventative contracts, not fabricated runtime recovery evidence.

## Prerequisites and manual order

| Order | Dependency / action | State | Expected result / stop condition |
| --- | --- | --- | --- |
| 0 | Exact environment, ExpectedDatabase, dedicated read-only connection / verify-only | pending | Actual identity byte-matches approval; a name alone is not proof |
| 1 | Backup, two-level execution/operation logging, Reason capture, recovery, maintenance window / verify-only | blocked | DBA-owned plan and restore proof; no default log schema invented |
| 2 | Legacy articles columns and current int_* tables/indexes/history / verify-only | pending | Match frozen baseline; partial schemas or duplicate global collector labels block |
| 3 | Baseline / execute-if-absent | pending | Only an empty int_* namespace; an existing v2 schema needs separately reviewed stamp after exact precheck |
| 4 | v3 delta / deploy-required | pending | Ten tables, six columns, shared-content nonunique index, global-account partial unique index and FTS support |
| 5 | Version/constraints/row-count postcheck / verify-only | pending | int_schema_version has exactly int_v3_20260830 and the expected contract |
| 6 | Backend, UI, then enabled jobs / deploy-required | blocked | Same-environment schema and recovery acceptance first |

SQLite requires FTS5 with trigram support; PostgreSQL uses built-in simple-text GIN (no extension install).
No business-row rewrite is included. Version bookkeeping is metadata DML; schema/index/FTS statements are DDL.
Separate those execution sections in the DBA-reviewed package and preserve revision order. Legacy missing-column
repair and existing duplicate collector reconciliation need their own exact scope; never guess or auto-delete.

## Step 1 DryRun — not run

Offline rendering is not database DryRun. Safe input is dialect plus an explicit source revision, no URL or secret.
The renderer has no online command. Review generated DDL and version-metadata DML separately; bind the reviewed
digest, ExpectedDatabase, short Reason, exact objects, pre-state and session into the DBA receipt. Default
execution intent is DryRun=1 / ConfirmApply=0 / ShowDetail=0; no executable generic mutation wrapper is supplied.

Read-only version postcheck (only after the table is confirmed to exist):

```sql
-- <++>
SELECT version_num FROM int_schema_version ORDER BY version_num;
-- <++>
```

Result: not executed. Expected exactly one head row after execution. Before execution, match the approved source
revision. Missing/unexpected version, constraints, columns, FTS support, duplicate globals or recovery proof stops.

## Step 2 Real execution — blocked

The exact generated artifact and digest must be reviewed for a registered staging environment. A new schema may
use base→head; an exactly verified v2 schema uses v2→head only. Never run base against existing tables, stamp an
unverified schema, run a downgrade, or start the application as a migration shortcut. Full baseline and delta are
mutually exclusive routes, not two independent whole-file operations. User/DBA execution requires fresh approval,
DryRun=0 / ConfirmApply=1, remark/log checks, write-set snapshots and nonzero execution ID from the approved plan.

Expected outcome: zero business articles or feedback rewritten; schema objects and revision metadata match the
manifest. Actual result: not executed. No execution ID, elapsed time or affected-row count is claimed.

## Postcheck, crash reconciliation and recovery

User/DBA supplies schema/uniqueness/FTS checks, before/after counts and execution/operation-log reconciliation.
Unknown/partial failure stops further DDL, retry, repair, rollback and release. Read-only comparison must bind the
execution ID, candidate digest and exact target; no direct log repair. Shared recovery DryRun/execution/postcheck
remain blocked until a reviewed recovery contract exists. A transaction rollback or backup assumption is not
recovery proof, especially across partial DDL or client disconnect. TEST evidence never clears PRODUCTION.
