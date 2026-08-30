# 微信公众号智能聚合系统验证记录

Tool: Codex App
Date: 2026-08-24
Updated: 2026-08-25
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
  frontend production build, generated-asset integrity, source whitespace and sensitive-pattern checks; the
  2026-08-25 docs-only deltas add donor/current Git, local-link, source-presence, statement consistency, CodeNote
  project/catalog resolution and populated AI-DB structure checks.
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
| legacy requirement/research migration | core docs and future backlog | false completion claims, license crossing and stale behavior | donor/current Git snapshot, focused source search, migration matrix, local links and diff | runtime/data migration excluded | pass (docs/static) |
| CodeNote + AI-DB initialization | agents, future DB tasks and CodeNote resolver | stale links, duplicate authority, leaked secrets or implied mutation permission | project audit, resolver, catalog tests, 15-file structure, JSON/link/diff/secret checks | live DB/runtime excluded | pass (rules/docs/static) |

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

## Legacy Documentation Migration Receipt

- Old `wechat-download-api/czz-main@3e85bab` is three documentation-only commits ahead of
  `origin/main@043c2f9`; its application README is unchanged from that baseline.
- Current core source confirms existing RSS/Atom/JSON/Markdown Feed, authorization notifications, proxy paths,
  v2 single-article downloads and asynchronous MD/DOCX/JSON/CSV/PDF batch export.
- No current FastMCP, `/mcp`, `ENABLE_MCP` or `MCP_TOKEN` source/config entry was found outside task/research docs;
  the Spec was corrected from implied v1 availability to `planned`.
- Existing batch export has page/selection scope but no reconciled date/window/incremental, HTML/EPUB or verified
  default no-upstream-call contract, so it remains `partial-current`.
- The documentation index, migration matrix, raw requirement, Spec, plan, ledger, verification, handoff, changes,
  architecture guide, research document and both tracked root README entry points are in the synchronized sweep.
- Validation covered 13 changed Markdown files and 56 repository-local links; all 6 documentation-sync members and
  2 declared validators parsed, 7/7 focused source contracts were present, current MCP runtime hits were 0, and
  `git diff --check` plus the scoped sensitive-pattern scan passed.

## CodeNote And AI-DB Initialization Receipt

- The core initially had only upstream `AGENTS.md`; `CLAUDE.md`, `vibe/rules`, `vibe/specs`, `vibe/knowledge` and
  `vibe/ai-db` were absent. The upstream repository guidance was retained below a compact CodeNote router.
- CodeNote project audit passes in working view before and after its conservative `--fix-links` replay.
- The CodeNote workspace resolver returns `we-mp-rss` for both project-ID and exact local-path lookup, including the
  expected entry/rules/requirement/status routes and opaque local instance ID.
- The HEAD catalog already contained 40 projects while its count assertion still expected 39. Registering
  `we-mp-rss` produced 41; the test now uses the verified current count, adds exact alias/repository assertions and
  passes 14/14. This closes the local assertion drift without changing any pre-existing project identity.
- JSON parsing passes for the tracked project index and local-only workspace binding. The AI-DB shape check confirms
  all 15 required workspace/memory files are present and non-empty.
- Full-project `--all-markdown` adds no task-owned finding; it still reports 16 pre-existing diagnostics in untouched
  files: five broken links in two older Web UI guides and eleven repeated headings in `TROUBLESHOOTING_CASCADE.md`.
- The correctly rooted CodeNote master audit reports no finding against either task-owned error-memory record. It
  retains the ten HEAD baseline diagnostics plus one dirty-worktree `rule-state` drift caused by an unrelated
  pre-existing untracked Skill. A generator run briefly projected that foreign Skill; the generated hunk was
  inspected, discarded and the manifest restored to its exact pre-task content.
- Scoped `git diff --check`, sensitive-pattern and task-path checks are required at final staging. The unrelated
  concurrent `tools/fix_db.py` change is not owned, modified, staged or accepted by WU-9.
- No application process, SQLite/PostgreSQL connection, Redis, MQTT, provider, migration, DDL, DML, credential,
  deployment or push action ran. AI-DB evidence is `code + document + prior disposable tests`, never live DB proof.

## Verification Route Recoveries

- A `python -m unittest` filesystem-path invocation failed before collection with `ValueError: Empty module name`.
  Direct trusted-file execution collected the real suite and ultimately passed 14/14; the existing global
  `python-unittest-absolute-file-path-module-resolution` occurrence was updated.
- A zsh scalar file list was evaluated as one composite path rather than 15 items. An explicit array and
  `"${array[@]}"` replay passed 15/15; the verified `zsh-scalar-file-list-not-word-split` record was added to the
  CodeNote Git/Shell module.
- A CodeNote master audit was once pointed at the repository root rather than its `Vibe_Rules` master root. Its large
  missing-file output was discarded; the correctly rooted replay was used, with the unrelated dirty-worktree
  manifest drift classified separately from task-owned error-memory validation.

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
- MCP implementation, tenant-scoped Feed/cursor behavior, batch-export date/incremental scope, HTML/EPUB formats and
  remote-image/no-hidden-provider-call runtime tests remain explicit product gaps.

## Memory Decision

- Existing task memory was used only to recover the 2026-08-24 collection/SupSub research boundary and was
  rechecked against current local Git and documents. Project database memory is now initialized under `vibe/ai-db/`.
  The earlier SQLite URL routing record remains authoritative; two shell/test-runner recoveries were routed through
  CodeNote error memory. No credential, raw transcript, command output, database row or global Codex memory was written.

## Rule Declaration

- Global entry: CodeNote Rule Kernel loaded after project switch.
- Project entry: repository `AGENTS.md`.
- Sidecar: main-only, not applicable.
- Document routing: Controlled task folder plus project-current documentation, CodeNote project routes and AI-DB memory.
- Documentation impact: requirement-canonical plus project-current; index, migration, research and all Controlled
  owners synchronized in one round.
- High-risk gate: live calls, credentials, SupSub installation/OAuth/purchase/mutations/quota use, user DB mutation,
  deployment and push remain blocked.
- Evolution Candidate: none; the two verified tool traps used existing error-memory governance and did not change
  application behavior, SQL policy, Hook/runtime configuration or product requirements beyond RAW-005.

## v3 Remediation Evidence (2026-08-30)

- Baseline: `czz-main@d44a41e`, two pre-existing verify/changes hunks preserved and excluded from new commits.
- WU-10: seven-batch plan, explicit RAW-006 authority, exact file manifest and source-derived impact trace added;
  scoped code-link audit and diff whitespace check passed. No application check was needed for this docs batch.
- WU-11..16: pending; historical 39-test evidence does not validate freshness, daily coverage or ranking parity.
- Automatic global router reports an oversized response owner and registry/loading-graph drift. The user permits
  bypassing only that automatic check for this implementation turn; no global rule was changed.
- Verification route: scoped docs plus isolated intelligence package contracts and affected frontend checks.
  Real databases, online migration, provider accounts/spend, runtime services, deployment and push remain unrun.
- Sidecar: main thread; no delegates. Memory route: project current/AI-DB documentation, no global memory write.
