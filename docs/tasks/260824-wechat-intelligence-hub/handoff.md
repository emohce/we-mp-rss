# 微信公众号智能聚合系统交接

Tool: Codex App
Date: 2026-08-24
Task: wechat-intelligence-hub

Documentation level: `controlled`

## Control Plane Snapshot

- Controller: `app-root`
- Work-order version: 2
- Canonical plan: [plan.md](plan.md)
- Canonical task ledger: [tasks.md](tasks.md)
- Last material event: WU-6 connector requirement revision accepted; WU-7 SupSub runtime canary deferred.

## Current State

- Core repository is on local `czz-main`, based on upstream `f54aba5` and containing split local commits through
  `13057d4` before the RAW-003 documentation batch.
- `Wechat2RSS` is a read-only local reference at `0416ecf`.
- Legacy repository retains rollback branch and stash; its `czz-main` has three local documentation commits.
- No live provider, credential, user database, deployment or push action has occurred.
- RAW-002 supersedes the SQLite-only interpretation: PostgreSQL + Redis is the recommended production profile;
  MQTT is optional distributed event transport and SQLite remains the Lite profile.
- RAW-003 adds a provider-neutral connector lifecycle and a SupSub research decision without authorizing runtime
  installation or changing the accepted core implementation.

## Completed

- Online and local source/license research.
- Recoverable legacy Git re-batching.
- Core/reference clone and remote write protection.
- Tiered SQLite/PostgreSQL storage, Redis coordination, optional MQTT/outbox transport and content-store contracts.
- Tenant-scoped v2 article/analysis/feedback/preference/digest/download APIs and cursor-safe provider workers.
- Global right-side intelligence drawer and synchronized production bundle without new navigation routes.
- Controlled requirement, operator, research, verification and error-memory documentation.
- Reusable connector registry/verification template and a dated SupSub price, CLI, authentication and risk snapshot.

## Documentation Impact

- Authority refs: repository rules, upstream source, approved plan and research evidence.
- `doc_drift`: reconciled; no known conflict remains between Spec, implementation, README/config and operator docs.
- Final impact: `project-current`.
- Verification boundary: static/offline evidence accepted; runtime acceptance remains separate.

## Open Runtime Gates

- Back up and inspect the actual database, review generated DDL, then approve a staging migration.
- Configure and connect PostgreSQL/Redis; add MQTT only for a distributed deployment.
- Review current official-account permissions or a paid supplier contract, then authorize one bounded live canary.
- For SupSub, verify Feed/OPML formats, terms, quotas and account fixtures; then separately approve CLI installation,
  OAuth and a one-way read-only canary if still desired.
- Run browser/accessibility acceptance, notification delivery checks and deployment acceptance.

## Next Safe Step

- Continue adding future services through the provider verification template. For a SupSub implementation, the next
  safe step is a user-supplied test Feed/OPML sample or separately authorized test account—not a production sync.
