"""Daily cohort snapshots and durable reconciliation scheduling (no network)."""
from datetime import date, datetime, timedelta
import hashlib
import json

from sqlalchemy import select

from core.models.article import Article
from .idempotency import normalize_idempotency_key
from .models import (AnalysisRun, CollectionJob, CollectionRun, DailyRun, DailyRunSource,
                     Digest, WorkflowJob, WorkspaceArticle, WorkspaceMembership)
from .scheduling import DEFAULT_SCHEDULE


def article_day(timestamp: int):
    published = datetime.fromtimestamp(timestamp, DEFAULT_SCHEDULE.timezone)
    day = published.date()
    if published.time() > DEFAULT_SCHEDULE.cutoff_at:
        day += timedelta(days=1)
    return day


def coverage_for(session, daily_run, article_ids=()):
    sources = []
    counts = {"expected": 0, "completed": 0, "partial": 0, "pending": 0, "failed": 0, "skipped": 0}
    for source, job, run in session.execute(
        select(DailyRunSource, CollectionJob, CollectionRun)
        .outerjoin(CollectionJob, CollectionJob.id == DailyRunSource.job_id)
        .outerjoin(CollectionRun, CollectionRun.job_id == CollectionJob.id)
        .where(DailyRunSource.daily_run_id == daily_run.id)
        .order_by(DailyRunSource.provider, DailyRunSource.source_id)
    ):
        reason = source.skipped_reason or (job.last_error_code if job else "not_scheduled")
        if source.skipped_reason:
            state = "skipped"
        elif job and job.state == "failed":
            state = "failed"
        elif job and job.state == "completed" and run and run.state in {"completed", "partial"}:
            state = run.state
            reason = run.error_code or ""
        else:
            state = "pending"
        counts["expected"] += 1
        counts[state] += 1
        sources.append({"provider": source.provider, "source_id": source.source_id,
                        "state": state, "reason": reason})
    ids = set(article_ids)
    analyzed = set(session.scalars(select(AnalysisRun.article_id).where(
        AnalysisRun.workspace_id == daily_run.workspace_id,
        AnalysisRun.status == "completed", AnalysisRun.article_id.in_(ids),
    ))) if ids else set()
    pending_analysis = set()
    failed_analysis = set()
    for job in session.scalars(select(WorkflowJob).where(
        WorkflowJob.workspace_id == daily_run.workspace_id, WorkflowJob.kind == "article_analysis",
        WorkflowJob.state != "completed",
    )):
        article_id = str((job.payload or {}).get("article_id", ""))
        if article_id in ids:
            (failed_analysis if job.state == "failed" else pending_analysis).add(article_id)
    pending_analysis.update(ids - analyzed - failed_analysis)
    return {**counts, "sources": sources, "collection_enabled": daily_run.collection_enabled,
            "analysis_pending": len(pending_analysis), "analysis_failed": len(failed_analysis),
            "complete": counts["completed"] == counts["expected"] and not pending_analysis and not failed_analysis}


def queue_reconciliations(session, *, workspace_ids=(), article_ids=(), collection_job_id=None,
                          cause: str, now: datetime, user_ids=None):
    runs = {}
    if collection_job_id:
        for run in session.scalars(select(DailyRun).join(
            DailyRunSource, DailyRunSource.daily_run_id == DailyRun.id,
        ).where(DailyRunSource.job_id == collection_job_id)):
            runs[run.id] = run
    if article_ids and workspace_ids:
        days = {article_day(int(value)).isoformat() for value in session.scalars(
            select(Article.publish_time).where(Article.id.in_(article_ids), Article.publish_time.is_not(None))
        )}
        for run in session.scalars(select(DailyRun).where(
            DailyRun.workspace_id.in_(workspace_ids), DailyRun.run_date.in_(days),
        )):
            runs[run.id] = run
    for run in runs.values():
        queue_run(session, run, cause=cause, now=now, user_ids=user_ids)


def queue_run(session, run, *, cause: str, now: datetime, user_ids=None):
    users = user_ids if user_ids is not None else session.scalars(select(WorkspaceMembership.user_id).where(
        WorkspaceMembership.workspace_id == run.workspace_id,
    ))
    for user_id in users:
        key = normalize_idempotency_key(f"digest-reconcile:{run.id}:{user_id}:{cause}", 180)
        if session.scalar(select(WorkflowJob.id).where(WorkflowJob.idempotency_key == key)) is None:
            session.add(WorkflowJob(
                workspace_id=run.workspace_id, user_id=user_id, kind="digest_reconcile",
                payload={"digest_date": run.run_date}, idempotency_key=key,
                due_at=max(now, run.publish_after), priority=15,
            ))


def queue_changed_coverage(session, run, now):
    """Hourly materialization also recovers a terminal error after publication."""
    if session.scalar(select(Digest.id).where(Digest.daily_run_id == run.id)) is None:
        return
    start_ts, end_ts = DEFAULT_SCHEDULE.article_window(date.fromisoformat(run.run_date))
    ids = list(session.scalars(select(Article.id).join(WorkspaceArticle, WorkspaceArticle.article_id == Article.id)
        .where(WorkspaceArticle.workspace_id == run.workspace_id,
               Article.publish_time >= start_ts, Article.publish_time <= end_ts)))
    signature = hashlib.sha256(json.dumps(coverage_for(session, run, ids), sort_keys=True).encode()).hexdigest()[:24]
    queue_run(session, run, cause=f"coverage:{signature}", now=now)
