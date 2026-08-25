# Database Business Glossary

Last verified: 2026-08-25
Evidence: `Controlled Spec + code`

| Term | Meaning | Durable owner |
| --- | --- | --- |
| Workspace | Isolation boundary for subscriptions, articles, feedback, preferences and digests | `int_workspaces`, memberships |
| Source | Official account or connector source identity | legacy feed/article source plus `source_id` fields |
| Collection cursor | Last durably accepted provider progress, advanced only after persistence succeeds | `int_collector_cursors` |
| Collection job | Idempotent, leased unit of provider work | `int_collection_jobs` |
| Rate-limit ledger | Durable provider/account cooldown and signal state | `int_rate_limit_ledgers` |
| Analysis run | Versioned AI/heuristic output for an article | `int_analysis_runs`, `int_article_topics` |
| Feedback event | Explicit user judgment used to rank/filter and propose preference rules | `int_feedback_events` |
| Preference proposal/rule | Inferred candidate versus user-approved durable behavior | `int_preference_rule_proposals`, `int_preference_rules` |
| Digest | Date-bounded summary projection and its ordered items | `int_digests`, `int_digest_items` |
| Outbox event | Durable event awaiting transport/delivery | `int_outbox_events` |
| Content blob | Content-addressed body/media object referenced by article | `int_article_content_blobs` plus object store |
