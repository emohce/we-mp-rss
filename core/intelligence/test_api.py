from __future__ import annotations

import os
import sys
import unittest
from datetime import date
from pathlib import Path

import requests
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
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

from .models import WorkspaceArticle
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
            if name == "articles" or name.startswith("int_")
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


if __name__ == "__main__":
    unittest.main()
