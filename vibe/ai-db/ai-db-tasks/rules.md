# AI-DB Task Rules

Tool: tool-neutral (Codex, Claude, Grok, and any CodeNote-routed agent)

- Follow the global [AI-DB task owner](../../../../CzzProj/CodeNote/DevelopRef/调试工具/db/governance/task-rules.md), [SQL handoff prerequisite contract](../../../../CzzProj/CodeNote/DevelopRef/调试工具/db/governance/sql-handoff-prerequisites.md) and project [AI-DB rules](../rules.md).
- New tasks use `ai-db-tasks/<yyMMdd>/<HHmm-task-id>/`.
- Minimum files: `plan.md`, `sql.md`; add `verify.md` whenever execution, deployment, production, recovery or handoff risk exists. Add `handoff.md` only for active/unresolved transfer state.
- `sql.md` begins with the required execution-status banner and reference index. Every prerequisite is `verified`, `pending`, `blocked` or `not-applicable` with evidence.
- Agents never execute mutation SQL, migration runners, database initialization, stored procedures, permission changes or recovery candidates. The user/DBA supplies execution evidence.
- Use [task-template.md](task-template.md) to create the task plan; use the global SQL/result template for `sql.md`.
