---
id: we-mp-rss-sqlite-memory-pool-routing
status: verified
scope: core/db.py SQLite engine initialization
fingerprint: sqlite-memory-url-misrouted-to-service-pool-options
first_seen: 2026-08-24
last_verified: 2026-08-24
review_after: 2027-02-24
evidence:
  - ../../tasks/260824-wechat-intelligence-hub/verify.md
  - ../../../core/db.py
tags:
  - sqlalchemy
  - sqlite
  - testing
  - database
---

# SQLite URL pool routing

## Symptom

Creating an engine from the valid in-memory URL `sqlite://` failed because SQLAlchemy received service-database pool options that its SQLite pool does not accept.

## Wrong assumption

SQLite detection was implemented as an exact `sqlite:///` prefix check. That prefix describes common file URLs, but it does not cover in-memory or explicit-driver SQLite URLs.

## Verified root cause

The pool and connection branches classified every URL without the three-slash prefix as a service database. The in-memory URL therefore received `max_overflow` and `pool_timeout`.

## Detection order

1. Inspect the SQLAlchemy URL scheme before selecting pool options.
2. Treat every supported scheme beginning with `sqlite` as SQLite.
3. Restrict filesystem creation logic separately to file-backed `sqlite:///` URLs.
4. Compile or open both a file-backed and an in-memory SQLite engine.

## Prevention rule

Route engine and PRAGMA behavior by the SQLite dialect family, not by one file-URL spelling. Keep file creation behind the narrower file-backed check.

## Alternative Route

- Status: `verified`
- Preconditions: the URL is supplied to `core.db.Db.init`.
- Steps: detect `sqlite*`; omit service pool sizing; retain SQLite connection arguments and PRAGMAs; use the narrow `sqlite:///` check only for creating a parent directory/file.
- Verification: the isolated v2 API contract imports with `DB=sqlite://`, and the existing file-backed foundation suite remains green.
- Applicability boundary: SQLAlchemy SQLite URLs only; PostgreSQL and MySQL continue to use configured service pool sizing.
- Fallback: use a temporary file-backed SQLite URL if a third-party dialect does not support in-memory operation.

## Occurrence History

| Occurrence | Date | Task | Trigger | Failed route | Recovery | Outcome |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | 2026-08-24 | wechat-intelligence-hub | isolated API contract test | `sqlite://` entered service pool branch | classify the complete SQLite scheme family | verified |
