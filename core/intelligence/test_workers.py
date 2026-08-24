from __future__ import annotations

import unittest
from datetime import date, datetime
import json

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from core.models.article import Article
from core.models.base import Base
from core.models.feed import Feed

from .collector import CollectedPage, CollectionWorker, CollectorError
from .events import EventEnvelope, RedisCoordinator
from .jobs import JobRepository
from .models import (
    CollectionJob,
    CollectorAccount,
    CollectorCursor,
    OutboxEvent,
    RateLimitLedger,
    Workspace,
    WorkspaceArticle,
    WorkspaceMembership,
    WorkspaceSubscription,
    Digest,
    WorkflowJob,
    utcnow,
)
from .outbox import OutboxDispatcher, OutboxRepository
from .providers import PaidJsonApiCollectorAdapter, WeMpRssCollectorAdapter
from .rate_limit import RateLimitRepository, RateSignal, RateState
from .scheduling import DEFAULT_SCHEDULE
from .workflow import DailyAutomationScheduler, WorkflowJobRepository, WorkflowWorker


class FakeCollector:
    def fetch_page(self, *, source_id: str, cursor: dict, page_budget: int) -> CollectedPage:
        if page_budget != 1:
            raise AssertionError("worker must request one page")
        return CollectedPage(
            articles=(
                {
                    "id": "collected-1",
                    "mp_id": source_id,
                    "title": "Collected",
                    "publish_time": 1_777_000_000,
                    "status": 1,
                },
            ),
            next_cursor={"offset": int(cursor.get("offset", 0)) + 1},
            ingestion_source="fake",
        )


class LimitedCollector:
    def fetch_page(self, **kwargs) -> CollectedPage:
        raise CollectorError("200013", safe_message="provider rate limited")


class InvalidAuthCollector:
    def fetch_page(self, **kwargs) -> CollectedPage:
        raise CollectorError("200003", safe_message="provider authorization expired")


class RecordingPublisher:
    def __init__(self):
        self.events: list[EventEnvelope] = []

    def publish(self, event: EventEnvelope) -> None:
        self.events.append(event)


class UnavailableCoordinator:
    redis_url = "redis://unavailable.invalid:6379/0"

    def consume_budget(self, *args, **kwargs):
        return None


class FakeResponse:
    def __init__(self, payload: dict, status_code: int = 200, headers: dict | None = None):
        self.payload = payload
        self.status_code = status_code
        self.headers = headers or {}
        self.content = json.dumps(payload).encode()

    def json(self) -> dict:
        return self.payload


class FakeHttp:
    def __init__(self, response: FakeResponse):
        self.response = response
        self.calls: list[dict] = []

    def get(self, url: str, **kwargs):
        self.calls.append({"url": url, **kwargs})
        return self.response


