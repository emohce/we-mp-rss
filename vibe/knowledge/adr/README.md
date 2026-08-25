# ADR Index

Tool: tool-neutral (Codex, Claude, Grok, and any CodeNote-routed agent)

Use this directory for durable architecture decisions that are not already owned by the current Controlled Spec.

## Current Decisions

- Tiered storage, durable truth, Redis/MQTT roles, floating management and provider-neutral connectors are currently owned by the [Controlled Spec](../../../docs/tasks/260824-wechat-intelligence-hub/spec.md) and [architecture guide](../../../docs/intelligence-hub.md); no duplicate ADR is created during initialization.

## Rules

- Create an ADR only for a durable decision, compatibility boundary, ownership change or irreversible tradeoff.
- Link the requirement and implementation evidence; state superseded decisions explicitly.
- Database route/schema observations belong in [AI-DB project memory](../../ai-db/project-memory/README.md), not an ADR.
