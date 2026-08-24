from __future__ import annotations

import json
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from core.models.article import Article
from core.models.base import Base

from .analysis import CliAnalyzer, HeuristicAnalyzer
from .exporting import SingleArticleExporter, safe_filename
from .models import (
    AnalysisRun,
    ArticleTopic,
    CollectionJob,
    CollectorAccount,
    FeedbackEvent,
    PreferenceRule,
    Topic,
    UserArticleState,
    Workspace,
    WorkspaceArticle,
    WorkspaceMembership,
    WorkspaceSubscription,
    utcnow,
)
from .scheduling import DEFAULT_SCHEDULE
from .services import (
    AccessDenied,
    AnalysisService,
    ArticleService,
    DigestService,
    FeedbackService,
    SubscriptionService,
    TenantService,
)


class IntelligenceServiceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite://")
        tables = [
            table
            for name, table in Base.metadata.tables.items()
            if name == "articles" or name.startswith("int_")
        ]
        Base.metadata.create_all(self.engine, tables=tables)
        self.session = Session(self.engine)
        self.session.add_all(
            [
                Workspace(id="workspace-a", name="A", slug="a", owner_user_id="user-a"),
                Workspace(id="workspace-b", name="B", slug="b", owner_user_id="user-b"),
                WorkspaceMembership(workspace_id="workspace-a", user_id="user-a", role="owner"),
                WorkspaceMembership(workspace_id="workspace-b", user_id="user-b", role="owner"),
            ]
        )
        self.session.commit()

    def tearDown(self) -> None:
        self.session.close()
        self.engine.dispose()

    def add_article(
        self,
        article_id: str,
        *,
        workspace_id: str = "workspace-a",
        source_id: str = "source-1",
        title: str = "AI 创业观察",
        publish_time: int = 1_777_000_000,
    ) -> Article:
        article = self.session.get(Article, article_id)
        if article is None:
            article = Article(
                id=article_id,
                mp_id=source_id,
                title=title,
                description="人工智能产品与商业趋势",
                content="<p>这是完整正文，讨论 AI、开源软件与创业。</p>",
                content_html="<p>这是完整正文，讨论 AI、开源软件与创业。</p>",
                url=f"https://example.test/{article_id}",
                publish_time=publish_time,
                status=1,
            )
            self.session.add(article)
            self.session.flush()
        self.session.add(
            WorkspaceArticle(
                workspace_id=workspace_id,
                article_id=article_id,
                source_id=source_id,
            )
        )
        self.session.commit()
        return article

    def test_article_projection_and_analysis_are_workspace_scoped(self) -> None:
        self.add_article("shared")
        self.add_article("shared", workspace_id="workspace-b")
        self.session.add(
            AnalysisRun(
                workspace_id="workspace-b",
                article_id="shared",
                provider="test",
                prompt_version="v1",
                summary="B workspace only",
                output={"relevance_score": 0.9, "reason": "B only"},
            )
        )
        private_topic = Topic(slug="workspace-b-only", name="B 私有主题")
        self.session.add(private_topic)
        self.session.flush()
        self.session.add(
            ArticleTopic(
                workspace_id="workspace-b",
                article_id="shared",
                topic_id=private_topic.id,
                confidence=0.95,
                analysis_version="v1",
            )
        )
        self.session.commit()

        listed = ArticleService.list_articles(
            self.session, workspace_id="workspace-a", user_id="user-a"
        )
        self.assertEqual(len(listed["items"]), 1)
        self.assertNotIn("content", listed["items"][0])
        self.assertEqual(listed["items"][0]["ai_summary"], "")

        detail = ArticleService.get_article(
            self.session,
            workspace_id="workspace-a",
            user_id="user-a",
            article_id="shared",
        )
        self.assertIn("完整正文", detail["content"])
        self.assertEqual(detail["ai_summary"], "")
        self.assertEqual(detail["topics"], [])
        with self.assertRaises(AccessDenied):
            ArticleService.get_article(
                self.session,
                workspace_id="workspace-a",
                user_id="user-a",
                article_id="missing",
            )

    def test_legacy_backfill_is_bounded_and_idempotent(self) -> None:
        self.session.add(
            Article(
                id="legacy",
                mp_id="legacy-source",
                title="Legacy",
                publish_time=1_777_000_000,
                status=1,
            )
        )
        self.session.commit()
        first = TenantService.attach_legacy_articles(
            self.session,
            workspace_id="workspace-a",
            user_id="user-a",
            batch_size=1,
            authorized=True,
        )
        second = TenantService.attach_legacy_articles(
            self.session,
            workspace_id="workspace-a",
            user_id="user-a",
            batch_size=1,
            authorized=True,
        )
        self.assertEqual(first, {"attached": 1, "has_more": False})
        self.assertEqual(second, {"attached": 0, "has_more": False})

    def test_legacy_backfill_requires_explicit_admin_authorization(self) -> None:
        with self.assertRaises(AccessDenied):
            TenantService.attach_legacy_articles(
                self.session,
                workspace_id="workspace-a",
                user_id="user-a",
            )

    def test_feedback_does_not_conflate_like_with_favorite(self) -> None:
        self.add_article("feedback")
        FeedbackService.record(
            self.session,
            workspace_id="workspace-a",
            user_id="user-a",
            article_id="feedback",
            event_type="like",
        )
        state = self.session.scalar(select(UserArticleState))
        self.assertEqual(state.sentiment, "like")
        self.assertEqual(state.relevance_override, 1.0)
        self.assertFalse(state.is_favorite)

        filtered = ArticleService.list_articles(
            self.session,
            workspace_id="workspace-a",
            user_id="user-a",
            min_relevance=0.9,
        )
        self.assertEqual(filtered["items"][0]["effective_relevance"], 1.0)

        FeedbackService.record(
            self.session,
            workspace_id="workspace-a",
            user_id="user-a",
            article_id="feedback",
            event_type="favorite",
        )
        self.session.refresh(state)
        self.assertTrue(state.is_favorite)

    def test_analysis_topics_and_relevance_filter(self) -> None:
        self.add_article("analysis")
        envelope = AnalysisService().analyze_article(
            self.session,
            workspace_id="workspace-a",
            user_id="user-a",
            article_id="analysis",
        )
        self.assertEqual(envelope.provider, "heuristic")
        self.assertTrue(envelope.topics)
        result = ArticleService.list_articles(
            self.session,
            workspace_id="workspace-a",
            user_id="user-a",
            min_relevance=0.6,
        )
        self.assertEqual(result["items"], [])
        self.assertFalse(result["has_more"])

    def test_article_detail_deduplicates_topics_across_analysis_versions(self) -> None:
        self.add_article("topic-versions")
        topic = Topic(slug="ai", name="AI")
        self.session.add(topic)
        self.session.flush()
        self.session.add_all(
            [
                ArticleTopic(
                    workspace_id="workspace-a",
                    article_id="topic-versions",
                    topic_id=topic.id,
                    confidence=0.9,
                    analysis_version="v2",
                ),
                ArticleTopic(
                    workspace_id="workspace-a",
                    article_id="topic-versions",
                    topic_id=topic.id,
                    confidence=0.7,
                    analysis_version="v1",
                ),
            ]
        )
        self.session.commit()
        detail = ArticleService.get_article(
            self.session,
            workspace_id="workspace-a",
            user_id="user-a",
            article_id="topic-versions",
        )
        self.assertEqual(detail["topics"], [{"slug": "ai", "name": "AI", "confidence": 0.9}])

    def test_preference_proposals_require_distinct_articles_and_user_approval(self) -> None:
        now = utcnow()
        for index in range(20):
            article_id = f"preference-{index}"
            self.add_article(article_id, source_id="preferred-source")
            self.session.add(
                FeedbackEvent(
                    workspace_id="workspace-a",
                    user_id="user-a",
                    article_id=article_id,
                    event_type="like",
                    created_at=now - timedelta(days=10) + timedelta(hours=index * 13),
                )
            )
            self.session.add(
                UserArticleState(
                    workspace_id="workspace-a",
                    user_id="user-a",
                    article_id=article_id,
                    sentiment="like",
                    relevance_override=1.0,
                )
            )
        self.session.commit()
        proposals = FeedbackService.propose_preferences(
            self.session, workspace_id="workspace-a", user_id="user-a"
        )
        self.assertEqual(len(proposals), 1)
        self.assertEqual(proposals[0].condition, {"source_ids": ["preferred-source"]})
        reviewed = FeedbackService.review_proposal(
            self.session,
            workspace_id="workspace-a",
            user_id="user-a",
            proposal_id=proposals[0].id,
            approve=True,
        )
        self.assertEqual(reviewed.status, "approved")
        self.assertEqual(self.session.query(PreferenceRule).count(), 1)

    def test_subscription_initial_discovery_is_idempotent(self) -> None:
        first_subscription, first_job = SubscriptionService.subscribe(
            self.session,
            workspace_id="workspace-a",
            user_id="user-a",
            source_id="source-1",
        )
        second_subscription, second_job = SubscriptionService.subscribe(
            self.session,
            workspace_id="workspace-a",
            user_id="user-a",
            source_id="source-1",
        )
        self.assertEqual(first_subscription.id, second_subscription.id)
        self.assertEqual(first_job.id, second_job.id)
        self.assertEqual(self.session.query(WorkspaceSubscription).count(), 1)
        self.assertEqual(self.session.query(CollectionJob).count(), 1)
        self.assertEqual(first_job.payload["page_budget"], 1)
        account = self.session.scalar(select(CollectorAccount))
        self.assertIsNone(account.workspace_id)
        self.assertEqual(account.secret_ref, "driver.token")

    def test_daily_digest_and_expiring_share_link(self) -> None:
        digest_date = date(2026, 8, 24)
        publish_time = int(DEFAULT_SCHEDULE.moments(digest_date)["collect"].timestamp())
        self.add_article("digest", publish_time=publish_time)
        AnalysisService().analyze_article(
            self.session,
            workspace_id="workspace-a",
            user_id="user-a",
            article_id="digest",
        )
        digest = DigestService.generate(
            self.session,
            workspace_id="workspace-a",
            user_id="user-a",
            digest_date=digest_date,
        )
        self.assertEqual(digest.status, "published")
        serialized = DigestService.serialize(
            self.session,
            workspace_id="workspace-a",
            user_id="user-a",
            digest_date=digest_date.isoformat(),
        )
        self.assertEqual(len(serialized["items"]), 1)
        link, token = DigestService.create_share_link(
            self.session,
            workspace_id="workspace-a",
            user_id="user-a",
            digest_date=digest_date.isoformat(),
            expires_in_hours=24,
        )
        resolved_link, resolved_digest = DigestService.resolve_share(self.session, token)
        self.assertEqual(resolved_link.id, link.id)
        self.assertEqual(resolved_digest.id, digest.id)
        self.assertNotEqual(link.token_hash, token)
        public_data = DigestService.serialize_public_share(self.session, token)
        self.assertNotIn("content", public_data["items"][0]["article"])
        self.assertNotIn("is_favorite", public_data["items"][0]["article"])