class WorkerInfrastructureTest(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite://")
        tables = [
            table
            for name, table in Base.metadata.tables.items()
            if name == "articles" or name.startswith("int_")
        ]
        Base.metadata.create_all(self.engine, tables=tables)
        self.session_factory = sessionmaker(bind=self.engine, expire_on_commit=False)
        with self.session_factory() as session:
            session.add(Workspace(id="workspace", name="W", slug="w", owner_user_id="user"))
            session.add(
                CollectorAccount(
                    id="account",
                    workspace_id="workspace",
                    provider="fake",
                    label="test",
                )
            )
            session.commit()

    def tearDown(self) -> None:
        self.engine.dispose()

    def test_collection_worker_persists_before_cursor_and_emits_outbox(self) -> None:
        jobs = JobRepository(self.session_factory)
        rates = RateLimitRepository(self.session_factory)
        job, created = jobs.enqueue(
            workspace_id="workspace",
            provider="fake",
            source_id="source",
            account_id="account",
            idempotency_key="collect:one",
        )
        self.assertTrue(created)
        worker = CollectionWorker(
            session_factory=self.session_factory,
            jobs=jobs,
            rate_limits=rates,
            adapters={"fake": FakeCollector()},
        )
        self.assertEqual(worker.run_once(), "completed")
        with self.session_factory() as session:
            self.assertIsNotNone(session.get(Article, "collected-1"))
            stored_job = session.get(CollectionJob, job.id)
            self.assertEqual(stored_job.state, "completed")
            cursor = session.scalar(select(CollectorCursor))
            self.assertEqual(cursor.cursor, {"offset": 1})
            link = session.scalar(select(WorkspaceArticle))
            self.assertEqual(link.article_id, "collected-1")
            event = session.scalar(select(OutboxEvent))
            self.assertEqual(event.event_type, "collection.page.persisted")
            analysis_job = session.scalar(
                select(WorkflowJob).where(WorkflowJob.kind == "article_analysis")
            )
            self.assertEqual(analysis_job.payload, {"article_id": "collected-1"})

    def test_shared_source_collection_fans_out_without_duplicate_provider_calls(self) -> None:
        with self.session_factory() as session:
            session.add(Workspace(id="workspace-2", name="W2", slug="w2", owner_user_id="user-2"))
            session.add_all(
                [
                    WorkspaceSubscription(
                        workspace_id="workspace",
                        source_id="source",
                        provider="fake",
                    ),
                    WorkspaceSubscription(
                        workspace_id="workspace-2",
                        source_id="source",
                        provider="fake",
                    ),
                ]
            )
            session.commit()
        jobs = JobRepository(self.session_factory)
        job, _ = jobs.enqueue(
            workspace_id="workspace",
            provider="fake",
            source_id="source",
            account_id="account",
            idempotency_key="collect:shared-source",
        )
        worker = CollectionWorker(
            session_factory=self.session_factory,
            jobs=jobs,
            rate_limits=RateLimitRepository(self.session_factory),
            adapters={"fake": FakeCollector()},
        )
        self.assertEqual(worker.run_once(), "completed")
        with self.session_factory() as session:
            links = session.scalars(
                select(WorkspaceArticle).where(WorkspaceArticle.article_id == "collected-1")
            ).all()
            analysis_jobs = session.scalars(
                select(WorkflowJob).where(WorkflowJob.kind == "article_analysis")
            ).all()
            self.assertEqual({link.workspace_id for link in links}, {"workspace", "workspace-2"})
            self.assertEqual({item.workspace_id for item in analysis_jobs}, {"workspace", "workspace-2"})
            self.assertEqual(session.get(CollectionJob, job.id).state, "completed")

    def test_provider_rate_limit_is_durable_and_retried(self) -> None:
        jobs = JobRepository(self.session_factory)
        rates = RateLimitRepository(self.session_factory)
        job, _ = jobs.enqueue(
            workspace_id="workspace",
            provider="fake",
            source_id="source",
            account_id="account",
            idempotency_key="collect:limited",
        )
        worker = CollectionWorker(
            session_factory=self.session_factory,
            jobs=jobs,
            rate_limits=rates,
            adapters={"fake": LimitedCollector()},
        )
        self.assertEqual(worker.run_once(), "retry")
        with self.session_factory() as session:
            stored_job = session.get(CollectionJob, job.id)
            self.assertEqual(stored_job.state, "retry")
            self.assertEqual(stored_job.last_error_code, "200013")
            ledger = session.scalar(select(RateLimitLedger))
            self.assertEqual(ledger.state, RateState.COOLDOWN.value)
            self.assertEqual(ledger.last_signal, RateSignal.RATE_LIMITED.value)

    def test_provider_auth_failure_disables_the_real_collector_account(self) -> None:
        jobs = JobRepository(self.session_factory)
        rates = RateLimitRepository(self.session_factory)
        job, _ = jobs.enqueue(
            workspace_id="workspace",
            provider="fake",
            source_id="source",
            account_id="account",
            idempotency_key="collect:invalid-auth",
        )
        worker = CollectionWorker(
            session_factory=self.session_factory,
            jobs=jobs,
            rate_limits=rates,
            adapters={"fake": InvalidAuthCollector()},
        )
        self.assertEqual(worker.run_once(), "account_disabled")
        with self.session_factory() as session:
            self.assertEqual(session.get(CollectionJob, job.id).state, "failed")
            account = session.get(CollectorAccount, "account")
            self.assertEqual(account.status, "disabled")
            self.assertEqual(account.last_error_code, "200003")
            ledger = session.scalar(select(RateLimitLedger))
            self.assertEqual(ledger.state, RateState.DISABLED.value)

    def test_outbox_claim_is_leased_and_dispatch_is_idempotent(self) -> None:
        repository = OutboxRepository(self.session_factory)
        event, created = repository.enqueue(
            event_type="digest.published",
            aggregate_type="digest",
            aggregate_id="digest-1",
            idempotency_key="digest:1",
            workspace_id="workspace",
            payload={"digest_id": "digest-1"},
        )
        duplicate, duplicate_created = repository.enqueue(
            event_type="digest.published",
            aggregate_type="digest",
            aggregate_id="digest-1",
            idempotency_key="digest:1",
        )
        self.assertTrue(created)
        self.assertFalse(duplicate_created)
        self.assertEqual(event.id, duplicate.id)

        publisher = RecordingPublisher()
        dispatcher = OutboxDispatcher(repository, publisher)
        self.assertTrue(dispatcher.dispatch_once())
        self.assertFalse(dispatcher.dispatch_once())
        self.assertEqual([item.event_id for item in publisher.events], [event.id])
        with self.session_factory() as session:
            self.assertEqual(session.get(OutboxEvent, event.id).state, "delivered")

    def test_outbox_long_idempotency_keys_are_stable_without_prefix_collision(self) -> None:
        repository = OutboxRepository(self.session_factory)
        shared_prefix = "x" * 200
        first, first_created = repository.enqueue(
            event_type="test.created",
            aggregate_type="test",
            aggregate_id="one",
            idempotency_key=f"{shared_prefix}:one",
        )
        duplicate, duplicate_created = repository.enqueue(
            event_type="test.created",
            aggregate_type="test",
            aggregate_id="one",
            idempotency_key=f"{shared_prefix}:one",
        )
        second, second_created = repository.enqueue(
            event_type="test.created",
            aggregate_type="test",
            aggregate_id="two",
            idempotency_key=f"{shared_prefix}:two",
        )
        self.assertTrue(first_created)
        self.assertFalse(duplicate_created)
        self.assertTrue(second_created)
        self.assertEqual(first.id, duplicate.id)
        self.assertNotEqual(first.id, second.id)
        self.assertLessEqual(len(first.idempotency_key), 160)

    def test_corrupt_rate_state_fails_closed_and_can_recover(self) -> None:
        with self.session_factory() as session:
            session.add(
                RateLimitLedger(
                    provider="fake",
                    account_id="corrupt",
                    state="unexpected-state",
                    failure_count=3,
                )
            )
            session.commit()
        repository = RateLimitRepository(self.session_factory)
        self.assertEqual(repository.snapshot("fake", "corrupt").state, RateState.COOLDOWN)
        recovered = repository.apply_signal("fake", "corrupt", RateSignal.SUCCESS)
        self.assertEqual(recovered.state, RateState.HEALTHY)

    def test_configured_redis_outage_fails_closed_for_collection_budget(self) -> None:
        repository = RateLimitRepository(self.session_factory, UnavailableCoordinator())
        allowed, snapshot = repository.allow_request("fake", "account")
        self.assertFalse(allowed)
        self.assertEqual(snapshot.state, RateState.HEALTHY)

    def test_job_repositories_normalize_long_idempotency_keys(self) -> None:
        shared_prefix = "job" * 100
        jobs = JobRepository(self.session_factory)
        first, first_created = jobs.enqueue(
            workspace_id="workspace",
            provider="fake",
            source_id="source",
            account_id="account",
            idempotency_key=f"{shared_prefix}:one",
        )
        duplicate, duplicate_created = jobs.enqueue(
            workspace_id="workspace",
            provider="fake",
            source_id="source",
            account_id="account",
            idempotency_key=f"{shared_prefix}:one",
        )
        self.assertTrue(first_created)
        self.assertFalse(duplicate_created)
        self.assertEqual(first.id, duplicate.id)
        self.assertLessEqual(len(first.idempotency_key), 160)

        workflows = WorkflowJobRepository(self.session_factory)
        workflow, created = workflows.enqueue(
            workspace_id="workspace",
            user_id="user",
            kind="preference_refresh",
            payload={},
            idempotency_key=f"{shared_prefix}:workflow",
            due_at=utcnow(),
        )
        self.assertTrue(created)
        self.assertLessEqual(len(workflow.idempotency_key), 180)

    def test_redis_is_optional_and_never_the_durable_fallback(self) -> None:
        coordinator = RedisCoordinator("")
        self.assertFalse(coordinator.health())
        self.assertIsNone(
            coordinator.consume_budget("fake:account", capacity=2, refill_per_second=0.5)
        )
        rates = RateLimitRepository(self.session_factory, coordinator)
        allowed, snapshot = rates.allow_request("fake", "account")
        self.assertTrue(allowed)
        self.assertEqual(snapshot.state, RateState.HEALTHY)

    def test_daily_scheduler_and_workflow_jobs_are_durable_and_idempotent(self) -> None:
        run_date = date(2026, 8, 24)
        with self.session_factory() as session:
            session.add(
                WorkspaceMembership(workspace_id="workspace", user_id="user", role="owner")
            )
            session.add(
                WorkspaceSubscription(
                    workspace_id="workspace",
                    source_id="source",
                    provider="fake",
                )
            )
            article = Article(
                id="digest-source",
                mp_id="source",
                title="Daily",
                publish_time=int(DEFAULT_SCHEDULE.moments(run_date)["collect"].timestamp()),
                status=1,
            )
            session.add(article)
            session.flush()
            session.add(
                WorkspaceArticle(
                    workspace_id="workspace",
                    article_id=article.id,
                    source_id="source",
                )
            )
            session.commit()

        collection_repository = JobRepository(self.session_factory)
        workflow_repository = WorkflowJobRepository(self.session_factory)
        scheduler = DailyAutomationScheduler(
            session_factory=self.session_factory,
            collection_jobs=collection_repository,
            workflow_jobs=workflow_repository,
        )
        first = scheduler.schedule_day(run_date)
        second = scheduler.schedule_day(run_date)
        self.assertEqual(
            first,
            {"collection_jobs": 1, "digest_jobs": 1, "preference_jobs": 1},
        )
        self.assertEqual(
            second,
            {"collection_jobs": 0, "digest_jobs": 0, "preference_jobs": 0},
        )

        worker = WorkflowWorker(
            session_factory=self.session_factory,
            repository=workflow_repository,
        )
        self.assertEqual(worker.run_once(now=datetime(2026, 8, 24, 0, 5)), "completed")
        with self.session_factory() as session:
            digest = session.scalar(select(Digest))
            self.assertIsNotNone(digest)
            digest_job = session.scalar(
                select(WorkflowJob).where(WorkflowJob.kind == "daily_digest")
            )
            self.assertEqual(digest_job.state, "completed")

    def test_daily_scheduler_materializes_one_collection_per_shared_source(self) -> None:
        with self.session_factory() as session:
            session.add(Workspace(id="workspace-2", name="W2", slug="w2", owner_user_id="user-2"))
            session.add(
                CollectorAccount(
                    id="shared-account",
                    workspace_id=None,
                    provider="shared",
                    label="shared credential",
                )
            )
            session.add_all(
                [
                    WorkspaceSubscription(
                        workspace_id="workspace",
                        source_id="same-source",
                        provider="shared",
                    ),
                    WorkspaceSubscription(
                        workspace_id="workspace-2",
                        source_id="same-source",
                        provider="shared",
                    ),
                ]
            )
            session.commit()
        scheduler = DailyAutomationScheduler(
            session_factory=self.session_factory,
            collection_jobs=JobRepository(self.session_factory),
            workflow_jobs=WorkflowJobRepository(self.session_factory),
        )
        first = scheduler.schedule_day(date(2026, 8, 25))
        second = scheduler.schedule_day(date(2026, 8, 25))
        self.assertEqual(first["collection_jobs"], 1)
        self.assertEqual(second["collection_jobs"], 0)


class ProviderAdapterTest(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite://")
        Base.metadata.create_all(self.engine, tables=[Feed.__table__])
        self.session_factory = sessionmaker(bind=self.engine, expire_on_commit=False)
        with self.session_factory() as session:
            session.add(Feed(id="source", faker_id="fake-id", mp_name="Source", status=1))
            session.commit()

    def tearDown(self) -> None:
        self.engine.dispose()

    def test_we_mp_rss_adapter_performs_exactly_one_request_without_retry(self) -> None:
        payload = {
            "base_resp": {"ret": 0},
            "publish_page": json.dumps(
                {
                    "publish_list": [
                        {
                            "publish_info": json.dumps(
                                {
                                    "appmsgex": [
                                        {
                                            "aid": "aid-1",
                                            "title": "Title",
                                            "link": "https://example.test/article",
                                            "update_time": 1_777_000_000,
                                        }
                                    ]
                                }
                            )
                        }
                    ]
                }
            ),
        }
        http = FakeHttp(FakeResponse(payload))
        adapter = WeMpRssCollectorAdapter(
            session_factory=self.session_factory,
            token_getter=lambda key, default="": {"token": "token", "cookie": "cookie"}.get(key, default),
            http=http,
        )
        page = adapter.fetch_page(source_id="source", cursor={}, page_budget=1)
        self.assertEqual(len(http.calls), 1)
        self.assertFalse(http.calls[0]["allow_redirects"])
        self.assertEqual(http.calls[0]["params"]["begin"], 0)
        self.assertEqual(page.articles[0]["id"], "source-aid-1")
        self.assertEqual(page.next_cursor, {"page": 1, "exhausted": False})

    def test_we_mp_rss_rate_code_is_propagated_without_internal_sleep(self) -> None:
        http = FakeHttp(FakeResponse({"base_resp": {"ret": 200013}}))
        adapter = WeMpRssCollectorAdapter(
            session_factory=self.session_factory,
            token_getter=lambda key, default="": "configured",
            http=http,
        )
        with self.assertRaises(CollectorError) as raised:
            adapter.fetch_page(source_id="source", cursor={}, page_budget=1)
        self.assertEqual(raised.exception.code, "200013")
        self.assertEqual(len(http.calls), 1)

    def test_paid_api_requires_https_allowlist_and_uses_bounded_contract(self) -> None:
        with self.assertRaises(ValueError):
            PaidJsonApiCollectorAdapter(
                endpoint="https://untrusted.test/feed",
                allowed_hosts={"api.vendor.test"},
                api_key_getter=lambda: "key",
            )
        http = FakeHttp(
            FakeResponse(
                {
                    "articles": [{"id": "paid-1", "title": "Paid"}],
                    "next_cursor": {"page": 2},
                }
            )
        )
        adapter = PaidJsonApiCollectorAdapter(
            endpoint="https://api.vendor.test/v1/articles",
            allowed_hosts={"api.vendor.test"},
            api_key_getter=lambda: "secret-key",
            http=http,
        )
        page = adapter.fetch_page(source_id="source", cursor={"page": 1}, page_budget=1)
        self.assertEqual(page.articles[0]["mp_id"], "source")
        self.assertEqual(page.next_cursor, {"page": 2})
        self.assertEqual(http.calls[0]["headers"]["Authorization"], "Bearer secret-key")


if __name__ == "__main__":
    unittest.main()
