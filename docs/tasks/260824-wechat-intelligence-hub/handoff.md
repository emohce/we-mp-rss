# 微信公众号智能聚合系统交接

Tool: Codex App
Date: 2026-08-24
Updated: 2026-08-30
Task: wechat-intelligence-hub

Documentation level: `controlled`

## Control Plane Snapshot

- Controller: `app-root`
- Work-order version: 6
- Canonical plan: [plan.md](plan.md)
- Canonical task ledger: [tasks.md](tasks.md)
- Last material event: WU-10 plan `71367de`, WU-11 schema `26b983c`; WU-12 collection passes 53 focused tests.
  WU-13 daily reconciliation is active; WU-14..16 are pending. WU-7 live SupSub canary remains deferred.

## Current State

- Core repository is on local `czz-main`, based on upstream `f54aba5` and containing split local commits through
  `d44a41e`. The RAW-005 CodeNote/AI-DB initialization is committed as `0947b3c` plus ledger sync `f2987dd`; an
  unrelated pre-existing `tools/fix_db.py` splice repair is committed separately as `44198c3`. Nothing is pushed.
- `Wechat2RSS` is a read-only local reference at `0416ecf`.
- Legacy repository retains rollback branch and stash; its `czz-main` has three local documentation commits.
- No live provider, credential, user database, deployment or push action has occurred.
- RAW-002 supersedes the SQLite-only interpretation: PostgreSQL + Redis is the recommended production profile;
  MQTT is optional distributed event transport and SQLite remains the Lite profile.
- RAW-003 adds a provider-neutral connector lifecycle and a SupSub research decision without authorizing runtime
  installation or changing the accepted core implementation.
- RAW-004 makes this core repository the only current documentation home and classifies every relevant donor
  behavior. It corrects MCP to `planned` and batch export to `partial-current` rather than claiming full parity.
- RAW-005 initializes the core's own CodeNote route chain and populated AI-DB documentation/memory workspace. The
  CodeNote catalog keeps `wechat-download-api` and `we-mp-rss` as separate stable identities; no DB action is implied.

## Completed

- Online and local source/license research.
- Recoverable legacy Git re-batching.
- Core/reference clone and remote write protection.
- Tiered SQLite/PostgreSQL storage, Redis coordination, optional MQTT/outbox transport and content-store contracts.
- Tenant-scoped v2 article/analysis/feedback/preference/digest/download APIs and cursor-safe provider workers.
- Global right-side intelligence drawer and synchronized production bundle without new navigation routes.
- Controlled requirement, operator, research, verification and error-memory documentation.
- Reusable connector registry/verification template and a dated SupSub price, CLI, authentication and risk snapshot.
- Canonical [documentation index](../../README.md) and
  [legacy requirement/implementation migration matrix](../../migrations/wechat-download-api.md), including data,
  license, security and not-yet-implemented boundaries.
- CodeNote adapters, project rules, status/knowledge routes, stable project catalog/binding, and a 15-file populated
  [AI-DB workspace](../../../vibe/ai-db/README.md) with environment/schema/business/recovery boundaries.

## Documentation Impact

- Authority refs: repository rules, upstream source, approved plan and research evidence.
- `doc_drift`: reconciled; the previous missing project route/AI-DB owner is now synchronized without copying the old
  repository's no-AI-DB constraint or CodeNote owner bodies.
- Final impact: `requirement-canonical + project-current`; CodeNote catalog/error-memory projections are linked siblings.
- Verification boundary: static/offline evidence accepted; runtime acceptance remains separate.

## Open Runtime Gates

- Back up and inspect the actual database, review generated DDL, then approve a staging migration.
- Configure and connect PostgreSQL/Redis; add MQTT only for a distributed deployment.
- Review current official-account permissions or a paid supplier contract, then authorize one bounded live canary.
- For SupSub, verify Feed/OPML formats, terms, quotas and account fixtures; then separately approve CLI installation,
  OAuth and a one-way read-only canary if still desired.
- Run browser/accessibility acceptance, notification delivery checks and deployment acceptance.
- Implement and verify tenant-scoped Feed/MCP only as separate work; extend the current batch exporter with
  date/window/incremental scope, HTML/EPUB and explicit no-hidden-provider-call behavior rather than copying donor code.
- For database work, create a canonical AI-DB task and resolve a user-approved read-only staging route first; app
  startup with initialization, generated DDL, migration runners and data repair remain human/DBA-gated mutations.

## Next Safe Step

- Active implementation follows [v3 seven-batch plan](plan.md#active-v3-remediation), continuing with WU-13
  coverage/revisions after WU-12 local commit. Current-turn authorization includes local scoped commits
  only. Preserve unrelated verify/changes hunks; do not reset, stash, change other worktrees or push.
- Historical WU-1..9 success does not close current head-poll, digest-barrier, common-ranking and reader-state gaps.

- For product implementation, take one planned/partial row from the migration matrix and create a scoped acceptance
  slice. For DB validation, the next safe step is a separately approved read-only staging schema inspection; for
  SupSub, use a user-supplied Feed/OPML fixture or separately authorized test account—not a production sync.