class IntelligenceUtilityTest(unittest.TestCase):
    def test_heuristic_export_schedule_and_cli_safeguards(self) -> None:
        article = {
            "id": "a/1",
            "title": "AI: 产品/创业?",
            "description": "人工智能与开源软件",
            "content": "<p>正文</p>",
            "url": "https://example.test/a",
        }
        analysis = HeuristicAnalyzer().analyze(article)
        self.assertTrue(analysis.topics)
        self.assertLessEqual(len(analysis.summary), 321)

        exporter = SingleArticleExporter()
        for format_name in ("md", "html", "json"):
            artifact = exporter.export(article, format_name)
            self.assertTrue(artifact.content)
            self.assertTrue(artifact.filename.endswith(f".{format_name}"))
        self.assertNotIn("/", safe_filename(article["title"]))

        unsafe = {
            **article,
            "content": (
                "<p onclick='steal()'>正文<img src='javascript:steal()' onerror='steal()'></p>"
                "<script>steal()</script><form action='https://evil.test'><input></form>"
            ),
            "url": "javascript:steal()",
        }
        exported_html = exporter.export(unsafe, "html").content.decode("utf-8")
        self.assertIn("Content-Security-Policy", exported_html)
        self.assertNotIn("<script", exported_html)
        self.assertNotIn("onclick", exported_html)
        self.assertNotIn("javascript:", exported_html)
        self.assertNotIn("<form", exported_html)

        moments = DEFAULT_SCHEDULE.moments(date(2026, 8, 24))
        self.assertEqual(moments["cutoff"].hour, 7)
        self.assertEqual(moments["cutoff"].minute, 50)
        self.assertEqual(moments["digest"].hour, 8)
        window_start, window_end = DEFAULT_SCHEDULE.article_window(date(2026, 8, 24))
        self.assertEqual(window_end - window_start + 1, 24 * 60 * 60)

        with tempfile.TemporaryDirectory() as temp_name:
            temp_dir = Path(temp_name)
            schema_path = temp_dir / "schema.json"
            input_path = temp_dir / "article.json"
            schema_path.write_text("{}", encoding="utf-8")
            input_path.write_text(json.dumps(article), encoding="utf-8")
            command, stdin = CliAnalyzer("codex")._command(temp_dir, schema_path, input_path)
            self.assertIsInstance(command, list)
            self.assertIn("--ephemeral", command)
            self.assertIn("read-only", command)
            self.assertIn("--ignore-rules", command)
            self.assertIn("untrusted", stdin)


if __name__ == "__main__":
    unittest.main()
