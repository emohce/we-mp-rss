from __future__ import annotations

import os
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

from sqlalchemy import create_engine, select
from sqlalchemy.dialects import mysql, postgresql, sqlite
from sqlalchemy.schema import CreateTable
from sqlalchemy.orm import sessionmaker

from core.models.article import Article

from .jobs import JobRepository
from .models import (
    ArticleContentBlob,
    AnalysisRun,
    CollectionJob,
    CollectorAccount,
    CollectorCursor,
    DeliveryChannel,
    Digest,
    DigestItem,
    ExportJob,
    FeedbackEvent,
    OutboxEvent,
    PreferenceRule,
    PreferenceRuleProposal,
    RateLimitLedger,
    ShareLink,
    SourceProfile,
    Topic,
    ArticleTopic,
    UserArticleState,
    Workspace,
    WorkspaceArticle,
    WorkspaceMembership,
    WorkspaceSubscription,
    WorkflowJob,
)
from .rate_limit import RateLimitPolicy, RateSignal, RateSnapshot, RateState, classify_provider_error
from .settings import InfrastructureSettings, StorageProfile
from .storage import LocalContentStore


class InfrastructureSettingsTest(unittest.TestCase):
    def test_profiles_require_their_real_dependencies(self):
        lite = InfrastructureSettings()
        self.assertEqual(lite.validate(), [])

        standard = InfrastructureSettings(
            profile=StorageProfile.STANDARD,
            database_url="postgresql://db/wx",
            redis_url="redis://cache:6379/0",
        )
        self.assertEqual(standard.validate(), [])

        distributed = InfrastructureSettings(
            profile=StorageProfile.DISTRIBUTED,
            database_url="postgresql://db/wx",
            redis_url="redis://cache:6379/0",
        )
        self.assertIn("distributed profile requires MQTT_URL", distributed.validate())

    def test_describe_never_exposes_connection_strings(self):
        settings = InfrastructureSettings(
            profile=StorageProfile.DISTRIBUTED,
            database_url="postgresql://secret-user:secret-pass@db/wx",
            redis_url="redis://:secret@cache/0",
            mqtt_url="mqtt://user:secret@broker",
        )
        projection = str(settings.describe())
        self.assertNotIn("secret", projection)
        self.assertNotIn("secret-user", projection)

    def test_runtime_config_is_used_only_when_environment_is_absent(self):
        values = {
            "storage.profile": "standard",
            "db": "postgresql://config-user:secret@db/werss",
            "redis.url": "redis://cache/0",
        }
        with patch.dict(os.environ, {}, clear=True):
            settings = InfrastructureSettings.from_env(values.get)
        self.assertEqual(settings.profile, StorageProfile.STANDARD)
        self.assertEqual(settings.database_url, values["db"])
        self.assertEqual(settings.redis_url, values["redis.url"])


