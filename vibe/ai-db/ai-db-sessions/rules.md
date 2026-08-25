# AI-DB Session Rules

Tool: tool-neutral (Codex, Claude, Grok, and any CodeNote-routed agent)

- Follow the global [AI-DB session owner](../../../../CzzProj/CodeNote/DevelopRef/调试工具/db/governance/session-rules.md).
- Create a session only for a DB topic that spans multiple task directories, staged DBA evidence, or a long-lived environment/release dependency.
- New session documents use `ai-db-sessions/<yyMMdd>/<HHmm-session-id>.md` and start from [session-template.md](session-template.md).
- Store compressed state and links only; never paste secrets, full result dumps, personal data or raw transcripts.
- Promote stable route/schema facts to [project memory](../project-memory/README.md) and keep task-specific SQL/results in the owning task.
