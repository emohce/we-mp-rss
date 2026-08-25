# Database Handoff

Updated: 2026-08-25

## Current State

- Stable code/document memory is initialized.
- No live database route, schema snapshot, row-count baseline, backup receipt, migration history or execution-ID recovery contract is accepted.
- No database connection or mutation was performed during initialization.

## Open Gates

1. User/DBA selects an exact non-production environment and supplies a secret-safe read-only route.
2. Run the read-only schema inspector and record environment-specific evidence in a new AI-DB task.
3. Compare actual legacy and `int_*` objects with revision `intelligence-v2-20260824-1`; keep drift explicit.
4. If a migration is needed, author a full `sql.md` handoff with prerequisite inventory, DryRun, exact impact, postcheck, recovery and release order.
5. User/DBA separately approves and executes any DDL/DML. TEST evidence does not authorize production.

## Next Safe Step

The next database step is a user-approved, read-only staging schema inspection. Application startup with `-init True`, migration runners and generated DDL execution are not read-only substitutes.
