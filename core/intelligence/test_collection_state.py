from datetime import datetime, timedelta
import unittest

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from core.models.base import Base
from core.models.article import Article
from .collection_state import CollectionState, LeaseLost
from .collector import CollectedPage, CollectionWorker
from .jobs import JobRepository
from .models import (CollectionJob, CollectionRun, CollectorAccount, OutboxEvent,
                     RequestBudget, SourceCheckpoint, Workspace, WorkspaceArticle, WorkspaceSubscription)
from .rate_limit import RateLimitRepository


class Pages:
    def __init__(self, pages):
        self.pages = pages
        self.cursors = []

    def fetch_page(self, *, source_id, cursor, page_budget):
        self.cursors.append(dict(cursor))
        index = int(cursor.get("page", 0))
        ids = self.pages[index] if index < len(self.pages) else []
        return CollectedPage(tuple({"id": item, "mp_id": source_id, "title": item} for item in ids),
                             {"page": index + 1, "exhausted": index + 1 >= len(self.pages)}, "fake")


class CollectionStateTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite://")
        Base.metadata.create_all(self.engine, tables=[t for n, t in Base.metadata.tables.items()
                                                    if n == "articles" or n.startswith("int_")])
        self.factory = sessionmaker(self.engine, expire_on_commit=False)
        self.now = datetime(2026, 8, 30, 0, 0)
        with self.factory() as session:
            session.add_all([Workspace(id="w", name="W", slug="w", owner_user_id="u"),
                             CollectorAccount(id="a", workspace_id="w", provider="fake", label="A")])
            session.commit()
        self.jobs = JobRepository(self.factory)

    def tearDown(self):
        self.engine.dispose()

    def enqueue(self, key, *, kind="head", budget=3, now=None):
        return self.jobs.enqueue(workspace_id="w", provider="fake", source_id="s", account_id="a",
                                 idempotency_key=key, kind=kind, payload={"page_budget": budget},
                                 due_at=now or self.now)[0]

    def worker(self, provider):
        return CollectionWorker(session_factory=self.factory, jobs=self.jobs,
                                rate_limits=RateLimitRepository(self.factory), adapters={"fake": provider})

    def test_next_day_starts_at_head_and_stops_on_known_boundary(self):
        provider = Pages([["old-head"], ["old-tail"]])
        first = self.enqueue("day-1")
        worker = self.worker(provider)
        self.assertEqual(worker.run_once(now=self.now), "page_persisted")
        self.assertEqual(worker.run_once(now=self.now + timedelta(seconds=30)), "completed")
        provider.pages = [["new-head"], ["old-head"], ["old-tail"]]
        second = self.enqueue("day-2", now=self.now + timedelta(days=1))
        self.assertEqual(worker.run_once(now=self.now + timedelta(days=1)), "page_persisted")
        self.assertEqual(worker.run_once(now=self.now + timedelta(days=1, seconds=30)), "completed")
        self.assertEqual(provider.cursors, [{}, {"page": 1, "exhausted": False}, {}, {"page": 1, "exhausted": False}])
        with self.factory() as session:
            self.assertEqual(session.get(CollectionJob, second.id).state, "completed")
            self.assertEqual(session.query(CollectionRun).count(), 2)
            self.assertEqual(session.scalar(select(SourceCheckpoint)).head_ids, ["new-head"])
            self.assertEqual(session.query(WorkspaceArticle).count(), 3)

    def test_backfill_and_head_checkpoints_do_not_share_cursor(self):
        provider = Pages([["one"], ["two"], ["three"]])
        worker = self.worker(provider)
        self.enqueue("backfill-1", kind="backfill", budget=1)
        self.assertEqual(worker.run_once(now=self.now), "partial")
        self.enqueue("head", now=self.now + timedelta(minutes=1), budget=1)
        self.assertEqual(worker.run_once(now=self.now + timedelta(minutes=1)), "partial")
        self.enqueue("backfill-2", kind="backfill", now=self.now + timedelta(minutes=2), budget=1)
        self.assertEqual(worker.run_once(now=self.now + timedelta(minutes=2)), "partial")
        self.assertEqual(provider.cursors[1], {})
        self.assertEqual(provider.cursors[2], {"page": 1, "exhausted": False})
        with self.factory() as session:
            self.assertEqual(session.query(SourceCheckpoint).count(), 2)

    def test_truncated_head_run_keeps_previous_complete_boundary(self):
        with self.factory() as session:
            session.add(SourceCheckpoint(account_id="a", source_id="s", mode="head", head_ids=["old"]))
            session.commit()
        self.enqueue("truncated", budget=1)
        self.assertEqual(self.worker(Pages([["new"], ["old"]])).run_once(now=self.now), "partial")
        with self.factory() as session:
            checkpoint = session.scalar(select(SourceCheckpoint))
            self.assertEqual(checkpoint.head_ids, ["old"])
            self.assertIsNone(checkpoint.last_success_at)
            self.assertEqual(session.scalar(select(CollectionRun)).error_code, "page_budget")

    def test_expired_lease_cannot_persist_or_advance_and_new_owner_can(self):
        job = self.enqueue("lease")
        claimed = self.jobs.claim_next(now=self.now, lease_seconds=10)
        state = CollectionState(self.factory)
        attempt = state.begin_page(claimed, self.now)
        page = Pages([["article"]]).fetch_page(source_id="s", cursor={}, page_budget=1)
        with self.assertRaises(LeaseLost):
            state.finish_page(claimed, attempt, page, self.now + timedelta(seconds=11))
        replacement = self.jobs.claim_next(now=self.now + timedelta(seconds=11))
        new_attempt = state.begin_page(replacement, self.now + timedelta(seconds=11))
        with self.assertRaises(LeaseLost):
            state.finish_page(claimed, attempt, page, self.now + timedelta(seconds=12))
        with self.factory() as session:
            self.assertEqual(session.query(Article).count(), 0)
            self.assertEqual(session.query(OutboxEvent).count(), 0)
        self.assertEqual(state.finish_page(replacement, new_attempt, page, self.now + timedelta(seconds=12)), "completed")

    def test_failed_page_rolls_back_articles_links_and_checkpoint(self):
        self.enqueue("bad-page")
        claimed = self.jobs.claim_next(now=self.now)
        state = CollectionState(self.factory)
        attempt = state.begin_page(claimed, self.now)
        page = CollectedPage(({"id": "ok"}, {"id": "bad", "mp_id": "another-source"}), {}, "fake")
        with self.assertRaises(ValueError):
            state.finish_page(claimed, attempt, page, self.now)
        with self.factory() as session:
            self.assertEqual(session.query(Article).count(), 0)
            self.assertEqual(session.scalar(select(SourceCheckpoint)).version, 0)

    def test_private_account_does_not_fan_out_to_other_workspace(self):
        with self.factory() as session:
            session.add(Workspace(id="other", name="Other", slug="other", owner_user_id="other"))
            session.add(WorkspaceSubscription(workspace_id="other", source_id="s", provider="fake"))
            session.commit()
        self.enqueue("private")
        self.assertEqual(self.worker(Pages([["private"]])).run_once(now=self.now), "completed")
        with self.factory() as session:
            self.assertEqual(list(session.scalars(select(WorkspaceArticle.workspace_id))), ["w"])

    def test_local_budget_deferrals_do_not_exhaust_attempts(self):
        rates = RateLimitRepository(self.factory)
        self.assertTrue(rates.allow_request("fake", "a", source_id="s", now=self.now)[0])
        job = self.enqueue("budget")
        provider = Pages([["article"]])
        worker = self.worker(provider)
        for seconds in range(10):
            with self.factory() as session:
                session.get(CollectionJob, job.id).due_at = self.now
                session.commit()
            self.assertEqual(worker.run_once(now=self.now + timedelta(seconds=seconds)), "rate_deferred")
        self.assertEqual(provider.cursors, [])
        with self.factory() as session:
            self.assertEqual(session.get(CollectionJob, job.id).attempts, 0)
        self.assertEqual(worker.run_once(now=self.now + timedelta(seconds=30)), "completed")

    def test_budgets_persist_across_repository_instances_and_layers(self):
        rates = RateLimitRepository(self.factory)
        self.assertTrue(rates.allow_request("fake", "a", source_id="s", now=self.now)[0])
        restarted = RateLimitRepository(self.factory)
        self.assertFalse(restarted.allow_request("fake", "b", source_id="other", now=self.now)[0])
        self.assertTrue(restarted.allow_request("fake", "b", source_id="other", now=self.now + timedelta(seconds=6))[0])
        self.assertFalse(restarted.allow_request("fake", "a", source_id="s", now=self.now + timedelta(seconds=12))[0])
        self.assertFalse(restarted.allow_request("fake", "c", source_id="s", now=self.now + timedelta(seconds=12))[0])
        with self.factory() as session:
            self.assertIsNone(session.get(RequestBudget, "account:fake:c"))

    def test_disabled_account_never_calls_provider(self):
        with self.factory() as session:
            session.get(CollectorAccount, "a").status = "disabled"
            session.commit()
        self.enqueue("disabled")
        provider = Pages([["article"]])
        self.assertEqual(self.worker(provider).run_once(now=self.now), "account_disabled")
        self.assertEqual(provider.cursors, [])


if __name__ == "__main__":
    unittest.main()
