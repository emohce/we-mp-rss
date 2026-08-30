from datetime import date, datetime, timedelta
import tempfile
import unittest

from sqlalchemy import create_engine, event, select, text
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import sessionmaker

from core.models.article import Article
from core.models.base import Base
from . import test_services as fixtures
from .collector import CollectedPage, CollectionWorker
from .exporting import SingleArticleExporter
from .jobs import JobRepository
from .models import (AnalysisRun, ArticleContentBlob, ArticleTopic, CollectorAccount, FeedbackEvent,
                     PreferenceRule, PreferenceRuleProposal, SearchDocument, UserArticleState,
                     Workspace, WorkspaceArticle, WorkspaceMembership, utcnow)
from .preferences import revoke_rule, save_filter, validate_filter
from .ranking import RankingQuery, topic_slug
from .rate_limit import RateLimitRepository
from .scheduling import DEFAULT_SCHEDULE
from .search import index_article
from .services import ArticleService, DigestService, FeedbackService
from .storage import LocalContentStore


class PreferenceRankingTest(unittest.TestCase):
    setUp = fixtures.IntelligenceServiceTest.setUp
    tearDown = fixtures.IntelligenceServiceTest.tearDown
    add_article = fixtures.IntelligenceServiceTest.add_article

    def listing(self, **kwargs):
        return ArticleService.list_articles(self.session, workspace_id="workspace-a", user_id="user-a", **kwargs)

    def feedback(self, article_id, kind, value=None):
        return FeedbackService.record(self.session, workspace_id="workspace-a", user_id="user-a",
                                      article_id=article_id, event_type=kind, value=value)

    def test_inbox_digest_scores_match_and_explicit_feedback_wins(self):
        day = date(2026, 8, 24)
        timestamp = int(DEFAULT_SCHEDULE.moments(day)["collect"].timestamp())
        for item in ("liked", "neutral", "disliked"):
            self.add_article(item, publish_time=timestamp)
        rule = PreferenceRule(workspace_id="workspace-a", user_id="user-a", rule_type="source_preference",
                              condition={"source_ids": ["source-1"]}, action={"rank_boost": 0.25})
        self.session.add(rule)
        self.session.commit()
        self.feedback("liked", "like")
        self.feedback("disliked", "dislike")
        self.feedback("disliked", "favorite")
        listed = self.listing()["items"]
        self.assertEqual([(row["id"], row["effective_relevance"]) for row in listed],
                         [("liked", 1.0), ("neutral", 0.75), ("disliked", 0.0)])
        self.assertEqual(listed[-1]["rank_adjustment"], 0)
        DigestService.generate(self.session, workspace_id="workspace-a", user_id="user-a", digest_date=day)
        digest = DigestService.serialize(self.session, workspace_id="workspace-a", user_id="user-a", digest_date=day.isoformat())
        self.assertEqual([(row["article"]["id"], row["relevance_score"]) for row in digest["items"]],
                         [(row["id"], row["effective_relevance"]) for row in listed])
        revoke_rule(self.session, workspace_id="workspace-a", user_id="user-a", rule_id=rule.id)
        revoke_rule(self.session, workspace_id="workspace-a", user_id="user-a", rule_id=rule.id)
        self.assertEqual(rule.version, 2)
        self.assertEqual(self.listing()["items"][1]["effective_relevance"], 0.5)

    def test_personal_topic_correction_filters_and_rules_do_not_change_other_users(self):
        self.add_article("article")
        self.session.add(WorkspaceMembership(workspace_id="workspace-a", user_id="reader-b", role="member"))
        topic = fixtures.Topic(slug="ai", name="AI")
        self.session.add(topic)
        self.session.flush()
        self.session.add(ArticleTopic(workspace_id="workspace-a", article_id="article", topic_id=topic.id,
                                      confidence=0.8, analysis_version="v1"))
        self.session.commit()
        self.feedback("article", "topic_correction", {"topics": ["新能源"]})
        self.session.add(PreferenceRule(workspace_id="workspace-a", user_id="user-a", rule_type="topic_preference",
                                        condition={"topic_slugs": [topic_slug("新能源")]}, action={"rank_boost": 0.25}))
        self.session.commit()
        filtered = self.listing(topic="新能源", min_relevance=0.7)
        self.assertEqual(filtered["total"], 1)
        self.assertEqual(filtered["items"][0]["effective_relevance"], 0.75)
        self.assertEqual(self.listing(topic="ai")["items"], [])
        choices = RankingQuery(self.session, "workspace-a", "user-a").topic_choices()
        self.assertEqual(choices[0]["name"], "新能源")
        other = ArticleService.list_articles(self.session, workspace_id="workspace-a", user_id="reader-b", topic="ai")
        self.assertEqual(other["total"], 1)
        self.assertEqual(other["items"][0]["effective_relevance"], 0.5)
        self.assertEqual(self.session.query(ArticleTopic).count(), 1)
        self.feedback("article", "topic_correction", {"reset": True})
        self.assertEqual(self.listing(topic="ai")["total"], 1)

    def test_invalid_feedback_is_rejected_before_state_or_event_write(self):
        self.add_article("article")
        for kind, value in (("topic_correction", {"topics": "not-a-list"}),
                            ("topic_correction", {"topics": ["x"] * 9}),
                            ("summary_preference", {"style": "execute"})):
            with self.assertRaises(ValueError):
                self.feedback("article", kind, value)
        self.assertEqual(self.session.query(FeedbackEvent).count(), 0)
        self.assertEqual(self.session.query(UserArticleState).count(), 0)

    def test_all_history_supports_source_topic_and_reading_proposals_with_idempotent_approval(self):
        old = utcnow() - timedelta(days=180)
        topic = fixtures.Topic(slug="ai", name="AI")
        self.session.add(topic)
        self.session.flush()
        for index in range(20):
            item = f"old-{index}"
            self.add_article(item)
            self.session.add_all([
                FeedbackEvent(workspace_id="workspace-a", user_id="user-a", article_id=item, event_type="like",
                              created_at=old + timedelta(days=index)),
                FeedbackEvent(workspace_id="workspace-a", user_id="user-a", article_id=item,
                              event_type="summary_preference", value={"style": "brief"},
                              created_at=old + timedelta(days=index, seconds=1)),
                UserArticleState(workspace_id="workspace-a", user_id="user-a", article_id=item, sentiment="like"),
                ArticleTopic(workspace_id="workspace-a", article_id=item, topic_id=topic.id,
                             confidence=0.8, analysis_version="v1"),
            ])
        self.session.commit()
        proposals = FeedbackService.propose_preferences(self.session, workspace_id="workspace-a", user_id="user-a")
        self.assertEqual({p.rule_type for p in proposals}, {"source_preference", "topic_preference", "reading_preference"})
        for _ in range(2):
            FeedbackService.review_proposal(self.session, workspace_id="workspace-a", user_id="user-a",
                                            proposal_id=proposals[0].id, approve=True)
        self.assertEqual(self.session.query(PreferenceRule).count(), 1)
        self.assertEqual(FeedbackService.propose_preferences(self.session, workspace_id="workspace-a", user_id="user-a"), [])

    def test_relevance_filter_finds_older_match_beyond_500_and_cursor_is_scope_bound(self):
        for index in range(620):
            self.session.add(Article(id=f"row-{index:04d}", mp_id="source-1", title="Row", publish_time=index + 1, status=1))
            self.session.add(WorkspaceArticle(workspace_id="workspace-a", article_id=f"row-{index:04d}", source_id="source-1"))
        self.session.add(UserArticleState(workspace_id="workspace-a", user_id="user-a", article_id="row-0000", relevance_override=1.0))
        self.session.commit()
        filtered = self.listing(min_relevance=0.9)
        self.assertEqual([item["id"] for item in filtered["items"]], ["row-0000"])
        self.assertEqual(filtered["total"], 1)
        first = self.listing(limit=2)
        second = self.listing(limit=2, cursor=first["next_cursor"])
        self.assertFalse({item["id"] for item in first["items"]} & {item["id"] for item in second["items"]})
        with self.assertRaises(ValueError):
            self.listing(limit=2, cursor=first["next_cursor"], topic="other")
        calls = []
        def track(conn, cursor, statement, params, context, executemany):
            if statement.lstrip().upper().startswith("SELECT"):
                calls.append(statement)
        event.listen(self.engine, "before_cursor_execute", track)
        try:
            self.listing(limit=100)
        finally:
            event.remove(self.engine, "before_cursor_execute", track)
        self.assertLessEqual(len(calls), 8, "list serialization must not lazy-load article bodies")

    def test_saved_filters_validate_and_update_only_same_owner(self):
        saved = save_filter(self.session, workspace_id="workspace-a", user_id="user-a", name="AI",
                             filters={"topic": "ai", "min_relevance": 0.7})
        second = save_filter(self.session, workspace_id="workspace-a", user_id="user-a", name="AI",
                              filters={"topic": "ai", "order": "newest"})
        self.assertEqual(saved.id, second.id)
        for value in ({"sql": "select"}, {"min_relevance": float("nan")}, {"date_from": 20, "date_to": 10}):
            with self.assertRaises(ValueError):
                validate_filter(value)

    def test_sqlite_fts_and_legacy_literal_body_search(self):
        article = self.add_article("indexed")
        article.content = article.content_html = "<h2>新能源创新</h2><p>正文检索能力</p>"
        self.session.execute(text("CREATE VIRTUAL TABLE int_search_fts USING fts5(article_id UNINDEXED, search_text, tokenize='trigram')"))
        self.session.execute(text("CREATE TRIGGER fixture_search_insert AFTER INSERT ON int_search_documents BEGIN INSERT INTO int_search_fts(article_id, search_text) VALUES (new.article_id, new.search_text); END"))
        index_article(self.session, article)
        self.session.commit()
        self.assertEqual(self.listing(search="正文检索")["total"], 1)
        legacy = self.add_article("legacy")
        legacy.content = legacy.content_html = "<p>literal 100%_match</p>"
        self.session.commit()
        self.assertEqual(self.listing(search="100%_match")["total"], 1)
        self.assertEqual(self.listing(search="missing%_")["total"], 0)

    def test_topic_ranking_compiles_for_postgresql_and_markdown_is_not_html(self):
        self.session.add(PreferenceRule(workspace_id="workspace-a", user_id="user-a", rule_type="topic_preference",
            condition={"topic_slugs": ["ai"]}, action={"rank_boost": 0.25}))
        self.session.commit()
        query = RankingQuery(self.session, "workspace-a", "user-a")
        sql = str(query.ordered(query.filtered(topic="ai", min_relevance=0.5)).compile(dialect=postgresql.dialect()))
        self.assertIn("int_feedback_events", sql)
        exported = SingleArticleExporter().export({"title": "Title", "content_html": "<h2>Section</h2><ul><li>One</li></ul><strong>Bold</strong><script>bad()</script>"}, "md")
        markdown = exported.content.decode()
        self.assertIn("## Section", markdown)
        self.assertIn("- One", markdown)
        self.assertIn("**Bold**", markdown)
        self.assertNotIn("<h2>", markdown)
        self.assertNotIn("bad()", markdown)


