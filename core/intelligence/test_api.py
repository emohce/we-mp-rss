from __future__ import annotations

import os
import sys
import unittest
from datetime import date
from pathlib import Path

import requests
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, func
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


# Import the project API against an isolated in-memory configuration. This
# avoids credential writes, outbound version checks and user database access.
os.environ["DB"] = "sqlite://"
os.environ["SECRET_KEY"] = "test-only-secret-key-that-is-long-enough-for-jwt"
original_argv = sys.argv[:]
original_get = requests.get
sys.argv = [
    original_argv[0],
    "-config",
    str(Path(__file__).parents[2] / "config.example.yaml"),
]


def _offline_get(*args, **kwargs):
    raise requests.RequestException("offline contract test")


requests.get = _offline_get
try:
    from apis.intelligence import (
        _render_digest_page,
        get_intelligence_session,
        public_router,
        router,
    )
    from core.auth import get_current_user_or_ak
finally:
    requests.get = original_get
    sys.argv = original_argv

from core.models.article import Article
from core.models.base import Base
from core.models.feed import Feed

from .models import WorkspaceArticle, WorkspaceSubscription, CollectionJob
from .scheduling import DEFAULT_SCHEDULE


class IntelligenceApiContractTest(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        tables = [
            table
            for name, table in Base.metadata.tables.items()
            if name in {"articles", "feeds"} or name.startswith("int_")
        ]
        Base.metadata.create_all(self.engine, tables=tables)
        self.session_factory = sessionmaker(bind=self.engine, expire_on_commit=False)

        app = FastAPI()
        app.include_router(router, prefix="/api/v2/intelligence")
        app.include_router(public_router, prefix="/share")

        def session_override():
            with self.session_factory() as session:
                yield session

        app.dependency_overrides[get_intelligence_session] = session_override
        app.dependency_overrides[get_current_user_or_ak] = lambda: {
            "user_id": "user-a",
            "username": "alice",
            "auth_type": "test",
        }
        self.app = app
        self.client = TestClient(app)
        bootstrap = self.client.post("/api/v2/intelligence/workspaces/bootstrap")
        self.assertEqual(bootstrap.status_code, 200)
        self.assertEqual(
            bootstrap.json()["data"]["legacy_backfill"]["skipped"],
            "admin_required",
        )
        self.workspace_id = bootstrap.json()["data"]["id"]

    def tearDown(self) -> None:
        self.client.close()
        self.engine.dispose()

    def seed_article(self, article_id: str = "api-article") -> None:
        run_date = date(2026, 8, 24)
        with self.session_factory() as session:
            session.add(
                Article(
                    id=article_id,
                    mp_id="source-api",
                    title="API 人工智能日报",
                    description="AI 与开源产品",
                    content="<p>完整正文</p>",
                    content_html="<p>完整正文</p>",
                    url=f"https://example.test/{article_id}",
                    publish_time=int(DEFAULT_SCHEDULE.moments(run_date)["collect"].timestamp()),
                    status=1,
                )
            )
            session.flush()
            session.add(
                WorkspaceArticle(
                    workspace_id=self.workspace_id,
                    article_id=article_id,
                    source_id="source-api",
                )
            )
            session.commit()

    def test_article_analysis_feedback_download_digest_and_public_share(self) -> None:
        self.seed_article()
        params = {"workspace_id": self.workspace_id}
        listed = self.client.get("/api/v2/intelligence/articles", params=params)
        self.assertEqual(listed.status_code, 200)
        item = listed.json()["data"]["items"][0]
        self.assertNotIn("content", item)

        analyzed = self.client.post(
            "/api/v2/intelligence/articles/api-article/analyze", params=params
        )
        self.assertEqual(analyzed.status_code, 200)
        self.assertEqual(analyzed.json()["data"]["provider"], "heuristic")

        feedback = self.client.post(
            "/api/v2/intelligence/articles/api-article/feedback",
            params=params,
            json={"event_type": "like", "value": {"reason": "有用"}},
        )
        self.assertEqual(feedback.status_code, 200)

        detail = self.client.get(
            "/api/v2/intelligence/articles/api-article", params=params
        )
        self.assertIn("完整正文", detail.json()["data"]["content"])
        self.assertEqual(detail.json()["data"]["feedback_sentiment"], "like")

        download = self.client.get(
            "/api/v2/intelligence/articles/api-article/download",
            params={**params, "format": "md"},
        )
        self.assertEqual(download.status_code, 200)
        self.assertIn("attachment", download.headers["content-disposition"])
        self.assertIn("完整正文", download.text)

        generated = self.client.post(
            "/api/v2/intelligence/digests/2026-08-24/generate", params=params
        )
        self.assertEqual(generated.status_code, 200)
        self.assertEqual(len(generated.json()["data"]["items"]), 1)
        shared = self.client.post(
            "/api/v2/intelligence/digests/2026-08-24/share",
            params=params,
            json={"expires_in_hours": 24},
        )
        self.assertEqual(shared.status_code, 200)
        share_url = shared.json()["data"]["url"]
        page = self.client.get(share_url)
        self.assertEqual(page.status_code, 200)
        self.assertIn("2026-08-24", page.text)
        self.assertNotIn("完整正文", page.text)
        self.assertIn("Content-Security-Policy", page.headers)
        self.assertIn("修订 1", page.text)
        self.assertEqual(page.headers["cache-control"], "no-store")
        history = self.client.get("/api/v2/intelligence/digests/2026-08-24/revisions", params=params)
        self.assertEqual(history.json()["data"][0]["revision"], 1)
        revoked = self.client.post(f"/api/v2/intelligence/shares/{shared.json()['data']['id']}/revoke", params=params)
        self.assertEqual(revoked.status_code, 200)
        self.assertEqual(self.client.get(share_url).status_code, 404)

    def test_openapi_exposes_v2_contract_and_share_renderer_escapes_input(self) -> None:
        paths = self.app.openapi()["paths"]
        self.assertIn("/api/v2/intelligence/articles", paths)
        self.assertIn("/api/v2/intelligence/articles/{article_id}/download", paths)
        self.assertIn("/api/v2/intelligence/digests/{digest_date}/share", paths)

        page = _render_digest_page(
            {
                "date": "<script>alert(1)</script>",
                "title": "<img src=x onerror=alert(1)>",
                "items": [
                    {
                        "rank": 1,
                        "article": {
                            "title": "<script>bad()</script>",
                            "url": "javascript:bad()",
                            "topics": [{"name": "<b>topic</b>"}],
                        },
                    }
                ],
            }
        )
        self.assertNotIn("<script>", page)
        self.assertNotIn("javascript:bad", page)
        self.assertIn("&lt;script&gt;", page)

    def test_saved_filters_and_personal_topic_feedback_are_scoped(self):
        self.seed_article()
        params = {"workspace_id": self.workspace_id}
        feedback = self.client.post("/api/v2/intelligence/articles/api-article/feedback", params=params,
                                    json={"event_type": "topic_correction", "value": {"topics": ["新能源"]}})
        self.assertEqual(feedback.status_code, 200)
        choices = self.client.get("/api/v2/intelligence/topics", params=params).json()["data"]
        self.assertEqual(choices[0]["name"], "新能源")
        filtered = self.client.get("/api/v2/intelligence/articles", params={**params, "topic": "新能源"})
        self.assertEqual(filtered.json()["data"]["total"], 1)
        saved = self.client.post("/api/v2/intelligence/saved-filters", params=params,
                                 json={"name": "新能源", "filters": {"topic": "新能源"}}).json()["data"]
        self.assertEqual(self.client.get("/api/v2/intelligence/saved-filters", params=params).json()["data"][0]["id"], saved["id"])
        history = self.client.get("/api/v2/intelligence/feedback", params=params).json()["data"]
        self.assertEqual(history["total"], 1)
        self.assertEqual(self.client.get("/api/v2/intelligence/learning-status", params=params).json()["data"]["history_scope"], "all")
        self.assertEqual(self.client.delete(f"/api/v2/intelligence/saved-filters/{saved['id']}", params=params).status_code, 200)
        self.assertEqual(self.client.get("/api/v2/intelligence/saved-filters", params=params).json()["data"], [])

    def test_invalid_filter_and_topic_payloads_do_not_write(self):
        self.seed_article()
        params = {"workspace_id": self.workspace_id}
        invalid = self.client.post("/api/v2/intelligence/saved-filters", params=params,
                                   json={"name": "bad", "filters": {"sql": "bad"}})
        self.assertEqual(invalid.status_code, 400)
        invalid_topic = self.client.post("/api/v2/intelligence/articles/api-article/feedback", params=params,
                                         json={"event_type": "topic_correction", "value": {"topics": "bad"}})
        self.assertEqual(invalid_topic.status_code, 400)
        self.assertEqual(self.client.get("/api/v2/intelligence/feedback", params=params).json()["data"]["total"], 0)

    def test_admin_bootstrap_never_imports_and_legacy_import_is_explicit_bounded(self):
        with self.session_factory() as session:
            session.add_all([Article(id=f"legacy-{i}", mp_id="legacy", title="Legacy", status=1) for i in range(3)])
            session.commit()
        endpoint = f"/api/v2/intelligence/workspaces/{self.workspace_id}/legacy-import"
        self.assertEqual(self.client.post(endpoint, json={"confirm": True}).status_code, 404)
        self.app.dependency_overrides[get_current_user_or_ak] = lambda: {
            "user_id": "user-a", "username": "alice", "role": "admin", "auth_type": "test",
        }
        boot = self.client.post("/api/v2/intelligence/workspaces/bootstrap").json()["data"]
        self.assertTrue(boot["can_import_legacy"])
        self.assertEqual(boot["legacy_backfill"]["attached"], 0)
        self.assertEqual(boot["legacy_backfill"]["skipped"], "explicit_request_required")
        self.assertEqual(self.client.post(endpoint, json={"confirm": False}).status_code, 422)
        with self.session_factory() as session:
            self.assertEqual(session.scalar(select(func.count()).select_from(WorkspaceArticle)), 0)
        batch = self.client.post(endpoint, json={"confirm": True, "batch_size": 2}).json()["data"]
        self.assertEqual(batch, {"attached": 2, "has_more": True})
        final = self.client.post(endpoint, json={"confirm": True, "batch_size": 2}).json()["data"]
        self.assertEqual(final, {"attached": 1, "has_more": False})

    def test_local_source_selection_subscription_pause_and_idempotent_backfill(self):
        params = {"workspace_id": self.workspace_id}
        with self.session_factory() as session:
            session.add_all([Feed(id="resolved", mp_name="已解析公众号", faker_id="not-returned-secret", status=1),
                             Feed(id="unresolved", mp_name="未解析公众号", status=1)])
            session.commit()
        choices = self.client.get("/api/v2/intelligence/sources/available", params=params).json()["data"]
        self.assertEqual(choices, [{"id": "resolved", "name": "已解析公众号", "provider": "we-mp-rss"}])
        invalid = self.client.post("/api/v2/intelligence/subscriptions", params=params,
                                   json={"source_id": "unresolved", "provider": "we-mp-rss"})
        self.assertEqual(invalid.status_code, 400)
        paid = self.client.post("/api/v2/intelligence/subscriptions", params=params,
                                json={"source_id": "resolved", "provider": "paid-api"})
        self.assertEqual(paid.status_code, 400)
        with self.session_factory() as session:
            self.assertEqual(session.scalar(select(func.count()).select_from(WorkspaceSubscription)), 0)
        created = self.client.post("/api/v2/intelligence/subscriptions", params=params,
                                   json={"source_id": "resolved", "provider": "we-mp-rss"}).json()["data"]
        endpoint = f"/api/v2/intelligence/subscriptions/{created['subscription']['id']}"
        for _ in range(2):
            queued = self.client.post(endpoint + "/backfill", params=params, json={"request_id": "request-fixture", "page_budget": 3})
            self.assertEqual(queued.status_code, 200)
        with self.session_factory() as session:
            self.assertEqual(session.scalar(select(func.count()).select_from(CollectionJob).where(CollectionJob.kind == "backfill")), 1)
        paused = self.client.patch(endpoint, params=params, json={"status": "paused"}).json()["data"]
        self.assertEqual(paused["inflight_policy"], "existing_daily_cohort_is_preserved")
        self.assertEqual(self.client.post(endpoint + "/backfill", params=params, json={"request_id": "another-fixture"}).status_code, 404)

    def test_connector_preview_is_read_only_and_import_requires_admin_public_confirmation(self):
        from .test_connectors import json_feed
        params = {"workspace_id": self.workspace_id}
        preview = self.client.post("/api/v2/intelligence/connectors/preview", params=params,
                                   json={"provider": "local-feed", "content": json_feed()})
        self.assertEqual(preview.status_code, 200)
        self.assertEqual(preview.json()["data"]["count"], 1)
        with self.session_factory() as session:
            self.assertEqual(session.scalar(select(func.count()).select_from(Article)), 0)
        payload = {"provider": "local-feed", "source_key": "reading-ai", "request_id": "import-fixture",
                   "content": json_feed(), "confirm_public_content": True}
        self.assertEqual(self.client.post("/api/v2/intelligence/connectors/import", params=params, json=payload).status_code, 404)
        self.app.dependency_overrides[get_current_user_or_ak] = lambda: {
            "user_id": "user-a", "username": "alice", "role": "admin", "auth_type": "test",
        }
        self.assertEqual(self.client.post("/api/v2/intelligence/connectors/import", params=params,
                                          json={**payload, "confirm_public_content": False}).status_code, 422)
        imported = self.client.post("/api/v2/intelligence/connectors/import", params=params, json=payload)
        self.assertEqual(imported.status_code, 200)
        self.assertEqual(imported.json()["data"]["network_requests"], 0)
        self.assertEqual(imported.json()["data"]["imported"], 1)
        again = self.client.post("/api/v2/intelligence/connectors/import", params=params, json=payload)
        self.assertEqual(again.json()["data"]["status"], "already_completed")
        sources = self.client.get("/api/v2/intelligence/sources/available", params=params).json()["data"]
        self.assertEqual(sources[0]["name"], "reading-ai")
        self.assertEqual(sources[0]["provider"], "local-feed")

    def test_operation_status_exposes_configuration_not_probed_runtime(self):
        params = {"workspace_id": self.workspace_id}
        response = self.client.get("/api/v2/intelligence/operations", params=params)
        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertFalse(data["runtime_verified"])
        self.assertEqual(data["connection_status"], "not_probed")
        self.assertEqual(data["delivery_mode"], "local-retained-no-transport")
        self.assertTrue(all(not item["automatic_fallback"] for item in data["connectors"]))
        foreign = self.client.get("/api/v2/intelligence/operations", params={"workspace_id": "not-mine"})
        self.assertEqual(foreign.status_code, 404)

    def test_offline_import_is_excluded_from_legacy_repair_and_forced_fetch(self):
        import ast
        from types import SimpleNamespace
        from unittest.mock import Mock
        from core.models.base import DATA_STATUS

        # Importing jobs executes its legacy package initializer, which starts
        # Redis-backed queues. Test the exact source functions, not that runtime.
        denied_fetch = Mock(side_effect=AssertionError("no hidden provider calls"))
        namespace = {"Article": Article, "DATA_STATUS": DATA_STATUS,
                     "cfg": SimpleNamespace(get=lambda key, default=None: default),
                     "fetch_article_content": denied_fetch}
        for relative, name in (("core/article_content.py", "sync_article_content"),
                               ("jobs/fetch_no_article.py", "claim_next_article")):
            source = Path(__file__).parents[2] / relative
            tree = ast.parse(source.read_text())
            function = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == name)
            self.assertEqual(function.decorator_list, [])
            exec(compile(ast.Module(body=[function], type_ignores=[]), str(source), "exec"), namespace)
        sync_article_content = namespace["sync_article_content"]
        claim_next_article = namespace["claim_next_article"]
        self.seed_article("connector:offline")
        with self.session_factory() as session:
            article = session.get(Article, "connector:offline")
            article.content = article.content_html = ""
            article.has_content = 0
            session.commit()
            self.assertIsNone(claim_next_article(session))
            self.assertEqual(sync_article_content(session, article, force=True), (False, "offline_connector"))
            article.content = "<p>cached public content</p>"
            self.assertEqual(sync_article_content(session, article, force=True), (True, "cached"))
            denied_fetch.assert_not_called()
        self.seed_article("normal-repair")
        with self.session_factory() as session:
            article = session.get(Article, "normal-repair")
            article.has_content = 0
            session.commit()
            self.assertEqual(claim_next_article(session).id, "normal-repair")


if __name__ == "__main__":
    unittest.main()
