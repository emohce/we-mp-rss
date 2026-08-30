# Database Handoff

Updated: 2026-08-30

## Current State

- Stable code/document memory is initialized.
- No live database route, schema snapshot, row-count baseline, backup receipt, migration history or execution-ID recovery contract is accepted.
- No database connection or mutation was performed during initialization.
- V3 code/offline handoff is populated; final isolated package suite passes 91 tests. This is not a schema
  application receipt. Separately, an earlier legacy test import connected to Redis and may have written queue
  status; actual effect is unverified, with no recovery performed. See the [incident](../../../docs/tasks/260824-wechat-intelligence-hub/verify.md#v3-test-isolation-incident).

## Open Gates

1. User/DBA selects an exact non-production environment and supplies a secret-safe read-only route.
2. Run the read-only schema inspector and record environment-specific evidence in a new AI-DB task.
3. Compare actual legacy and `int_*` objects with revision `int_v3_20260830`; keep drift explicit and resolve
   the exact source revision through the [v3 package](../ai-db-tasks/260830/0941-intelligence-v3/sql.md).
4. If a migration is needed, author a full `sql.md` handoff with prerequisite inventory, DryRun, exact impact, postcheck, recovery and release order.
5. User/DBA separately approves and executes any DDL/DML. TEST evidence does not authorize production.

## Next Safe Step

The next database step is a user-approved, read-only staging schema inspection. Application startup with `-init True`, migration runners and generated DDL execution are not read-only substitutes.