class ContentCollectionTest(unittest.TestCase):
    def test_collected_body_binds_deduplicated_objects_and_local_read_verifies_hash(self):
        engine = create_engine("sqlite://")
        Base.metadata.create_all(engine, tables=[t for n, t in Base.metadata.tables.items() if n == "articles" or n.startswith("int_")])
        factory = sessionmaker(engine, expire_on_commit=False)
        with factory() as session:
            session.add_all([Workspace(id="w", name="W", slug="w", owner_user_id="u"),
                             WorkspaceMembership(workspace_id="w", user_id="u", role="owner"),
                             CollectorAccount(id="a", workspace_id="w", provider="fake", label="A")])
            session.commit()
        now = datetime(2026, 8, 30)
        body = "<h2>Shared body</h2><p>存储正文</p>"
        class Provider:
            def fetch_page(self, **kwargs):
                return CollectedPage(tuple({"id": item, "mp_id": "s", "content_html": body} for item in ("a1", "a2")), {"exhausted": True}, "fake")
        with tempfile.TemporaryDirectory() as folder:
            store = LocalContentStore(folder)
            jobs = JobRepository(factory)
            jobs.enqueue(workspace_id="w", provider="fake", source_id="s", account_id="a", idempotency_key="body", due_at=now)
            worker = CollectionWorker(session_factory=factory, jobs=jobs, rate_limits=RateLimitRepository(factory),
                                      adapters={"fake": Provider()}, content_store=store)
            self.assertEqual(worker.run_once(now=now), "completed")
            with factory() as session:
                pointers = list(session.scalars(select(ArticleContentBlob)))
                self.assertEqual(len(pointers), 2)
                self.assertEqual(pointers[0].object_key, pointers[1].object_key)
                self.assertEqual(session.query(SearchDocument).count(), 2)
                article = session.get(Article, "a1")
                article.content = article.content_html = None
                session.commit()
                detail = ArticleService.get_article(session, workspace_id="w", user_id="u", article_id="a1",
                                                     content_store_factory=lambda: store)
                self.assertEqual(detail["content_status"], "stored")
                self.assertEqual(detail["content_html"], body)
                class Corrupt:
                    def get(self, key):
                        return b"wrong body"
                missing = ArticleService.get_article(session, workspace_id="w", user_id="u", article_id="a1",
                                                      content_store_factory=Corrupt)
                self.assertEqual(missing["content_status"], "unavailable")
                self.assertIn("元数据", SingleArticleExporter().export(missing, "md").content.decode())
        engine.dispose()


if __name__ == "__main__":
    unittest.main()
