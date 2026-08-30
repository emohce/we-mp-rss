import json
import unittest
from datetime import datetime, timedelta
from unittest.mock import patch

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from core.models.article import Article
from core.models.base import Base
from .connectors import (UsagePolicy, capabilities, canonical_url, import_feed, parse_feed,
                         parse_supsub_output, preview_feed, reserve_usage, supsub_read_plan)
from .events import NullPublisher
from .models import (CollectionJob, CollectorAccount, ConnectorIdentity, ConnectorUsage, OutboxEvent,
                     RateLimitLedger, SearchDocument, SourceCheckpoint, WorkflowJob, Workspace,
                     WorkspaceArticle, WorkspaceMembership, WorkspaceSubscription, utcnow)
from .operations import operations_snapshot
from .outbox import OutboxDispatcher, OutboxRepository
from .services import ArticleService
from .settings import InfrastructureSettings
from .workflow import WorkflowJobRepository, WorkflowWorker


def json_feed(identity="one", url="https://example.test/one", title="AI 开源工具", date="2026-08-29T09:00:00+08:00"):
    return json.dumps({"version": "https://jsonfeed.org/version/1.1", "title": "Fixture",
                       "items": [{"id": identity, "url": url, "title": title, "date_published": date,
                                  "content_html": "<h2>本地正文</h2><p>量子计算</p>"}]}, ensure_ascii=False)


class ConnectorContractTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite://")
        tables = [table for name, table in Base.metadata.tables.items() if name == "articles" or name.startswith("int_")]
        Base.metadata.create_all(self.engine, tables=tables)
        self.factory = sessionmaker(self.engine, expire_on_commit=False)
        with self.factory() as session:
            session.add_all([Workspace(id="w1", name="one", slug="one", owner_user_id="u1"), Workspace(id="w2", name="two", slug="two", owner_user_id="u2")])
            session.flush()
            session.add_all([WorkspaceMembership(workspace_id="w1", user_id="u1"), WorkspaceMembership(workspace_id="w2", user_id="u2")])
            session.commit()

    def tearDown(self):
        self.engine.dispose()

    def ingest(self, content=None, workspace="w1", user="u1", request_id="request-fixture", provider="local-feed", policy=UsagePolicy()):
        with self.factory() as session:
            return import_feed(session, workspace_id=workspace, user_id=user, provider=provider,
                               source_key="source-a", content=content or json_feed(), request_id=request_id, policy=policy)

    def test_rss_atom_json_feed_share_bounded_normalization_without_network(self):
        rss = '<rss version="2.0" xmlns:content="http://purl.org/rss/1.0/modules/content/"><channel><item><guid>one</guid><title>RSS</title><link>https://example.test/one?utm_source=x</link><pubDate>Sat, 29 Aug 2026 01:00:00 GMT</pubDate><content:encoded>&lt;p&gt;正文&lt;/p&gt;</content:encoded></item></channel></rss>'
        atom = '<feed xmlns="http://www.w3.org/2005/Atom"><entry><id>one</id><title>Atom</title><link href="https://example.test/one"/><updated>2026-08-29T01:00:00Z</updated><content type="html">&lt;p&gt;正文&lt;/p&gt;</content></entry></feed>'
        with patch('requests.get', side_effect=AssertionError('offline only')), patch('subprocess.run', side_effect=AssertionError('no CLI execution')):
            parsed = [parse_feed(value) for value in (rss, atom, json_feed())]
        self.assertEqual([kind for kind, _ in parsed], ["rss", "atom", "json-feed"])
        self.assertEqual(len({rows[0].published_at for _, rows in parsed}), 1)
        self.assertEqual(parsed[0][1][0].url, "https://example.test/one")
        self.assertEqual(parsed[1][1][0].body, "<p>正文</p>")

    def test_invalid_dates_xml_entities_remote_content_and_oversized_windows_fail_closed(self):
        dangerous = ['<!DOCTYPE rss [<!ENTITY x SYSTEM "file:///etc/passwd">]><rss>&x;</rss>',
                     '<feed xmlns="http://www.w3.org/2005/Atom"><entry><id>x</id><content src="https://example.test/body"/></entry></feed>',
                     'x' * (1024 * 1024 + 1), json_feed(date="2026-08-29T09:00:00"),
                     json.dumps({"version": "https://jsonfeed.org/version/1.1", "items": [{"id": str(i)} for i in range(101)]})]
        for content in dangerous:
            with self.subTest(content=content[:30]), self.assertRaises(ValueError):
                parse_feed(content)
        _, missing = parse_feed(json_feed(date=""))
        self.assertIsNone(missing[0].published_at)

    def test_opml_only_previews_groups_and_redacts_capability_urls(self):
        content = '<opml version="2.0"><body><outline text="科技"><outline text="公开" xmlUrl="https://example.test/feed.xml"/><outline text="私有" xmlUrl="https://example.test/feed?k=secret"/></outline></body></opml>'
        result = preview_feed(content)
        self.assertFalse(result["can_import"])
        self.assertEqual(result["entries"][0]["groups"], ["科技"])
        self.assertEqual(result["entries"][1]["public_url"], "")
        self.assertNotIn("secret", json.dumps(result).replace('requires_secret_ref', 'redacted'))
        with self.assertRaises(ValueError):
            self.ingest(content)
        with self.factory() as session:
            self.assertEqual(session.query(WorkspaceSubscription).count(), 0)

    def test_import_idempotency_identity_mapping_and_canonical_fields_are_preserved(self):
        first = self.ingest()
        self.assertEqual(first["imported"], 1)
        self.assertEqual(self.ingest()["status"], "already_completed")
        # Another supplier's identity may point at the same canonical article
        # only within this workspace, without overwriting its existing body/title.
        second = self.ingest(json_feed(identity="supplier-id", title="Do not overwrite"), provider="supsub", request_id="supplier-request")
        self.assertEqual(second["imported"], 0)
        with self.factory() as session:
            self.assertEqual(session.query(Article).count(), 1)
            self.assertEqual(session.query(ConnectorIdentity).count(), 2)
            self.assertEqual(session.scalar(select(Article)).title, "AI 开源工具")
            self.assertIn("量子计算", session.scalar(select(SearchDocument)).search_text)
            self.assertEqual(session.query(OutboxEvent).count(), 2)
            self.assertEqual(session.query(WorkflowJob).count(), 1)
        with self.assertRaises(ValueError):
            self.ingest(json_feed(title="changed input"))

    def test_import_never_reuses_another_workspace_private_article_or_title(self):
        self.ingest()
        self.ingest(workspace="w2", user="u2")
        with self.factory() as session:
            self.assertEqual(session.query(Article).count(), 2)
            rows = list(session.scalars(select(WorkspaceArticle)))
            self.assertNotEqual(rows[0].article_id, rows[1].article_id)
        with self.assertRaises(ValueError):
            self.ingest(workspace="w2", user="u1", request_id="denied-fixture")

    def test_imported_articles_reach_the_existing_local_analysis_worker(self):
        self.ingest()
        worker = WorkflowWorker(session_factory=self.factory, repository=WorkflowJobRepository(self.factory))
        self.assertEqual(worker.run_once(), "completed")
        with self.factory() as session:
            listed = ArticleService.list_articles(session, workspace_id="w1", user_id="u1", search="量子计算")
            self.assertEqual(listed["total"], 1)
            self.assertTrue(listed["items"][0]["topics"])

    def test_budget_denial_and_bad_page_are_atomic(self):
        self.ingest(policy=UsagePolicy(daily_units=1))
        with self.assertRaisesRegex(ValueError, "budget exhausted"):
            self.ingest(json_feed(identity="two", url="https://example.test/two"), request_id="next-fixture", policy=UsagePolicy(daily_units=1))
        malformed = json.loads(json_feed()); malformed["items"].append({"id": "bad", "url": "javascript:bad"})
        with self.assertRaises(ValueError):
            self.ingest(json.dumps(malformed), request_id="malformed-page")
        with self.factory() as session:
            self.assertEqual(session.query(Article).count(), 1)
            self.assertEqual(session.query(ConnectorUsage).count(), 1)

    def test_billable_default_denial_and_uncertain_spend_cannot_be_retried(self):
        args = dict(workspace_id="w1", provider="paid-api", operation="paid-page", request_id="paid-fixture", fingerprint="same", billable=True)
        with self.factory() as session:
            with self.assertRaisesRegex(ValueError, "billable operation denied"):
                reserve_usage(session, **args)
            receipt, fresh = reserve_usage(session, **args, policy=UsagePolicy(allow_billable=True))
            self.assertTrue(fresh)
            receipt.status = "unknown"; session.commit()
            with self.assertRaisesRegex(ValueError, "unresolved"):
                reserve_usage(session, **args, policy=UsagePolicy(allow_billable=True))

    def test_read_only_supsub_argv_is_not_a_shell_or_installation_path(self):
        plan = supsub_read_plan("/fixture/supsub", "sub.contents", source_id=123)
        self.assertIn("--all", plan["argv"])
        self.assertIn("json", plan["argv"])
        self.assertFalse(plan["execute"])
        self.assertEqual(plan["environment"]["SUPSUB_DISABLE_AUTOUPDATER"], "1")
        for operation in ("sub.mark-read", "sub.add", "deepread.run", "deepread.share", "auth.login", "update", "mp.search"):
            with self.subTest(operation=operation), self.assertRaises(ValueError):
                supsub_read_plan("/fixture/supsub", operation)
        with self.assertRaises(ValueError):
            supsub_read_plan("supsub", "sub.list")
        with self.assertRaises(ValueError):
            supsub_read_plan("/fixture/supsub", "search", query="--api-url=unsafe")
        query = "AI; $(do-not-run)"
        self.assertEqual(supsub_read_plan("/fixture/supsub", "search", query=query)["argv"][-1], query)

    def test_supplier_envelope_and_registry_do_not_claim_runtime_verification(self):
        self.assertEqual(parse_supsub_output('{"success":true,"data":[{"contentId":1}]}'), [{"contentId": 1}])
        for output in ('banner\n{}', '{"success":false,"error":{"token":"private"}}', '{"data":[]}'):
            with self.assertRaises(ValueError):
                parse_supsub_output(output)
        for capability in capabilities():
            self.assertEqual(capability["connection_status"], "unverified")
            self.assertFalse(capability["automatic_fallback"])
        self.assertFalse(preview_feed(json_feed(), "wechat2rss")["can_import"])
        with self.assertRaises(ValueError):
            self.ingest(provider="wechat2rss")

    def test_canonical_url_rejects_secret_and_private_targets(self):
        for url in ("file:///private", "http://127.0.0.1/", "http://[::1]/", "https://localhost/", "https://user:password@example.test/", "https://example.test/?token=hidden"):
            with self.subTest(url=url), self.assertRaises(ValueError):
                canonical_url(url)
        self.assertEqual(canonical_url("https://EXAMPLE.test:443/read?mid=1&utm_source=x#heading"), "https://example.test/read?mid=1")

    def test_import_html_is_safe_for_legacy_views_as_well_as_the_reader(self):
        payload = json.loads(json_feed())
        payload["items"][0]["content_html"] = '<html><body><p id="clobber" onclick="evil()">正文</p><script>evil()</script><meta http-equiv="refresh" content="0;url=https://example.test"/><img src="https://example.test/tracker"/><a href="javascript:evil()">链接</a><svg><script>evil()</script></svg></body></html>'
        self.ingest(json.dumps(payload))
        with self.factory() as session:
            body = session.scalar(select(Article)).content_html
            self.assertIn("正文", body)
            for forbidden in ("<script", "<meta", "<svg", "onclick", "clobber", "javascript:", "https://example.test/tracker"):
                self.assertNotIn(forbidden, body)

    def test_null_transport_retains_event_without_claim_or_delivery(self):
        repository = OutboxRepository(self.factory)
        event, _ = repository.enqueue(event_type="fixture", aggregate_type="article", aggregate_id="one", idempotency_key="fixture", workspace_id="w1")
        self.assertFalse(OutboxDispatcher(repository, NullPublisher()).dispatch_once())
        with self.factory() as session:
            stored = session.get(OutboxEvent, event.id)
            self.assertEqual(stored.state, "pending")
            self.assertEqual(stored.attempts, 0)
            self.assertIsNone(stored.delivered_at)

    def test_operations_show_shared_source_but_not_other_private_jobs_or_secrets(self):
        with self.factory() as session:
            session.add_all([CollectorAccount(id="shared", provider="we-mp-rss", label="shared-secret", secret_ref="never-expose"),
                             CollectorAccount(id="private", workspace_id="w2", provider="fake", label="private-secret")])
            session.flush()
            session.add_all([WorkspaceSubscription(workspace_id="w1", provider="we-mp-rss", source_id="source"),
                             CollectionJob(workspace_id="w2", account_id="shared", provider="we-mp-rss", source_id="source", kind="head", idempotency_key="shared-job", last_error_code="200013", last_error_message="credential-secret"),
                             CollectionJob(workspace_id="w2", account_id="private", provider="fake", source_id="source", kind="head", idempotency_key="private-job"),
                             RateLimitLedger(account_id="shared", provider="we-mp-rss", state="cooldown", cooldown_until=utcnow() + timedelta(minutes=30)),
                             SourceCheckpoint(account_id="shared", source_id="source", mode="head", cursor={"secret": "never-return"})])
            session.commit()
            projection = operations_snapshot(session, workspace_id="w1", user_id="u1", settings=InfrastructureSettings())
            self.assertEqual(projection["collection_counts"], {"queued": 1})
            self.assertEqual(projection["recent_jobs"][0]["error_code"], "200013")
            self.assertEqual(projection["accounts"][0]["state"], "cooldown")
            self.assertIsNotNone(projection["accounts"][0]["cooldown_until"])
            self.assertEqual(len(projection["checkpoints"]), 1)
            self.assertEqual(projection["delivery_mode"], "local-retained-no-transport")
            self.assertFalse(projection["runtime_verified"])
            self.assertNotIn("secret", json.dumps(projection, default=str))

    def test_expired_outbox_leases_cannot_deliver_and_exhausted_claims_become_failed(self):
        repository = OutboxRepository(self.factory)
        event, _ = repository.enqueue(event_type="fixture", aggregate_type="article", aggregate_id="one", idempotency_key="expired", workspace_id="w1")
        claim = repository.claim_next()
        with self.factory() as session:
            row = session.get(OutboxEvent, event.id)
            row.lease_expires_at = utcnow() - timedelta(seconds=1)
            row.max_attempts = row.attempts
            session.commit()
        self.assertFalse(repository.mark_delivered(event.id, claim.lease_token))
        self.assertFalse(repository.mark_retry(event.id, claim.lease_token, "stale"))
        self.assertIsNone(repository.claim_next())
        with self.factory() as session:
            self.assertEqual(session.get(OutboxEvent, event.id).state, "failed")


if __name__ == "__main__":
    unittest.main()
