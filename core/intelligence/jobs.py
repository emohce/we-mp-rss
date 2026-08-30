from __future__ import annotations

import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Callable

from sqlalchemy import and_, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from core.models.article import Article

from .idempotency import normalize_idempotency_key
from .models import (
    CollectionJob,
    CollectorCursor,
    OutboxEvent,
    WorkflowJob,
    Workspace,
    WorkspaceArticle,
    WorkspaceSubscription,
    new_id,
    utcnow,
)


@dataclass(frozen=True)
class ClaimedJob:
    id: str
    lease_token: str
    workspace_id: str
    account_id: str | None
    provider: str
    source_id: str
    kind: str
    payload: dict
    attempts: int
    max_attempts: int


class JobRepository:
    def __init__(self, session_factory: Callable[[], Session]):
        self.session_factory = session_factory

    def enqueue(
        self,
        *,
        workspace_id: str,
        provider: str,
        source_id: str,
        idempotency_key: str,
        kind: str = "discover",
        account_id: str | None = None,
        payload: dict | None = None,
        priority: int = 0,
        due_at: datetime | None = None,
    ) -> tuple[CollectionJob, bool]:
        normalized_key = normalize_idempotency_key(idempotency_key, 160)
        with self.session_factory() as session:
            existing = session.scalar(
                select(CollectionJob).where(CollectionJob.idempotency_key == normalized_key)
            )
            if existing:
                return existing, False
            job = CollectionJob(
                workspace_id=workspace_id,
                account_id=account_id,
                provider=provider,
                source_id=source_id,
                kind=kind,
                idempotency_key=normalized_key,
                payload=payload or {},
                priority=priority,
                due_at=due_at or utcnow(),
            )
            session.add(job)
            try:
                session.commit()
            except IntegrityError:
                session.rollback()
                existing = session.scalar(
                    select(CollectionJob).where(CollectionJob.idempotency_key == normalized_key)
                )
                if existing:
                    return existing, False
                raise
            session.refresh(job)
            return job, True

    def claim_next(self, *, lease_seconds: int = 120, now: datetime | None = None) -> ClaimedJob | None:
        now = now or utcnow()
        for _ in range(3):
            with self.session_factory() as session:
                session.execute(update(CollectionJob).where(
                    CollectionJob.state == "running", CollectionJob.lease_expires_at <= now,
                    CollectionJob.attempts >= CollectionJob.max_attempts,
                ).values(state="failed", lease_token="", lease_expires_at=None,
                         last_error_code="lease_exhausted", updated_at=now))
                session.commit()
                candidate_id = session.scalar(
                    select(CollectionJob.id)
                    .where(
                        CollectionJob.due_at <= now,
                        CollectionJob.attempts < CollectionJob.max_attempts,
                        or_(
                            CollectionJob.state.in_(["queued", "retry"]),
                            and_(
                                CollectionJob.state == "running",
                                CollectionJob.lease_expires_at.is_not(None),
                                CollectionJob.lease_expires_at <= now,
                            ),
                        ),
                    )
                    .order_by(CollectionJob.priority.desc(), CollectionJob.due_at, CollectionJob.created_at)
                    .limit(1)
                )
                if not candidate_id:
                    return None
                token = secrets.token_urlsafe(32)
                result = session.execute(
                    update(CollectionJob)
                    .where(
                        CollectionJob.id == candidate_id,
                        CollectionJob.due_at <= now,
                        CollectionJob.attempts < CollectionJob.max_attempts,
                        or_(
                            CollectionJob.state.in_(["queued", "retry"]),
                            and_(
                                CollectionJob.state == "running",
                                CollectionJob.lease_expires_at <= now,
                            ),
                        ),
                    )
                    .values(
                        state="running",
                        attempts=CollectionJob.attempts + 1,
                        lease_token=token,
                        lease_expires_at=now + timedelta(seconds=max(10, lease_seconds)),
                        updated_at=now,
                    )
                )
                if result.rowcount != 1:
                    session.rollback()
                    continue
                session.commit()
                job = session.get(CollectionJob, candidate_id)
                if not job:
                    return None
                return ClaimedJob(
                    id=job.id,
                    lease_token=token,
                    workspace_id=job.workspace_id,
                    account_id=job.account_id,
                    provider=job.provider,
                    source_id=job.source_id,
                    kind=job.kind,
                    payload=job.payload or {},
                    attempts=job.attempts,
                    max_attempts=job.max_attempts,
                )
        return None

    def defer(self, claimed: ClaimedJob, *, due_at: datetime, error_code: str) -> bool:
        """Waiting on our own budget/source lease is not a provider failure."""
        with self.session_factory() as session:
            result = session.execute(update(CollectionJob).where(
                CollectionJob.id == claimed.id, CollectionJob.state == "running",
                CollectionJob.lease_token == claimed.lease_token,
            ).values(state="queued", attempts=max(0, claimed.attempts - 1), due_at=due_at,
                     lease_token="", lease_expires_at=None, last_error_code=error_code,
                     last_error_message="local admission deferred"))
            session.commit()
            return result.rowcount == 1

    def complete_page(
        self,
        *,
        job_id: str,
        lease_token: str,
        account_id: str,
        next_cursor: dict,
        article_ids: list[str],
        ingestion_source: str,
    ) -> None:
        """Legacy explicit cursor API. Runtime collection uses CollectionState."""

        with self.session_factory() as session:
            job = session.scalar(
                select(CollectionJob).where(
                    CollectionJob.id == job_id,
                    CollectionJob.state == "running",
                    CollectionJob.lease_token == lease_token,
                    CollectionJob.lease_expires_at > utcnow(),
                )
            )
            if not job:
                raise ValueError("job lease is no longer valid")
            if article_ids:
                persisted = set(
                    session.scalars(select(Article.id).where(Article.id.in_(article_ids))).all()
                )
                missing = set(article_ids) - persisted
                if missing:
                    raise ValueError("cursor cannot advance before every article is persisted")
                target_workspace_ids = set(
                    session.scalars(
                        select(WorkspaceSubscription.workspace_id).where(
                            WorkspaceSubscription.provider == job.provider,
                            WorkspaceSubscription.source_id == job.source_id,
                            WorkspaceSubscription.status == "active",
                        )
                    ).all()
                )
                target_workspace_ids.add(job.workspace_id)
                existing_links = set(
                    session.execute(
                        select(WorkspaceArticle.workspace_id, WorkspaceArticle.article_id).where(
                            WorkspaceArticle.workspace_id.in_(target_workspace_ids),
                            WorkspaceArticle.article_id.in_(article_ids),
                        )
                    ).all()
                )
                for workspace_id in target_workspace_ids:
                    for article_id in article_ids:
                        if (workspace_id, article_id) not in existing_links:
                            session.add(
                                WorkspaceArticle(
                                    workspace_id=workspace_id,
                                    article_id=article_id,
                                    source_id=job.source_id,
                                    ingestion_source=ingestion_source,
                                )
                            )
            else:
                target_workspace_ids = {job.workspace_id}

            cursor = session.scalar(
                select(CollectorCursor).where(
                    CollectorCursor.account_id == account_id,
                    CollectorCursor.source_id == job.source_id,
                )
            )
            if cursor is None:
                cursor = CollectorCursor(
                    account_id=account_id,
                    source_id=job.source_id,
                    cursor=next_cursor,
                    version=1,
                    last_persisted_at=utcnow(),
                )
                session.add(cursor)
            else:
                cursor.cursor = next_cursor
                cursor.version += 1
                cursor.last_persisted_at = utcnow()
            job.state = "completed"
            job.lease_token = ""
            job.lease_expires_at = None
            job.updated_at = utcnow()
            for workspace_id in target_workspace_ids:
                workspace = session.get(Workspace, workspace_id)
                for article_id in article_ids:
                    workflow_key = f"article-analysis:{workspace_id}:{article_id}:v1"
                    if session.scalar(
                        select(WorkflowJob.id).where(WorkflowJob.idempotency_key == workflow_key)
                    ) is None:
                        session.add(
                            WorkflowJob(
                                workspace_id=workspace_id,
                                user_id=workspace.owner_user_id if workspace else "",
                                kind="article_analysis",
                                payload={"article_id": article_id},
                                idempotency_key=workflow_key,
                                priority=10,
                            )
                        )
            session.add(
                OutboxEvent(
                    workspace_id=job.workspace_id,
                    event_type="collection.page.persisted",
                    aggregate_type="collection_job",
                    aggregate_id=job.id,
                    payload={"article_ids": article_ids, "source_id": job.source_id},
                    idempotency_key=f"collection-page:{job.id}:{cursor.version}",
                )
            )
            session.commit()

    def retry(
        self,
        *,
        job_id: str,
        lease_token: str,
        due_at: datetime,
        error_code: str,
        error_message: str,
    ) -> bool:
        with self.session_factory() as session:
            result = session.execute(
                update(CollectionJob)
                .where(
                    CollectionJob.id == job_id,
                    CollectionJob.state == "running",
                    CollectionJob.lease_token == lease_token,
                )
                .values(
                    state="retry",
                    due_at=due_at,
                    lease_token="",
                    lease_expires_at=None,
                    last_error_code=error_code[:80],
                    last_error_message=error_message[:500],
                    updated_at=utcnow(),
                )
            )
            session.commit()
            return result.rowcount == 1

    def fail(self, *, job_id: str, lease_token: str, error_code: str, error_message: str) -> bool:
        with self.session_factory() as session:
            result = session.execute(
                update(CollectionJob)
                .where(
                    CollectionJob.id == job_id,
                    CollectionJob.state == "running",
                    CollectionJob.lease_token == lease_token,
                )
                .values(
                    state="failed",
                    lease_token="",
                    lease_expires_at=None,
                    last_error_code=error_code[:80],
                    last_error_message=error_message[:500],
                    updated_at=utcnow(),
                )
            )
            session.commit()
            return result.rowcount == 1
