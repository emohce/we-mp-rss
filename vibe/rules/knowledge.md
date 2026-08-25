# Knowledge Rules

Tool: tool-neutral (Codex, Claude, Grok, and any CodeNote-routed agent)

## Routing

- Project knowledge index: [../knowledge/README.md](../knowledge/README.md)
- Technical map: [../knowledge/technical-details.md](../knowledge/technical-details.md)
- ADR index: [../knowledge/adr/README.md](../knowledge/adr/README.md)
- Error memory: [../knowledge/error-memory/README.md](../knowledge/error-memory/README.md)
- Active process: [../specs/PROJECT_STATUS.md](../specs/PROJECT_STATUS.md)
- Database memory and handoff: [../ai-db/README.md](../ai-db/README.md)
- Product/current documentation: [../../docs/README.md](../../docs/README.md)

## Write Policy

- Search current project docs and memory before adding another owner.
- Store reusable verified facts with source labels such as `code`, `document`, `test`, `live`, `user-confirmed` or `inference`.
- Keep product requirements in the Controlled Spec, database facts in AI-DB project memory, and durable architectural decisions in ADRs.
- Never store credentials, tokens, cookies, personal article contents, secret URLs or connection strings.
- When behavior changes, update the current authority and link any historical source; do not make the knowledge index a duplicate Spec.

## AI-DB Boundary

- Application databases and `vibe/ai-db/` are different things. The latter is a documentation workspace only.
- Stable route identity, schema evidence and DB handoff state belong in `vibe/ai-db/project-memory/`.
- Runtime SQLAlchemy models and migrations remain source evidence until validated against an authorized live environment.
