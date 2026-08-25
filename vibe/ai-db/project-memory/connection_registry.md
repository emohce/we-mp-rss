# Database Connection Registry

Last verified: 2026-08-25
Evidence: `code + document`; no live DB route accepted

This registry contains stable route identities only. It never stores hosts, usernames, passwords, tokens or connection strings, and it never grants mutation authority.

| Project | Environment | Route ID | Database/schema | Allowed scope | Evidence/status |
| --- | --- | --- | --- | --- | --- |
| we-mp-rss | local-lite | `config-db-lite` | SQLite path supplied by local `DB`/`config.yaml`; actual file unverified | code/config inspection; disposable tests only | `documented / live-unverified / mutation-not-authorized` |
| we-mp-rss | staging-standard | `pending-staging-standard` | PostgreSQL database/schema pending | none until identity and access are supplied | `unconfigured / blocked` |
| we-mp-rss | staging-distributed | `pending-staging-distributed` | same PostgreSQL truth plus Redis/MQTT routes pending | none until identity and access are supplied | `unconfigured / blocked` |
| we-mp-rss | production | `not-registered` | pending | no access | `blocked / independent DBA-release gate` |

## Resolution Rules

- Resolve the exact environment and route before any connection attempt; a database name alone is insufficient.
- Read-only inspection needs explicit connection authorization and a secret delivery mechanism outside Markdown.
- TEST/staging receipts remain environment-specific and cannot authorize or validate production.
- Any future forward mutation candidate must use the global `ExpectedDatabase` assertion and task-specific user/DBA gate.
