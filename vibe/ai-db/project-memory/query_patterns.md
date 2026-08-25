# Read-Only Query Patterns

Last verified: 2026-08-25

## Preferred Route

- Use `tools/intelligence_schema.py inspect --database-url <secret-delivered-route>` only after the environment route and read-only connection are explicitly authorized. Do not paste the URL into task docs or logs.
- The inspector reports expected/missing/unexpected `int_*` tables and columns. It does not prove data correctness, migrations, row-level tenant isolation, index performance or release readiness.
- For deeper inspection, create an AI-DB task and place each read-only statement plus its result directly in `sql.md`, labelled by environment and source.

## Current Library

No reusable live query is accepted yet. Add one only after dialect, route, permission, result shape, sensitive-data boundary and last-verified evidence are known. SQL snippets must follow the global `-- <++>` selectable-segment markers.
