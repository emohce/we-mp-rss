# Core Database Relationships

Last verified: 2026-08-25
Evidence: `SQLAlchemy model declarations`; live FK state unverified

## Declared Relationships

- Workspace → memberships, workspace articles, subscriptions, user article state, collector accounts, collection jobs, analysis/source/feedback/preference data, digests, shares, exports, workflow/delivery and outbox.
- Legacy `articles.id` → workspace article projection, user state, content blob, topic/analysis/feedback/digest item and optional export target.
- Collector account → cursor and optional collection-job account.
- Topic → article-topic assignments.
- Preference proposal → optional accepted preference rule.
- Digest → digest items and share links.

## Correctness Relationships

- Provider fetch result → durable article/job state → cursor update → outbox event; cursor must not move before persistence.
- Database/outbox state → Redis wakeup or MQTT publish; transport failure must be replayable from durable state.
- Explicit feedback → immediate user/workspace state; inferred proposal → separate approval → active rule.
- Article content hash/object key → local/S3 object; metadata remains in SQL and the object store is not a tenant/feedback/task fact source.

## Unverified

- Actual live FK enforcement, indexes, cascade behavior, data cardinality and legacy-table drift require an authorized read-only schema inspection.
