# 微信公众号智能聚合系统验证记录

Tool: Codex App
Date: 2026-08-24
Task: wechat-intelligence-hub

Documentation level: `controlled`

## Verification Decision

- Route: `focused-automated`
- Reason: backend persistence/auth/concurrency and frontend routing are material but bounded to new v2 surfaces.
- Impact source and freshness: current `f54aba5` source plus task diff.
- Command provenance/reconciliation: dynamic impact trace; no full-suite escalation.
- Affected modules / boundaries: SQLAlchemy metadata/dialects, storage profiles, Redis/MQTT coordination,
  new services/router, FastAPI registration, Vue layout/floating drawer and docs.
- Checked: 39 backend tests, task-scoped Python compilation, three SQL dialect DDL renders, Compose parsing,
  frontend production build, generated-asset integrity, source whitespace and sensitive-pattern checks.
- Skipped: live WeChat, paid API, AI CLI, Redis/MQTT connections, SMTP/Webhooks, browser acceptance, user or
  production database mutation, SupSub installation/login/protected calls, deployment and push.
- Full-suite escalation: `none`.
- Owner: App Root.
- Residual risk: external provider behavior remains user-owned runtime acceptance.

## Verification Impact Trace

| Changed surface / claim | Direct consumers | Material boundary | Selected evidence | Skipped suites / reason | Outcome |
| --- | --- | --- | --- | --- | --- |
| SQLite tenant models | v2 services/API | ACL and job integrity | disposable SQLite model/service tests | user DB excluded | pass |
| PostgreSQL/Redis/MQTT profiles | API/workers/collectors | leases, replay and graceful degradation | dialect compile plus fake broker contracts | real connections excluded | pass (static/contract) |
| collection state machine | scheduler/collector adapters | retry/cursor safety | fake collector unit tests | live WeChat excluded | pass |
| AI/feedback/digests | v2 API/UI | untrusted CLI output | deterministic and fake CLI tests | real CLIs excluded | pass |
| Vue inbox/floating panels | browser bundle | routing/accessibility | production build and focused source/asset assertions | subjective visual acceptance | pass (build/static) |
| migration inspector | admin handoff | legacy DB mapping | read-only fixture and offline DDL | actual migration gated | pass (offline) |
| SupSub requirement revision | connector registry and future adapters | price/auth/quota/mutation drift | official page, public price response and official CLI source/docs | account canary and protected interfaces excluded | pass (research) |

## Evidence Receipts

- `.venv/bin/python -m unittest discover -s core/intelligence -t . -p 'test_*.py' -v`:
  39 tests passed in 0.425 seconds.
- `.venv/bin/python -m compileall -q ...`: all task-owned Python paths compiled.
- `tools/intelligence_schema.py ddl`: SQLite, PostgreSQL and MySQL each rendered 460 lines without connecting
  to a database.
- `docker compose ... config --no-env-resolution --quiet`: Distributed profile parsed successfully with a
  validation-only password.
- `npm run build`: Vite 8 transformed 5,614 modules and produced the production bundle.
- `diff -qr web_ui/dist/assets static/assets`: exact asset-tree match; all 14 `/assets/` references from
  `static/index.html` resolve.
- Source-only `git diff --check` and staged secret-pattern scans passed. Generated Monaco/Vite bundles contain
  upstream line-ending whitespace, so they are accepted by build plus byte-for-byte asset verification instead
  of rewriting minified strings.

## SupSub Research Receipt

- Public pricing snapshot: monthly ¥29, yearly ¥299 with ¥348 original-year field, 200 subscriptions and 10 focus
  points; price is dated and not used as runtime configuration.
- Official CLI snapshot: Git commit `84744549dfc35e8d829e0c7a4c144b51cf2b8659`, npm `0.4.3`, MIT.
- Official CLI contracts confirm JSON output, OAuth Device Flow without an API-key bypass, quota-consuming deepread,
  no raw-article endpoint, whole-source irreversible read actions and public/non-revocable deepread shares.
- The pricing endpoint's observed rate-limit header was explicitly rejected as evidence for a general content API
  quota. Marketing efficiency/source-count claims were also excluded from acceptance evidence.
- Documentation closeout resolved 15 local links, parsed all 4 documentation-sync members and 2 validators, and
  received HTTP 200 from 7 selected SupSub product, price, repository and CLI documentation URLs.

## Verified Failure And Recovery

- `sqlite://` API-fixture initialization initially entered the service-database pool branch because SQLite detection only matched file URLs.
- `core/db.py` now classifies the complete SQLite scheme family for engine options and PRAGMAs while retaining the narrower file-creation check.
- Durable prevention record: [SQLite URL pool routing](../../knowledge/error-memory/sqlite-memory-pool-routing.md).

## Pre-existing Verification Boundary

- Repository-wide `compileall` still encounters the pre-existing unterminated string in `tools/fix_db.py`; the file is unchanged by this task.
- Acceptance compiles every task-owned Python file explicitly and keeps repair of the unrelated legacy utility out of scope.

## Gaps

- Real provider quotas, current official-account permissions and paid supplier prices require deployment-time
  verification; no static test can establish those external contracts.
- PostgreSQL migration, Redis/MQTT connectivity, browser interaction, notification delivery and deployment remain
  explicit acceptance gates.
- `npm ci` reported 10 existing dependency audit findings (3 moderate, 7 high). The build also retains upstream
  large-chunk, direct-`eval` and ineffective-dynamic-import warnings; no broad dependency upgrade was attempted.
- SupSub Feed URL/authentication, OPML conflict semantics, protected-interface quotas/SLA, deepread allowance,
  service/privacy terms and stable field fixtures remain unverified; its runtime state is therefore `researched`.

## Memory Decision

- No relevant historical memory was used and no user/system memory was written. The verified SQLite URL routing
  failure was captured in the repository error-memory path required by the error-memory workflow.

## Rule Declaration

- Global entry: CodeNote Rule Kernel loaded after project switch.
- Project entry: repository `AGENTS.md`.
- Sidecar: main-only, not applicable.
- Document routing: Controlled task folder plus project-current documentation.
- High-risk gate: live calls, credentials, SupSub installation/OAuth/purchase/mutations/quota use, user DB mutation,
  deployment and push remain blocked.
