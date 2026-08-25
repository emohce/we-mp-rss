# We-MP-RSS Database Memory

Tool: tool-neutral (Codex, Claude, Grok, and any CodeNote-routed agent)
Last verified: 2026-08-25 (`code + document + prior focused tests`; no live DB)

## Stable Owners

| Document | Role | Current evidence boundary |
| --- | --- | --- |
| [system_map.md](system_map.md) | Runtime/database/infrastructure boundary | code + document |
| [connection_registry.md](connection_registry.md) | Project → environment → route → DB/schema → scope/status | no secrets; no live route accepted |
| [schema_inventory.md](schema_inventory.md) | Expected schema/model inventory | code/offline contract, not live schema |
| [business_glossary.md](business_glossary.md) | Terms mapped to durable objects | current Spec + models |
| [core_relationships.md](core_relationships.md) | Key declared/logical relations | SQLAlchemy model evidence |
| [query_patterns.md](query_patterns.md) | Reusable read-only inspection routes | no connection authorization |
| [delivery_log.md](delivery_log.md) | Accepted DB documentation deliveries | initialization only |
| [handoff.md](handoff.md) | Open environment/schema/recovery gates | active |

## Safety

- Global and project rules: [AI-DB entry](../README.md), [rules](../rules.md).
- No password, token, hostname, username or full connection string belongs here.
- `code` and offline DDL evidence describe the expected schema; only an authorized read-only inspection can establish live state.
- A known route never authorizes mutation. DDL/DML/recovery remains user/DBA-operated through a task package.
