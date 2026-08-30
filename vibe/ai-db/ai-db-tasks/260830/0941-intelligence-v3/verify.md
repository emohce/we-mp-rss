# Intelligence v3 schema verification

Date: 2026-08-30
Evidence: code + offline + isolated tests; NOT live database evidence

- 16 focused migration/foundation tests passed. The renderer is tested with engine connections forbidden.
- SQLite base→head: 618 lines; PostgreSQL base→head: 614 lines. V2→head: 176 / 172 lines.
- Every model table is present in the frozen full render. Historical revisions do not import application models.
- Schema-shaped fixtures without revision history are not runtime-ready. Missing-file inspection creates no file.
- Engine setup no longer calls compatibility DDL or opens a SQLite file. Explicit legacy initialization remains
  a mutation; intelligence workers require table/unique-constraint/version readiness.
- No online migration, schema stamping, real database, provider or service was run.
- Final WU-16 package verification passes 91 isolated tests under a pre-import I/O guard, zero denied attempts
  and no legacy runtime imports. It does not add live SQL evidence. The earlier Redis-connected legacy import
  is separately disclosed in the [Controlled incident](../../../../../docs/tasks/260824-wechat-intelligence-hub/verify.md#v3-test-isolation-incident),
  and possible queue-status effects remain unverified; the preceding no-service statement describes D2 only.
- Read-only staging precheck, same-session DryRun, execution/log/recovery and dependent release: pending/blocked
  as specified in [SQL handoff](sql.md). These gates cannot be closed by the tests above.
