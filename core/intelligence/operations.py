"""Read-only, workspace-scoped projections; never probe configured services."""
from sqlalchemy import and_, func, or_, select
from .connectors import capabilities
from .models import (CollectionJob, CollectorAccount, ConnectorUsage, Digest, OutboxEvent,
                     RateLimitLedger, SourceCheckpoint, WorkflowJob, WorkspaceSubscription, utcnow)
from .services import TenantService
from .settings import StorageProfile


def _safe_code(value):
    if value in {"200003", "200013", "auth_invalid", "rate_limited", "network_error", "page_budget",
                 "response_too_large", "invalid_payload", "source_not_found", "provider_missing", "lease_expired",
                 "invalid_publish_page", "invalid_publish_info", "bootstrap_window", "local_budget"}:
        return value
    if isinstance(value, str) and value in {f"http_{status}" for status in range(400, 600)}:
        return value
    return "other_error" if value else ""


def operations_snapshot(session, *, workspace_id, user_id, settings, collector_configured=False, jobs_configured=False):
    TenantService.require_membership(session, workspace_id, user_id)
    # Shared jobs are visible only for sources actually subscribed here. Private
    # accounts in another workspace are never included, even with the same ID.
    subscribed = select(WorkspaceSubscription.id).where(
        WorkspaceSubscription.workspace_id == workspace_id,
        WorkspaceSubscription.source_id == CollectionJob.source_id,
        WorkspaceSubscription.provider == CollectionJob.provider,
    ).exists()
    global_account = select(CollectorAccount.id).where(CollectorAccount.id == CollectionJob.account_id,
                                                     CollectorAccount.workspace_id.is_(None)).exists()
    visible_job = or_(CollectionJob.workspace_id == workspace_id, and_(subscribed, global_account))
    collection_counts = dict(session.execute(select(CollectionJob.state, func.count()).where(visible_job).group_by(CollectionJob.state)).all())
    workflow_counts = dict(session.execute(select(WorkflowJob.state, func.count()).where(
        WorkflowJob.workspace_id == workspace_id, WorkflowJob.user_id == user_id,
    ).group_by(WorkflowJob.state)).all())
    outbox_counts = dict(session.execute(select(OutboxEvent.state, func.count()).where(
        OutboxEvent.workspace_id == workspace_id,
    ).group_by(OutboxEvent.state)).all())
    jobs = list(session.scalars(select(CollectionJob).where(visible_job).order_by(CollectionJob.updated_at.desc()).limit(20)))
    account_ids = select(CollectionJob.account_id).where(visible_job, CollectionJob.account_id.is_not(None))
    accounts = [{"provider": account.provider, "state": account.status if account.status == "disabled" else (ledger.state if ledger else account.status), "last_error": _safe_code(account.last_error_code),
                 "cooldown_until": ledger.cooldown_until if ledger else None,
                 "failure_count": ledger.failure_count if ledger else 0}
                for account, ledger in session.execute(select(CollectorAccount, RateLimitLedger).outerjoin(
                    RateLimitLedger, and_(RateLimitLedger.account_id == CollectorAccount.id, RateLimitLedger.provider == CollectorAccount.provider),
                ).where(CollectorAccount.id.in_(account_ids)).limit(30))]
    checkpoints = [{"source_id": checkpoint.source_id, "mode": checkpoint.mode, "version": checkpoint.version,
                    "last_success_at": checkpoint.last_success_at}
                   for checkpoint in session.scalars(select(SourceCheckpoint).where(
                       SourceCheckpoint.account_id.in_(account_ids),
                       SourceCheckpoint.source_id.in_(select(WorkspaceSubscription.source_id).where(WorkspaceSubscription.workspace_id == workspace_id)),
                   ).order_by(SourceCheckpoint.last_success_at.desc(), SourceCheckpoint.id).limit(30))]
    recent_digests = [{"date": row.digest_date, "revision": row.revision, "status": row.status, "coverage": row.coverage}
                      for row in session.scalars(select(Digest).where(Digest.workspace_id == workspace_id, Digest.user_id == user_id)
                          .order_by(Digest.digest_date.desc()).limit(7))]
    usage = [{"provider": provider, "status": status, "billable": billable, "units": units, "requests": requests}
             for provider, status, billable, units, requests in session.execute(select(
                 ConnectorUsage.provider, ConnectorUsage.status, ConnectorUsage.billable,
                 func.sum(ConnectorUsage.units), func.count(),
             ).where(ConnectorUsage.workspace_id == workspace_id)
             .group_by(ConnectorUsage.provider, ConnectorUsage.status, ConnectorUsage.billable))]
    return {"observed_at": utcnow(), "scope": "workspace", "connection_status": "not_probed",
            "configured": {"jobs": bool(jobs_configured), "collector": bool(collector_configured),
                           "redis": bool(settings.redis_url), "mqtt": bool(settings.mqtt_url)},
            "runtime_verified": False, "delivery_mode": "mqtt-configured-unverified" if settings.profile is StorageProfile.DISTRIBUTED else "local-retained-no-transport",
            "collection_counts": collection_counts, "workflow_counts": workflow_counts, "outbox_counts": outbox_counts,
            "recent_jobs": [{"id": job.id, "provider": job.provider, "source_id": job.source_id, "mode": job.kind,
                             "state": job.state, "attempts": job.attempts, "due_at": job.due_at,
                             "error_code": _safe_code(job.last_error_code)} for job in jobs],
            "accounts": accounts, "checkpoints": checkpoints, "recent_digests": recent_digests,
            "usage": usage, "usage_scope": "all-recorded-units-not-a-monetary-balance", "connectors": capabilities()}
