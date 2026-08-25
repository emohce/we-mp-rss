# We-MP-RSS AI Rules

Tool: tool-neutral (Codex, Claude, Grok, and any CodeNote-routed agent)

## Initialization

- Reuse the injected [CodeNote master](../../../CzzProj/CodeNote/AiRef/VibePractice/Vibe_Rules/VibeAi.md), or read it once if it was not injected.
- This file is the project entry. Links below are task routes, not an initialization preload list.
- Start with the smallest applicable owner and add another only for a distinct task signal or global guard.

## Task Routes

- Global owner discovery: [CodeNote rule index](../../../CzzProj/CodeNote/AiRef/VibePractice/Vibe_Rules/README.md), only for AI-rule governance or unresolved global ownership.
- Project constraints: [project.md](project.md), for source, configuration, business behavior, security or project-risk work.
- Commands and verification: [workflow.md](workflow.md), before running project commands or selecting checks.
- Knowledge routing: [knowledge.md](knowledge.md), for reusable project facts, ADRs, technical knowledge or memory synchronization.
- Documentation routing: [documentation.md](documentation.md), for Standard/Controlled, documentation-governance, DB/data, cross-repository or deploy-gated work.
- Current process: [PROJECT_STATUS.md](../specs/PROJECT_STATUS.md), for ongoing/overlapping work and active gates.
- Product requirement authority: [Controlled Spec](../../docs/tasks/260824-wechat-intelligence-hub/spec.md).
- Database/data work: [AI-DB workspace](../ai-db/README.md); load its project rules plus the linked global governance before authoring SQL or changing schema/data contracts.
- Matching error memory: [project error-memory index](../knowledge/error-memory/README.md), only when a current symptom or failed route matches.
- Error capture: [error-memory-capture](../../../CzzProj/CodeNote/AiRef/VibePractice/Skills/global/error-memory-capture/SKILL.md), only after a verified reusable failure, user correction, DB/dataFix incident or tool/runtime trap; update the project error-memory route in the same closeout.

## Ownership Boundary

- CodeNote owns reusable cross-project collaboration and DB-safety rules.
- This repository owns its stack, commands, paths, business constraints, current requirements and database facts.
- `docs/tasks/260824-wechat-intelligence-hub/spec.md` remains the canonical product Spec; do not create a parallel `vibe/requirements/` tree.
- `vibe/ai-db/` is documentation and stable database memory. It is not a database, connection profile, migration runner or mutation authorization.

## Closeout

Every AI task reports:

- Verification performed or skipped with reason.
- Memory routing: none, project knowledge, error memory, ADR, AI-DB memory, or user confirmation needed.
- Process-document status: not needed, created, updated, compacted, or archived.
- Any unrun runtime, browser, provider, DB, deployment or user-feel acceptance gate.
