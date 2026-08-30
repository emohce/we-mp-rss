from __future__ import annotations

import secrets
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from typing import Callable

from sqlalchemy import and_, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .jobs import JobRepository
from .idempotency import normalize_idempotency_key
from .models import (
    CollectorAccount,
    OutboxEvent,
    WorkflowJob,
    WorkspaceMembership,
    WorkspaceSubscription,
    utcnow,
)
from .scheduling import DEFAULT_SCHEDULE
from .services import AnalysisService, DigestService, FeedbackService


@dataclass(frozen=True)
class ClaimedWorkflowJob:
    id: str
    lease_token: str
    workspace_id: str
    user_id: str
    kind: str
    payload: dict
    attempts: int
    max_attempts: int


class WorkflowJobRepository:
    def __init__(self, session_factory: Callable[[], Session]):
        self.session_factory = session_factory

    def enqueue(
        self,
        *,
        workspace_id: str,
        user_id: str,
        kind: str,
        payload: dict,
        idempotency_key: str,
        due_at: datetime,
        priority: int = 0,
    ) -> tuple[WorkflowJob, bool]:
        normalized_key = normalize_idempotency_key(idempotency_key, 180)
        with self.session_factory() as session:
            existing = session.scalar(
                select(WorkflowJob).where(WorkflowJob.idempotency_key == normalized_key)
            )
            if existing:
                return existing, False
            job = WorkflowJob(
                workspace_id=workspace_id,
                user_id=user_id,
                kind=kind,
                payload=payload,
                idempotency_key=normalized_key,
                due_at=due_at,
                priority=priority,
            )
            session.add(job)
            try:
                session.commit()
            except IntegrityError:
                session.rollback()
                existing = session.scalar(
                    select(WorkflowJob).where(WorkflowJob.idempotency_key == normalized_key)
                )
                if existing:
                    return existing, False
                raise
            session.refresh(job)
            return job, True

    def claim_next(
        self,
        *,
        now: datetime | None = None,
        lease_seconds: int = 120,
    ) -> ClaimedWorkflowJob | None:
        now = now or utcnow()
        for _ in range(3):
            with self.session_factory() as session:
                job_id = session.scalar(
                    select(WorkflowJob.id)
                    .where(
                        WorkflowJob.due_at <= now,
                        WorkflowJob.attempts < WorkflowJob.max_attempts,
                        or_(
                            WorkflowJob.state.in_(["queued", "retry"]),
                            and_(
                                WorkflowJob.state == "running",
                                WorkflowJob.lease_expires_at.is_not(None),
                                WorkflowJob.lease_expires_at <= now,
                            ),
                        ),
                    )
                    .order_by(WorkflowJob.priority.desc(), WorkflowJob.due_at, WorkflowJob.created_at)
                    .limit(1)
                )
                if not job_id:
                    return None
                token = secrets.token_urlsafe(32)
                result = session.execute(
                    update(WorkflowJob)
                    .where(
                        WorkflowJob.id == job_id,
                        or_(
                            WorkflowJob.state.in_(["queued", "retry"]),
                            and_(
                                WorkflowJob.state == "running",
                                WorkflowJob.lease_expires_at <= now,
                            ),
                        ),
                    )
                    .values(
                        state="running",
                        attempts=WorkflowJob.attempts + 1,
                        lease_token=token,
                        lease_expires_at=now + timedelta(seconds=max(10, lease_seconds)),
                        updated_at=now,
                    )
                )
                if result.rowcount != 1:
                    session.rollback()
                    continue
                session.commit()
                job = session.get(WorkflowJob, job_id)
                if job is None:
                    return None
                return ClaimedWorkflowJob(
                    id=job.id,
                    lease_token=token,
                    workspace_id=job.workspace_id,
                    user_id=job.user_id,
                    kind=job.kind,
                    payload=job.payload or {},
                    attempts=job.attempts,
                    max_attempts=job.max_attempts,
                )
        return None

    def complete(self, job: ClaimedWorkflowJob) -> bool:
        with self.session_factory() as session:
            stored = session.scalar(
                select(WorkflowJob).where(
                    WorkflowJob.id == job.id,
                    WorkflowJob.state == "running",
                    WorkflowJob.lease_token == job.lease_token,
                )
            )
            if stored is None:
                return False
            stored.state = "completed"
            stored.completed_at = utcnow()
            stored.lease_token = ""
            stored.lease_expires_at = None
            stored.last_error = ""
            event_key = f"workflow-completed:{stored.id}"
            session.add(
                OutboxEvent(
                    workspace_id=stored.workspace_id,
                    event_type=f"workflow.{stored.kind}.completed",
                    aggregate_type="workflow_job",
                    aggregate_id=stored.id,
                    payload={"job_id": stored.id, "kind": stored.kind},
                    idempotency_key=event_key,
                )
            )
            session.commit()
            return True

    def retry_or_fail(self, job: ClaimedWorkflowJob, error: str, *, now: datetime | None = None) -> bool:
        now = now or utcnow()
        with self.session_factory() as session:
            stored = session.scalar(
                select(WorkflowJob).where(
                    WorkflowJob.id == job.id,
                    WorkflowJob.state == "running",
                    WorkflowJob.lease_token == job.lease_token,
                )
            )
            if stored is None:
                return False
            if stored.attempts >= stored.max_attempts:
                stored.state = "failed"
            else:
                stored.state = "retry"
                stored.due_at = now + timedelta(minutes=min(60, 5 * stored.attempts))
            stored.lease_token = ""
            stored.lease_expires_at = None
            stored.last_error = error[:500]
            session.commit()
            return True


