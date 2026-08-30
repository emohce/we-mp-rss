# Schema Inventory

Last verified: 2026-08-30
Evidence: `code + prior disposable tests + offline DDL`; live state unverified

## Contract

- Expected intelligence schema revision: `int_v3_20260830`; predecessor `int_v2_20260824`.
- Model owner: `core/intelligence/models.py` on shared SQLAlchemy metadata.
- Required legacy dependency: `articles`.
- Inspection owner: `core/intelligence/migration.py::inspect_schema`.
- Offline DDL owner: `core/intelligence/migration.py::render_ddl` via `tools/intelligence_schema.py ddl`.

## Expected Intelligence Tables

| Domain | Tables |
| --- | --- |
| Workspace/access | `int_workspaces`, `int_workspace_memberships`, `int_workspace_articles`, `int_workspace_subscriptions`, `int_user_article_states` |
| Content/provider | `int_article_content_blobs`, `int_collector_accounts`, `int_collector_cursors` |
| Collection/control | `int_collection_jobs`, `int_rate_limit_ledgers` |
| AI/preferences | `int_topics`, `int_article_topics`, `int_analysis_runs`, `int_source_profiles`, `int_feedback_events`, `int_preference_rule_proposals`, `int_preference_rules` |
| Digest/export/share | `int_digests`, `int_digest_items`, `int_share_links`, `int_export_jobs` |
| Workflow/delivery | `int_workflow_jobs`, `int_delivery_channels`, `int_outbox_events` |
| v3 collection | `int_source_checkpoints`, `int_collection_runs`, `int_request_budgets` |
| v3 daily coverage | `int_daily_runs`, `int_daily_run_sources`, `int_digest_revisions` |
| v3 preferences/search | `int_saved_filters`, `int_search_documents`; SQLite FTS5 / PostgreSQL GIN |
| v3 provenance/usage | `int_connector_identities`, `int_connector_usage` |

V3 adds rule version/revocation and digest run/revision/hash/coverage columns, permits multiple article pointers
to one content hash, and makes shared collector labels unique through a partial index. Runtime readiness checks
the applied version and uniqueness constraints, not only table names. Ordinary missing indexes are advisories.
Execution remains governed by the [v3 handoff](../ai-db-tasks/260830/0941-intelligence-v3/plan.md).

## Current Evidence

- Disposable SQLite tests previously exercised model/service contracts.
- SQLite, PostgreSQL and MySQL dialects previously rendered offline DDL; MySQL renderability is portability evidence, not an accepted production profile.
- No authorized live schema inventory, row counts, collation/charset, extension list, migration history or unexpected-object review exists yet.
