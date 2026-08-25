# Workflow Rules

Tool: tool-neutral (Codex, Claude, Grok, and any CodeNote-routed agent)

## Safe Commands

Use the repository's documented commands and prefer the smallest focused verification.

Backend dependencies and local run:

```bash
pip install -r requirements.txt
cp config.example.yaml config.yaml
python main.py -job True -init True
```

The final command starts jobs and initialization hooks and can mutate the configured database. Do not run it merely to verify rule or documentation changes; require the applicable DB/runtime gate first.

Frontend:

```bash
cd web_ui
npm install
npm run build
```

Focused backend tests for the intelligence module:

```bash
python -m unittest discover -s core/intelligence -t . -p 'test_*.py' -v
```

Offline schema rendering is permitted because it does not connect to a database:

```bash
python tools/intelligence_schema.py ddl --dialect sqlite
python tools/intelligence_schema.py ddl --dialect postgresql
python tools/intelligence_schema.py ddl --dialect mysql
```

`tools/intelligence_schema.py inspect --database-url ...` is read-only by design, but connection authorization and a secret-free route still need to be established before use.

## AI Rule Verification

From the repository root:

```bash
python3 ../CzzProj/CodeNote/AiRef/VibePractice/Vibe_Rules/scripts/audit_ai_rules.py . --mode project --fix-links
python3 ../CzzProj/CodeNote/AiRef/VibePractice/Vibe_Rules/scripts/audit_ai_rules.py . --mode project
```

For documentation-heavy changes, also validate repository-local Markdown links, JSON structure, `git diff --check` and a scoped sensitive-pattern scan.

## Verification Boundaries

- Rule/docs-only changes do not require starting FastAPI, Docker, PostgreSQL, Redis, MQTT or a browser.
- Schema/migration work uses [AI-DB governance](../ai-db/README.md): static SQL handoff first, no mutation execution by an agent.
- Never claim live WeChat, provider quota, notification, Redis/MQTT, database migration, deployment or browser acceptance without direct evidence from the authorized environment.