def _naive_utc(value: datetime) -> datetime:
    return value.astimezone(timezone.utc).replace(tzinfo=None)


class DailyAutomationScheduler:
    """Materialize one day's collection and user workflows as durable jobs."""

    def __init__(
        self,
        *,
        session_factory: Callable[[], Session],
        collection_jobs: JobRepository,
        workflow_jobs: WorkflowJobRepository,
    ):
        self.session_factory = session_factory
        self.collection_jobs = collection_jobs
        self.workflow_jobs = workflow_jobs

    def schedule_day(self, day: date, *, include_collection: bool = True) -> dict[str, int]:
        moments = DEFAULT_SCHEDULE.moments(day)
        collection_due = _naive_utc(moments["collect"])
        digest_due = _naive_utc(moments["digest"])
        preference_due = _naive_utc(datetime.combine(day, time(8, 10), DEFAULT_SCHEDULE.timezone))
        with self.session_factory() as session:
            subscriptions = session.scalars(
                select(WorkspaceSubscription).where(WorkspaceSubscription.status == "active")
            ).all()
            memberships = [
                (membership.workspace_id, membership.user_id)
                for membership in session.scalars(select(WorkspaceMembership)).all()
            ]

            scheduled_collection = 0
            scheduled_sources: set[tuple[str, str, str]] = set()
            for subscription in subscriptions if include_collection else []:
                account = session.scalar(
                    select(CollectorAccount)
                    .where(
                        CollectorAccount.provider == subscription.provider,
                        CollectorAccount.status.in_(["healthy", "probe"]),
                        or_(
                            CollectorAccount.workspace_id == subscription.workspace_id,
                            CollectorAccount.workspace_id.is_(None),
                        ),
                    )
                    .order_by(CollectorAccount.workspace_id.is_not(None))
                    .limit(1)
                )
                account_key = account.id if account else "unconfigured"
                source_key = (account_key, subscription.provider, subscription.source_id)
                if source_key in scheduled_sources:
                    subscription.next_due_at = _naive_utc(
                        DEFAULT_SCHEDULE.moments(day + timedelta(days=1))["collect"]
                    )
                    continue
                scheduled_sources.add(source_key)
                _, created = self.collection_jobs.enqueue(
                    workspace_id=subscription.workspace_id,
                    provider=subscription.provider,
                    source_id=subscription.source_id,
                    account_id=account.id if account else None,
                    kind="head",
                    idempotency_key=(
                        f"daily-collection:{account_key}:{subscription.provider}:"
                        f"{subscription.source_id}:{day.isoformat()}"
                    ),
                    payload={"page_budget": 3, "schedule_date": day.isoformat()},
                    priority=20,
                    due_at=collection_due,
                )
                scheduled_collection += int(created)
                subscription.next_due_at = _naive_utc(
                    DEFAULT_SCHEDULE.moments(day + timedelta(days=1))["collect"]
                )
            session.commit()

        scheduled_digest = 0
        scheduled_preference = 0
        for workspace_id, user_id in memberships:
            _, digest_created = self.workflow_jobs.enqueue(
                workspace_id=workspace_id,
                user_id=user_id,
                kind="daily_digest",
                payload={"digest_date": day.isoformat()},
                idempotency_key=(
                    f"daily-digest:{workspace_id}:{user_id}:{day.isoformat()}"
                ),
                due_at=digest_due,
                priority=20,
            )
            scheduled_digest += int(digest_created)
            _, preference_created = self.workflow_jobs.enqueue(
                workspace_id=workspace_id,
                user_id=user_id,
                kind="preference_refresh",
                payload={"window_days": 90},
                idempotency_key=(
                    f"preference-refresh:{workspace_id}:{user_id}:{day.isoformat()}"
                ),
                due_at=preference_due,
                priority=5,
            )
            scheduled_preference += int(preference_created)
        return {
            "collection_jobs": scheduled_collection,
            "digest_jobs": scheduled_digest,
            "preference_jobs": scheduled_preference,
        }


class WorkflowWorker:
    def __init__(
        self,
        *,
        session_factory: Callable[[], Session],
        repository: WorkflowJobRepository,
    ):
        self.session_factory = session_factory
        self.repository = repository

    def run_once(self, *, now: datetime | None = None) -> str:
        claimed = self.repository.claim_next(now=now)
        if claimed is None:
            return "idle"
        try:
            with self.session_factory() as session:
                if claimed.kind == "daily_digest":
                    DigestService.generate(
                        session,
                        workspace_id=claimed.workspace_id,
                        user_id=claimed.user_id,
                        digest_date=date.fromisoformat(str(claimed.payload["digest_date"])),
                    )
                elif claimed.kind == "article_analysis":
                    AnalysisService().analyze_article(
                        session,
                        workspace_id=claimed.workspace_id,
                        user_id=claimed.user_id,
                        article_id=str(claimed.payload["article_id"]),
                    )
                elif claimed.kind == "preference_refresh":
                    FeedbackService.propose_preferences(
                        session,
                        workspace_id=claimed.workspace_id,
                        user_id=claimed.user_id,
                    )
                else:
                    raise ValueError("unsupported workflow kind")
            self.repository.complete(claimed)
            return "completed"
        except Exception as exc:
            self.repository.retry_or_fail(claimed, type(exc).__name__, now=now)
            return "retry"
