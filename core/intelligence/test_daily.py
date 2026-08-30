from datetime import date, datetime, timedelta, timezone
import unittest

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from core.models.base import Base
from core.models.article import Article
from .collector import CollectedPage, CollectionWorker
from .daily import coverage_for, queue_reconciliations
from .jobs import JobRepository
from .models import (AnalysisRun, CollectionJob, CollectorAccount, DailyRun, DailyRunSource,
                     Digest, DigestRevision, OutboxEvent, WorkflowJob, Workspace, WorkspaceArticle,
                     WorkspaceMembership, WorkspaceSubscription)
from .rate_limit import RateLimitRepository
from .scheduling import DEFAULT_SCHEDULE
from .services import AccessDenied, DigestService
from .workflow import DailyAutomationScheduler, WorkflowJobRepository, WorkflowWorker


class DailyDigestTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite://")
        Base.metadata.create_all(self.engine, tables=[t for n, t in Base.metadata.tables.items()
                                                    if n == "articles" or n.startswith("int_")])
        self.factory = sessionmaker(self.engine, expire_on_commit=False)
        self.day = date(2026, 8, 30)
        self.publish = datetime(2026, 8, 30, 0, 0)
        self.collect = self.publish - timedelta(minutes=90)
        self.timestamp = int(DEFAULT_SCHEDULE.moments(self.day)["collect"].timestamp())
        with self.factory() as session:
            session.add_all([Workspace(id="w", name="W", slug="w", owner_user_id="u"),
                             WorkspaceMembership(workspace_id="w", user_id="u", role="owner"),
                             CollectorAccount(id="a", workspace_id="w", provider="fake", label="A"),
                             WorkspaceSubscription(workspace_id="w", source_id="s", provider="fake")])
            session.commit()
        self.jobs = JobRepository(self.factory)
        self.workflows = WorkflowJobRepository(self.factory)
        self.scheduler = DailyAutomationScheduler(session_factory=self.factory, collection_jobs=self.jobs,
                                                   workflow_jobs=self.workflows)

    def tearDown(self):
        self.engine.dispose()

    def generate(self, now=None):
        with self.factory() as session:
            return DigestService.generate(session, workspace_id="w", user_id="u", digest_date=self.day,
                                           now=now or self.publish)

    def test_not_due_does_not_publish_or_materialize_digest(self):
        with self.assertRaises(ValueError):
            self.generate(self.publish - timedelta(seconds=1))
        with self.factory() as session:
            self.assertEqual(session.query(Digest).count(), 0)
            self.assertEqual(session.query(DailyRun).count(), 0)

    def test_cohort_is_frozen_and_disabled_collection_is_visible(self):
        self.scheduler.schedule_day(self.day, include_collection=False, now=self.collect)
        with self.factory() as session:
            session.scalar(select(WorkspaceSubscription)).status = "paused"
            session.add(WorkspaceSubscription(workspace_id="w", provider="fake", source_id="new"))
            session.commit()
        self.scheduler.schedule_day(self.day, include_collection=True, now=self.publish)
        digest = self.generate()
        self.assertEqual(digest.status, "partial")
        self.assertEqual(digest.coverage["expected"], 1)
        self.assertEqual(digest.coverage["skipped"], 1)
        self.assertEqual(digest.coverage["sources"][0]["source_id"], "s")
        self.assertEqual(digest.coverage["sources"][0]["reason"], "collection_disabled")
        with self.factory() as session:
            self.assertEqual(session.query(CollectionJob).count(), 0)

    def test_late_collection_and_analysis_automatically_revise_partial_digest(self):
        self.scheduler.schedule_day(self.day, now=self.collect)
        first = self.generate()
        self.assertEqual(first.revision, 1)
        self.assertEqual(first.coverage["pending"], 1)
        timestamp = self.timestamp

        class Provider:
            def fetch_page(self, **kwargs):
                return CollectedPage(({"id": "late", "mp_id": "s", "title": "AI 人工智能",
                                       "publish_time": timestamp, "status": 1},), {"exhausted": True}, "fake")

        worker = CollectionWorker(session_factory=self.factory, jobs=self.jobs,
                                  rate_limits=RateLimitRepository(self.factory), adapters={"fake": Provider()})
        arrival = self.publish + timedelta(minutes=5)
        self.assertEqual(worker.run_once(now=arrival), "completed")
        workflow_worker = WorkflowWorker(session_factory=self.factory, repository=self.workflows)
        for _ in range(12):
            result = workflow_worker.run_once(now=arrival)
            self.assertNotEqual(result, "retry")
            if result == "idle":
                break
        with self.factory() as session:
            digest = session.scalar(select(Digest))
            self.assertEqual(digest.status, "published")
            self.assertEqual(digest.revision, 3)
            self.assertTrue(digest.coverage["complete"])
            data = DigestService.serialize(session, workspace_id="w", user_id="u", digest_date=self.day.isoformat())
            self.assertTrue(data["items"][0]["is_late"])
            self.assertEqual(session.query(DigestRevision).count(), 3)
            events = list(session.scalars(select(OutboxEvent).where(OutboxEvent.aggregate_type == "digest")))
            self.assertEqual([event.payload["revision"] for event in events], [1, 2, 3])
            DigestService.generate(session, workspace_id="w", user_id="u", digest_date=self.day, now=arrival)
            self.assertEqual(session.query(DigestRevision).count(), 3)
            first_snapshot = session.scalar(select(DigestRevision).where(DigestRevision.revision == 1)).snapshot
            self.assertEqual(first_snapshot["items"], [])

    def test_failed_source_is_not_reported_complete(self):
        self.scheduler.schedule_day(self.day, now=self.collect)
        with self.factory() as session:
            job = session.scalar(select(CollectionJob))
            job.state = "failed"
            job.last_error_code = "200003"
            session.commit()
        digest = self.generate()
        self.assertEqual(digest.coverage["failed"], 1)
        self.assertFalse(digest.coverage["complete"])

    def test_all_candidates_are_included_and_snapshot_only_changes_on_revision(self):
        with self.factory() as session:
            for index in range(601):
                item = f"article-{index:04d}"
                session.add(Article(id=item, mp_id="s", title=item, publish_time=self.timestamp, status=1))
                session.add(WorkspaceArticle(workspace_id="w", article_id=item, source_id="s", added_at=self.collect))
            session.commit()
        digest = self.generate()
        with self.factory() as session:
            data = DigestService.serialize(session, workspace_id="w", user_id="u", digest_date=self.day.isoformat())
            self.assertEqual(len(data["items"]), 601)
            session.get(Article, "article-0600").title = "Updated"
            session.commit()
            before = DigestService.serialize(session, workspace_id="w", user_id="u", digest_date=self.day.isoformat())
            self.assertEqual(before["items"][0]["article"]["title"], "article-0600")
        self.assertEqual(self.generate().revision, 2)

    def test_share_follows_revision_without_mutating_snapshot_and_can_be_revoked(self):
        with self.factory() as session:
            session.add(Article(id="one", mp_id="s", title="One", publish_time=self.timestamp, status=1))
            session.add(WorkspaceArticle(workspace_id="w", article_id="one", source_id="s", added_at=self.collect))
            session.commit()
        self.generate()
        with self.factory() as session:
            link, token = DigestService.create_share_link(session, workspace_id="w", user_id="u",
                                                         digest_date=self.day.isoformat())
            public = DigestService.serialize_public_share(session, token)
            self.assertEqual(public["revision"], 1)
            self.assertNotIn("feedback_sentiment", public["items"][0]["article"])
            private = DigestService.serialize(session, workspace_id="w", user_id="u", digest_date=self.day.isoformat())
            self.assertIn("feedback_sentiment", private["items"][0]["article"])
            session.get(Article, "one").title = "Revised"
            session.commit()
            DigestService.generate(session, workspace_id="w", user_id="u", digest_date=self.day, now=self.publish)
            self.assertEqual(DigestService.serialize_public_share(session, token)["revision"], 2)
            DigestService.revoke_share(session, workspace_id="w", user_id="u", share_id=link.id)
            with self.assertRaises(AccessDenied):
                DigestService.resolve_share(session, token)

    def test_old_dated_late_article_is_reconciled_without_rolling_lookback_loss(self):
        old_day = date(2026, 8, 1)
        self.scheduler.schedule_day(old_day, now=self.collect)
        with self.factory() as session:
            session.add(Article(id="old", mp_id="s", title="Old", status=1,
                                publish_time=int(DEFAULT_SCHEDULE.moments(old_day)["collect"].timestamp())))
            session.flush()
            queue_reconciliations(session, workspace_ids=["w"], article_ids=["old"], cause="late-import",
                                  now=self.publish)
            session.commit()
            job = session.scalar(select(WorkflowJob).where(WorkflowJob.kind == "digest_reconcile"))
            self.assertEqual(job.payload["digest_date"], old_day.isoformat())


if __name__ == "__main__":
    unittest.main()
