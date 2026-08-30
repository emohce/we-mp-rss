"""Fenced page transactions; head polling never consumes the backfill cursor."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import or_, select, update
from sqlalchemy.exc import IntegrityError

from core.models.article import Article

from .idempotency import normalize_idempotency_key
from .daily import queue_reconciliations
from .content import bind_objects
from .search import index_article
from .jobs import ClaimedJob
from .models import (
    CollectionJob, CollectionRun, CollectorAccount, OutboxEvent, SourceCheckpoint,
    WorkflowJob, Workspace, WorkspaceArticle, WorkspaceSubscription,
)


class LeaseLost(ValueError):
    pass


class SourceBusy(ValueError):
    pass


@dataclass(frozen=True)
class PageAttempt:
    run_id: str
    checkpoint_id: str
    version: int
    cursor: dict


class CollectionState:
    def __init__(self, session_factory):
        self.session_factory = session_factory

    @staticmethod
    def _fence_job(session, claimed: ClaimedJob, now: datetime):
        result = session.execute(
            update(CollectionJob).where(
                CollectionJob.id == claimed.id, CollectionJob.state == "running",
                CollectionJob.lease_token == claimed.lease_token,
                CollectionJob.lease_expires_at > now,
            ).values(updated_at=now)
        )
        if result.rowcount != 1:
            raise LeaseLost("collection job lease expired or was replaced")
        return session.get(CollectionJob, claimed.id)

    def begin_page(self, claimed: ClaimedJob, now: datetime) -> PageAttempt:
        mode = "backfill" if claimed.kind == "backfill" else "head"
        with self.session_factory() as session:
            job = self._fence_job(session, claimed, now)
            query = select(SourceCheckpoint).where(
                SourceCheckpoint.account_id == claimed.account_id,
                SourceCheckpoint.source_id == claimed.source_id,
                SourceCheckpoint.mode == mode,
            )
            checkpoint = session.scalar(query)
            if checkpoint is None:
                try:
                    with session.begin_nested():
                        checkpoint = SourceCheckpoint(
                            account_id=claimed.account_id, source_id=claimed.source_id, mode=mode,
                        )
                        session.add(checkpoint)
                        session.flush()
                except IntegrityError:
                    checkpoint = session.scalar(query)
                    if checkpoint is None:
                        raise
            run = session.scalar(select(CollectionRun).where(CollectionRun.job_id == job.id))
            if run is None:
                run = CollectionRun(
                    job_id=job.id, checkpoint_id=checkpoint.id, mode=mode,
                    start_version=checkpoint.version,
                    cursor=dict(checkpoint.cursor or {}) if mode == "backfill" else {},
                    boundary_ids=list(checkpoint.head_ids or []) if mode == "head" else [],
                    started_at=now,
                )
                session.add(run)
                session.flush()
            if run.start_version != checkpoint.version:
                raise LeaseLost("source checkpoint advanced by another run")
            claimed_source = session.execute(
                update(SourceCheckpoint).where(
                    SourceCheckpoint.id == checkpoint.id,
                    SourceCheckpoint.version == run.start_version,
                    or_(SourceCheckpoint.lease_token == "", SourceCheckpoint.lease_token == run.id,
                        SourceCheckpoint.lease_expires_at <= now),
                ).values(lease_token=run.id, lease_expires_at=job.lease_expires_at)
            )
            if claimed_source.rowcount != 1:
                raise SourceBusy("another run owns the source checkpoint")
            attempt = PageAttempt(run.id, checkpoint.id, run.start_version, dict(run.cursor or {}))
            session.commit()
            return attempt

    def finish_page(self, claimed, attempt, page, now: datetime, *, stored_objects=None) -> str:
        """One DB commit owns article changes, visibility, progress and events."""
        with self.session_factory() as session:
            job = self._fence_job(session, claimed, now)
            result = session.execute(
                update(SourceCheckpoint).where(
                    SourceCheckpoint.id == attempt.checkpoint_id,
                    SourceCheckpoint.lease_token == attempt.run_id,
                    SourceCheckpoint.lease_expires_at > now,
                    SourceCheckpoint.version == attempt.version,
                ).values(version=attempt.version + 1)
            )
            if result.rowcount != 1:
                raise LeaseLost("source checkpoint lease or version changed")
            checkpoint = session.get(SourceCheckpoint, attempt.checkpoint_id)
            run = session.get(CollectionRun, attempt.run_id)
            ids = self.persist_articles(session, claimed, page)
            bind_objects(session, stored_objects or {})
            targets = self.link_articles(session, job, ids, page.ingestion_source, now)
            first_page = run.pages == 0
            if first_page:
                run.head_ids = ids
            run.pages += 1
            run.article_count += len(ids)
            run.cursor = dict(page.next_cursor)
            run.start_version = attempt.version + 1
            overlap = run.mode == "head" and bool(set(ids) & set(run.boundary_ids or []))
            exhausted = not ids or bool(page.next_cursor.get("exhausted"))
            page_limit = min(20, max(1, int(job.payload.get("page_budget", 3))))
            finished = overlap or exhausted or run.pages >= page_limit
            if run.mode == "backfill":
                checkpoint.cursor = dict(page.next_cursor)
            if finished:
                complete = overlap or exhausted
                run.state = "completed" if complete else "partial"
                run.error_code = "" if complete else ("page_budget" if run.boundary_ids else "bootstrap_window")
                run.finished_at = now
                # First poll seeds a known head window but does NOT claim historical completeness.
                if run.mode == "head" and (complete or not run.boundary_ids):
                    checkpoint.head_ids = list(run.head_ids or checkpoint.head_ids or [])
                if complete:
                    checkpoint.last_success_at = now
                checkpoint.lease_token = ""
                checkpoint.lease_expires_at = None
                job.state = "completed"
                job.last_error_code = run.error_code
            else:
                if page.next_cursor == attempt.cursor:
                    raise ValueError("provider cursor did not advance")
                job.state = "queued"
                job.due_at = now + timedelta(seconds=30)
                checkpoint.lease_expires_at = job.due_at + timedelta(seconds=120)
            job.attempts = 0  # counts consecutive request failures, not successful pages
            job.lease_token = ""
            job.lease_expires_at = None
            for workspace_id in targets:
                if finished and run.state == "completed":
                    session.execute(update(WorkspaceSubscription).where(
                        WorkspaceSubscription.workspace_id == workspace_id,
                        WorkspaceSubscription.provider == job.provider,
                        WorkspaceSubscription.source_id == job.source_id,
                    ).values(last_checked_at=now))
            session.add(OutboxEvent(
                workspace_id=job.workspace_id, event_type="collection.page.persisted",
                aggregate_type="collection_run", aggregate_id=run.id,
                payload={"article_ids": ids, "source_id": job.source_id, "mode": run.mode,
                         "state": run.state, "pages": run.pages},
                idempotency_key=f"collection-page:{run.id}:{run.pages}",
            ))
            queue_reconciliations(session, workspace_ids=targets, article_ids=ids,
                                  collection_job_id=job.id, cause=f"page:{run.id}:{run.pages}", now=now)
            session.commit()
            return run.state if finished else "page_persisted"

    @staticmethod
    def persist_articles(session, claimed, page) -> list[str]:
        protected = {"id", "mp_id", "is_read", "is_favorite", "is_export", "fetch_started_at"}
        columns = {column.name for column in Article.__table__.columns} - protected
        ids = []
        for raw in page.articles:
            article_id = str(raw.get("id") or "").strip()
            if not article_id or len(article_id) > 255 or article_id in ids:
                raise ValueError("invalid or duplicate article id")
            if raw.get("mp_id") not in (None, "", claimed.source_id):
                raise ValueError("article source does not match the claimed job")
            article = session.get(Article, article_id)
            if article is not None and article.mp_id != claimed.source_id:
                raise ValueError("article identity belongs to another source")
            if article is None:
                article = Article(id=article_id, mp_id=claimed.source_id)
                session.add(article)
            for key, value in raw.items():
                if key not in columns or value is None:
                    continue
                if key in {"content", "content_html"} and not str(value).strip():
                    continue  # metadata refresh must never erase a persisted body
                setattr(article, key, value)
            ids.append(article_id)
        session.flush()
        for article_id in ids:
            index_article(session, session.get(Article, article_id))
        return ids

    @staticmethod
    def link_articles(session, job, ids, ingestion_source, now):
        account = session.get(CollectorAccount, job.account_id)
        targets = {job.workspace_id}
        if account is not None and account.workspace_id is None:
            targets.update(session.scalars(select(WorkspaceSubscription.workspace_id).where(
                WorkspaceSubscription.provider == job.provider,
                WorkspaceSubscription.source_id == job.source_id,
                WorkspaceSubscription.status == "active",
            )))
        for workspace_id in targets:
            workspace = session.get(Workspace, workspace_id)
            for article_id in ids:
                link = session.scalar(select(WorkspaceArticle.id).where(
                    WorkspaceArticle.workspace_id == workspace_id,
                    WorkspaceArticle.article_id == article_id,
                ))
                if link is None:
                    session.add(WorkspaceArticle(
                        workspace_id=workspace_id, article_id=article_id, source_id=job.source_id,
                        ingestion_source=ingestion_source[:40], added_at=now,
                    ))
                article = session.get(Article, article_id)
                fingerprint = hashlib.sha256(json.dumps(
                    [article.title, article.description, article.content, article.content_html],
                    ensure_ascii=False,
                ).encode()).hexdigest()[:20]
                key = normalize_idempotency_key(f"article-analysis:{workspace_id}:{article_id}:{fingerprint}", 180)
                if session.scalar(select(WorkflowJob.id).where(WorkflowJob.idempotency_key == key)) is None:
                    session.add(WorkflowJob(
                        workspace_id=workspace_id, user_id=workspace.owner_user_id if workspace else "",
                        kind="article_analysis", payload={"article_id": article_id},
                        idempotency_key=key, priority=10, due_at=now,
                    ))
        return targets
