# Documentation Rules

Tool: tool-neutral (Codex, Claude, Grok, and any CodeNote-routed agent)
Date: 2026-08-25

## Purpose

Map CodeNote process/documentation governance onto this repository without copying its algorithms.

## Authorities

| Layer | Location | Role |
| --- | --- | --- |
| Global master | [CodeNote VibeAi](../../../CzzProj/CodeNote/AiRef/VibePractice/Vibe_Rules/VibeAi.md) | Cross-project workflow, safety, memory and closeout |
| Process layout | [CodeNote process rules](../../../CzzProj/CodeNote/AiRef/VibePractice/Vibe_Rules/process/rules.md#3-project-location) | Quick/Standard/Controlled and task layout |
| Requirement versioning | [CodeNote requirement owner](../../../CzzProj/CodeNote/AiRef/VibePractice/Vibe_Rules/process/requirement-versioning.md) | Raw requirement, revision and conflict handling |
| DB governance | [CodeNote AI-DB governance](../../../CzzProj/CodeNote/DevelopRef/调试工具/db/governance/README.md#5-workspace-shape-and-naming) | SQL/data safety and workspace shape |
| Project entry | [AGENTS.md](../../AGENTS.md), [CLAUDE.md](../../CLAUDE.md) | Short host/tool routers |
| Project rules | [README.md](README.md) | Local route index |
| Current product Spec | [Controlled Spec](../../docs/tasks/260824-wechat-intelligence-hub/spec.md) | Canonical merged requirement |
| Current process hub | [PROJECT_STATUS.md](../specs/PROJECT_STATUS.md) | Active state and gates |
| Project knowledge | [knowledge index](../knowledge/README.md) | Reusable facts and memory routes |
| Database handoff | [AI-DB entry](../ai-db/README.md) | Project DB facts/tasks; never execution authority |

## Project Mapping

- Existing Controlled work remains in `docs/tasks/260824-wechat-intelligence-hub/`; `vibe/specs/PROJECT_STATUS.md` is a compact router to it. Do not duplicate the task under `vibe/specs/`.
- The current Spec is the requirement authority. No parallel `vibe/requirements/` tree is configured.
- Product, architecture, provider research and migration mappings stay under `docs/`; reusable collaboration facts route to `vibe/knowledge/` and database facts to `vibe/ai-db/project-memory/`.
- New DB task handoffs use `vibe/ai-db/ai-db-tasks/<yyMMdd>/<HHmm-task-id>/`; mutation SQL stays documentation-only for user/DBA execution.
- Keep links relative to the file that owns them and run the CodeNote project audit after documentation-heavy changes.

## Process Contract Routing

- [Process rules](../../../CzzProj/CodeNote/AiRef/VibePractice/Vibe_Rules/process/rules.md) solely own `Quick`, `Standard non-requirement`, `Standard requirement` and `Controlled`. Legacy `L0/L1`, `L2` and `L3/L4` are compatibility vocabulary only and never force a level.
- Standard requirement work uses `raw-requirement.md + spec.md`, with the Spec owner holding the complete requirement evidence. Controlled work uses the globally defined owners; this adapter only maps their existing paths.
- Communication routes to [process/communication-io.md](../../../CzzProj/CodeNote/AiRef/VibePractice/Vibe_Rules/process/communication-io.md); rollout/runtime supervision route to [codex-evolution/rollout/README.md](../../../CzzProj/CodeNote/AiRef/VibePractice/Vibe_Rules/codex-evolution/rollout/README.md) and [codex-evolution/runtime-supervision/README.md](../../../CzzProj/CodeNote/AiRef/VibePractice/Vibe_Rules/codex-evolution/runtime-supervision/README.md). This repository does not copy those algorithms.

## Controlled Closeout

- The Controlled Spec owns scope/revisions; `plan.md` owns logical Work Units; `tasks.md` owns attempts/events; `verify.md` owns evidence and acceptance; `handoff.md` retains only active/unresolved state; `changes.md` inventories multi-file delivery.
- Check prior-task overlap before creating new task folders. User supplements to the same objective revise the existing task unless the authority or goal materially changes.
- Record final documentation impact as `none-with-reason`, `task-only`, `project-current`, `requirement-canonical`, `global-rule` or `template-propagation`.
- Update [PROJECT_STATUS.md](../specs/PROJECT_STATUS.md) when focus, task authority, verification, gates, sibling links or memory routing changes.
- Report Sidecar/main-thread result, Evolution Candidate, verification, memory routing and process-document status. Static/build success never closes live DB, provider, browser, deployment or user-feel gates.