class LocalContentStoreTest(unittest.TestCase):
    def test_content_addressed_write_is_idempotent_and_path_safe(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store = LocalContentStore(temp_dir)
            first = store.put(b"article-body", suffix="html")
            second = store.put(b"article-body", suffix=".html")
            self.assertEqual(first, second)
            self.assertTrue(store.exists(first.key))
            self.assertEqual(store.get(first.key), b"article-body")
            with self.assertRaises(ValueError):
                store.get("../../outside")


class DialectCompilationTest(unittest.TestCase):
    def test_v2_schema_compiles_for_supported_sql_dialects(self):
        tables = [
            Article.__table__,
            Workspace.__table__,
            WorkspaceMembership.__table__,
            WorkspaceArticle.__table__,
            WorkspaceSubscription.__table__,
            UserArticleState.__table__,
            ArticleContentBlob.__table__,
            CollectorAccount.__table__,
            CollectorCursor.__table__,
            CollectionJob.__table__,
            RateLimitLedger.__table__,
            Topic.__table__,
            ArticleTopic.__table__,
            AnalysisRun.__table__,
            SourceProfile.__table__,
            FeedbackEvent.__table__,
            PreferenceRuleProposal.__table__,
            PreferenceRule.__table__,
            Digest.__table__,
            DigestItem.__table__,
            ShareLink.__table__,
            ExportJob.__table__,
            WorkflowJob.__table__,
            DeliveryChannel.__table__,
            OutboxEvent.__table__,
        ]
        for dialect in (sqlite.dialect(), postgresql.dialect(), mysql.dialect()):
            for table in tables:
                ddl = str(CreateTable(table).compile(dialect=dialect))
                self.assertIn("CREATE TABLE", ddl)


class RateLimitPolicyTest(unittest.TestCase):
    def test_backoff_probe_and_success_recovery(self):
        now = datetime(2026, 8, 24, 6, 30)
        limited = RateLimitPolicy.apply(
            RateSnapshot(), RateSignal.RATE_LIMITED, now=now
        )
        self.assertEqual(limited.state, RateState.COOLDOWN)
        self.assertEqual(limited.cooldown_until, now + timedelta(minutes=15))
        self.assertFalse(limited.may_request(now + timedelta(minutes=14)))

        probe = RateLimitPolicy.apply(
            limited, RateSignal.PROBE_DUE, now=now + timedelta(minutes=15)
        )
        self.assertEqual(probe.state, RateState.PROBE)
        healthy = RateLimitPolicy.apply(probe, RateSignal.SUCCESS, now=now)
        self.assertEqual(healthy, RateSnapshot(RateState.HEALTHY, 0, None, "success"))

    def test_error_codes_are_not_conflated(self):
        self.assertEqual(classify_provider_error("200013"), RateSignal.RATE_LIMITED)
        self.assertEqual(classify_provider_error("200003"), RateSignal.AUTH_INVALID)
        self.assertEqual(classify_provider_error(None, 401), RateSignal.AUTH_INVALID)


class JobRepositoryTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
        tables = [
            Article.__table__,
            Workspace.__table__,
            WorkspaceMembership.__table__,
            WorkspaceArticle.__table__,
            WorkspaceSubscription.__table__,
            CollectorAccount.__table__,
            CollectorCursor.__table__,
            CollectionJob.__table__,
            WorkflowJob.__table__,
            OutboxEvent.__table__,
        ]
        Article.metadata.create_all(self.engine, tables=tables)
        self.session_factory = sessionmaker(self.engine, expire_on_commit=False, future=True)
        with self.session_factory() as session:
            workspace = Workspace(id="workspace", name="Personal", slug="personal", owner_user_id="user")
            account = CollectorAccount(
                id="account", workspace_id="workspace", provider="mp", label="primary"
            )
            session.add_all([workspace, account])
            session.commit()
        self.repository = JobRepository(self.session_factory)

    def test_enqueue_is_idempotent_and_claim_is_leased(self):
        first, created = self.repository.enqueue(
            workspace_id="workspace",
            provider="mp",
            source_id="source",
            idempotency_key="daily:workspace:source:2026-08-24",
            account_id="account",
        )
        second, created_again = self.repository.enqueue(
            workspace_id="workspace",
            provider="mp",
            source_id="source",
            idempotency_key="daily:workspace:source:2026-08-24",
            account_id="account",
        )
        self.assertTrue(created)
        self.assertFalse(created_again)
        self.assertEqual(first.id, second.id)

        claimed = self.repository.claim_next(now=datetime.utcnow())
        self.assertIsNotNone(claimed)
        self.assertIsNone(self.repository.claim_next(now=datetime.utcnow()))

    def test_cursor_advances_only_after_article_persistence(self):
        job, _ = self.repository.enqueue(
            workspace_id="workspace",
            provider="mp",
            source_id="source",
            idempotency_key="page:1",
            account_id="account",
        )
        claimed = self.repository.claim_next(now=datetime.utcnow())
        self.assertIsNotNone(claimed)

        with self.assertRaises(ValueError):
            self.repository.complete_page(
                job_id=job.id,
                lease_token=claimed.lease_token,
                account_id="account",
                next_cursor={"begin": 5},
                article_ids=["missing"],
                ingestion_source="mp",
            )
        with self.session_factory() as session:
            self.assertIsNone(session.scalar(select(CollectorCursor)))

        with self.session_factory() as session:
            session.add(
                Article(
                    id="article-1",
                    mp_id="source",
                    title="A persisted article",
                    url="https://mp.weixin.qq.com/s/example",
                    publish_time=1,
                )
            )
            session.commit()

        self.repository.complete_page(
            job_id=job.id,
            lease_token=claimed.lease_token,
            account_id="account",
            next_cursor={"begin": 5},
            article_ids=["article-1"],
            ingestion_source="mp",
        )
        with self.session_factory() as session:
            cursor = session.scalar(select(CollectorCursor))
            completed_job = session.get(CollectionJob, job.id)
            self.assertEqual(cursor.cursor, {"begin": 5})
            self.assertEqual(completed_job.state, "completed")
            self.assertEqual(session.query(WorkspaceArticle).count(), 1)
            self.assertEqual(session.query(OutboxEvent).count(), 1)


if __name__ == "__main__":
    unittest.main()
