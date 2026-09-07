<!-- codenote-local-context:conditional-v3 -->
# Project context

Project-owned conditional detail. Edit this local owner for project-specific facts; global policy stays in the compact core. Commands and inline paths are relative to the repository root unless their original text says otherwise. Read the sections relevant to the affected surface before material work.

## Project context from AGENTS.md

# We-MP-RSS AI Adapter

- For Standard/Controlled, DB/data, cross-repository or deploy-gated work, load [documentation rules](<documentation.md>), the [process hub](<../specs/PROJECT_STATUS.md>) and current [Controlled Spec](<../../docs/tasks/260824-wechat-intelligence-hub/spec.md>).
- Before schema, migration, data-fix, route or SQL work, load the [AI-DB entry](<../ai-db/README.md>). Load only the smallest matching owner/error record.
- Runtime is FastAPI/Python + Vue/Vite + SQLAlchemy, with SQLite Lite, PostgreSQL+Redis Standard and optional MQTT Distributed profiles; DB/outbox remain authoritative.
- Keep `config.yaml`, `.env`, `data/`, tokens, cookies, provider credentials and connection secrets local-only.
- Agents may render offline DDL but never execute DB mutations/migrations, live/paid provider actions, deploy/publish/push, credential writes or destructive cleanup without the applicable gate. Mutation SQL is a human/DBA handoff.
- Preserve unrelated work and behavior;

# Repository Guidelines

## Project Structure & Module Organization
`main.py` starts the FastAPI server defined in `web.py`. Core backend logic lives in `core/`, HTTP endpoints in `apis/`, page handlers in `views/`, scheduled jobs in `jobs/`, and WeChat/browser drivers in `driver/`. Frontend source is in `web_ui/src/`; built assets are served from `static/`. HTML templates for the legacy views live in `public/templates/`. Docker and deployment files are under `compose/` and `Dockerfiles/`. Keep new docs in `docs/` and utility scripts in `tools/` or `script/`.

## Build, Test, and Development Commands
Install backend dependencies with `pip install -r requirements.txt`, then copy `config.example.yaml` to `config.yaml`. Run the full backend locally with `python main.py -job True -init True`; this starts FastAPI, jobs, and initialization hooks. Frontend development happens in `web_ui/`: `npm install`, `npm run dev`, and `npm run build`. For the MQTT helper in `qtserver/`, use `npm install` and `npm run start`. Docker development should read runtime settings from `/.env`; use `docker compose -f compose/docker-compose.dev.yaml up -d --force-recreate` and avoid hardcoding credentials or proxy settings in compose files.

## Coding Style & Naming Conventions
Follow the existing style before introducing cleanup. Python uses 4-space indentation, snake_case for modules/functions, and grouped feature folders such as `core/notice/` and `apis/`. Vue files in `web_ui/src/views/` use PascalCase filenames like `AccessKeyManagement.vue`; composable utilities and API wrappers use camelCase or lower-case filenames such as `auth.ts` and `messageTask.ts`. There is no enforced formatter config in the repo, so keep imports tidy, avoid broad refactors, and match surrounding conventions.

## Testing Guidelines
Backend test coverage is minimal and mostly lives near the code, for example `core/lax/test_template_parser.py`. Run it from that directory with `cd core/lax && python -m unittest test_template_parser.py`. When touching API, scraping, or scheduler code, also do a local smoke test by starting `python main.py` and exercising the affected UI or endpoint. Frontend changes should at least pass `npm run build`.

## Commit & Pull Request Guidelines
Recent history includes `feat:` commits alongside ad-hoc messages like `1.4.9-Fix`; use Angular-style commits going forward, for example `fix: handle expired WeChat cookies`. Keep the body as `-` prefixed lines without blank lines.  PRs should include a short problem statement, the key changes, linked issues when relevant, config or migration notes, and screenshots for UI changes.
This clone should keep `origin` pointed at your fork and `upstream` pointed at `https://github.com/rachelos/we-mp-rss`.

## Security & Configuration Tips
Do not commit `config.yaml`, `/.env`, tokens, cookies, or data from `data/`. Start from `config.example.yaml` and `/.env.example`, then keep real secrets in local-only config. For deployment environments where WeChat blocks datacenter IPs, prefer the compose `singbox` sidecar and a single `PROXY_URL=` entry in `/.env` instead of modifying host proxy settings or duplicating proxy fields across files. Review `SECURITY.md` before changing auth, webhooks, or access-key flows.

## Project context from CLAUDE.md

# We-MP-RSS Claude Adapter

Conditional task routes (read only for the affected surface; reuse already-loaded owners):

- [AGENTS.md](<../../AGENTS.md>)
- [vibe/rules/README.md](<README.md>)
- [vibe/rules/documentation.md](<documentation.md>) for Standard/Controlled, DB/data, deploy-gated, business-changing, or documentation-heavy work
- [vibe/specs/PROJECT_STATUS.md](<../specs/PROJECT_STATUS.md>) for current or overlapping work
- [vibe/ai-db/README.md](<../ai-db/README.md>) before database or SQL work

This file is a discovery router, not a second rule owner. Preserve unrelated changes; never store credentials or execute database mutations.

## Project context from vibe/rules/README.md

# We-MP-RSS AI Rules

## Initialization

- This file is the project entry. Links below are task routes, not an initialization preload list.
- Start with the smallest applicable owner and add another only for a distinct task signal or global guard.

## Task Routes

- Project constraints: [project.md](<project.md>), for source, configuration, business behavior, security or project-risk work.
- Commands and verification: [workflow.md](<workflow.md>), before running project commands or selecting checks.
- Knowledge routing: [knowledge.md](<knowledge.md>), for reusable project facts, ADRs, technical knowledge or memory synchronization.
- Documentation routing: [documentation.md](<documentation.md>), for Standard/Controlled, documentation-governance, DB/data, cross-repository or deploy-gated work.
- Current process: [PROJECT_STATUS.md](<../specs/PROJECT_STATUS.md>), for ongoing/overlapping work and active gates.
- Product requirement authority: [Controlled Spec](<../../docs/tasks/260824-wechat-intelligence-hub/spec.md>).
- Database/data work: [AI-DB workspace](<../ai-db/README.md>); load its project rules plus the linked global governance before authoring SQL or changing schema/data contracts.
- Matching error memory: [project error-memory index](<../knowledge/error-memory/README.md>), only when a current symptom or failed route matches.
- Error capture: [error-memory-capture](<../../../CzzProj/CodeNote/AiRef/VibePractice/Skills/global/error-memory-capture/SKILL.md>), only after a verified reusable failure, user correction, DB/dataFix incident or tool/runtime trap; update the project error-memory route in the same closeout.

## Ownership Boundary

- CodeNote owns reusable cross-project collaboration and DB-safety rules.
- This repository owns its stack, commands, paths, business constraints, current requirements and database facts.
- `docs/tasks/260824-wechat-intelligence-hub/spec.md` remains the canonical product Spec; do not create a parallel `vibe/requirements/` tree.
- `vibe/ai-db/` is documentation and stable database memory. It is not a database, connection profile, migration runner or mutation authorization.

## Closeout

- Verification performed or skipped with reason.
- Any unrun runtime, browser, provider, DB, deployment or user-feel acceptance gate.
