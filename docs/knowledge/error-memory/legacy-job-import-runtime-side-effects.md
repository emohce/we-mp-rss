---
id: we-mp-rss-legacy-job-import-runtime-side-effects
status: verified
scope: isolated tests of legacy article repair functions
fingerprint: legacy-jobs-package-import-starts-redis-queues-before-test-isolation
first_seen: 2026-08-30
last_verified: 2026-08-30
review_after: 2027-02-28
evidence:
  - ../../../jobs/__init__.py
  - ../../../core/redis_client.py
  - ../../../core/queue/queue.py
  - ../../../core/intelligence/test_api.py
  - ../../../tools/test_intelligence_offline.py
  - ../../tasks/260824-wechat-intelligence-hub/verify.md
tags:
  - test-isolation
  - python-import
  - redis
  - legacy-queue
---

# Legacy job import starts runtime services

## Symptom and wrong assumption

A test importing a repair function also connected to Redis and started two in-process queue threads.
Using an in-memory SQL database and mocking an HTTP helper did not isolate other infrastructure imports.
The affected run passed its assertions but is not valid evidence of a fully offline execution.

## Verified root cause and scope

- `jobs.__init__` imports `jobs.mps`, pulling in legacy runtime dependencies before the requested function.
- `core.redis_client` constructs its singleton and pings Redis at module import.
- `core.queue.queue` starts both global queue threads at import; each startup calls a Redis status writer.
  The in-memory queues start empty and do not load Redis tasks for execution. Source inspection found no
  startup task consumption, but it does not prove the absence of server-side state changes.
- The affected process exited. No matching test process remained in the subsequent process inspection.
  Actual Redis key changes were not inspected or restored; they remain an explicit external verification gate.

Source owners: [package initializer](../../../jobs/__init__.py#L1),
[Redis initialization](../../../core/redis_client.py#L1),
[queue startup and persistence](../../../core/queue/queue.py#L1).

## Detection order and prevention

1. Inspect the entire package initializer chain before importing a legacy job in a test.
2. Install a process-level socket/process/DB audit guard before test discovery, not after an application import.
3. For bounded source-function contracts, compile only the selected AST function with explicit safe dependencies.
4. Fail the overall run if a library swallows a denied I/O operation or an unexpected runtime module is imported.
5. Do not broaden a contract test into Redis inspection, cleanup or runtime startup without separate authority.

## Alternative Route

- Status: `verified`.
- Preconditions: a local source-function contract needs no module initialization; no real-service acceptance intended.
- Steps: use the [offline runner](../../../tools/test_intelligence_offline.py#L1); disable urllib3's optional
  IPv6 bind probe while retaining the socket deny guard; discover the focused suite; the
  [legacy guard test](../../../core/intelligence/test_api.py#L328) compiles only the two selected functions.
- Verification: 91 focused tests pass; zero blocked I/O attempts and zero legacy runtime module imports.
- Applicability boundary: source-function and isolated API/model contracts only, not full legacy module startup,
  PostgreSQL, Redis, MQTT, provider or browser acceptance.
- Fallback: if the function requires runtime globals, extract a pure boundary in a separately reviewed change;
  do not import the service package or relax the I/O guard to make the test pass.

## Occurrence History

| Date | Task | Trigger | Failed route | Recovery | Outcome |
| --- | --- | --- | --- | --- | --- |
| 2026-08-30 | WU-16 | offline file records must avoid legacy repair | direct legacy package import | source-function test plus pre-import audit guard | test isolation verified; earlier Redis impact unverified |

Incident authority: [Controlled verification](../../tasks/260824-wechat-intelligence-hub/verify.md#v3-test-isolation-incident).
