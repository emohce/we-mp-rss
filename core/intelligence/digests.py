"""Revisioned, local-only daily digest generation."""
from datetime import datetime, timezone
import hashlib
import json

from sqlalchemy import select, update
from .daily import coverage_for
from .models import (DailyRun, DailyRunSource, Digest, DigestItem, DigestRevision, OutboxEvent,
                     Workspace, WorkspaceSubscription, utcnow)
from .ranking import RankingQuery
from .scheduling import DEFAULT_SCHEDULE


def generate_digest(session, *, workspace_id, user_id, digest_date, now=None):
    from .services import TenantService

    now = now or utcnow()
    TenantService.require_membership(session, workspace_id, user_id)
    moments = DEFAULT_SCHEDULE.moments(digest_date)
    publish_after = moments["digest"].astimezone(timezone.utc).replace(tzinfo=None)
    if now < publish_after:
        raise ValueError("daily digest is not due until 08:00 Asia/Shanghai")
    # A single workspace lock serializes competing first publications and revisions.
    session.execute(update(Workspace).where(Workspace.id == workspace_id)
                    .values(updated_at=Workspace.updated_at))
    daily_run = session.scalar(select(DailyRun).where(
        DailyRun.workspace_id == workspace_id, DailyRun.run_date == digest_date.isoformat(),
    ))
    if daily_run is None:
        daily_run = DailyRun(workspace_id=workspace_id, run_date=digest_date.isoformat(),
                             cutoff_at=moments["cutoff"].astimezone(timezone.utc).replace(tzinfo=None),
                             publish_after=publish_after, collection_enabled=False, created_at=now)
        session.add(daily_run)
        session.flush()
        for subscription in session.scalars(select(WorkspaceSubscription).where(
            WorkspaceSubscription.workspace_id == workspace_id, WorkspaceSubscription.status == "active",
        )):
            session.add(DailyRunSource(daily_run_id=daily_run.id, provider=subscription.provider,
                                      source_id=subscription.source_id, skipped_reason="not_scheduled"))
        session.flush()
    start_ts, cutoff_ts = DEFAULT_SCHEDULE.article_window(digest_date)
    ranking = RankingQuery(session, workspace_id, user_id)
    rows = session.execute(ranking.ordered(ranking.filtered(date_from=start_ts, date_to=cutoff_ts))).all()
    ids = [row[0].id for row in rows]
    items = []
    for row, data in zip(rows, ranking.serialize(rows)):
        items.append({"article": data, "relevance_score": data["effective_relevance"],
                      "reason": data["rank_reason"],
                      "is_late": bool(row.added_at and row.added_at > daily_run.cutoff_at)})
    for rank, item in enumerate(items, 1):
        item["rank"] = rank
    coverage = coverage_for(session, daily_run, ids)
    status = "published" if coverage["complete"] else "partial"
    late_count = sum(item["is_late"] for item in items)
    snapshot = {"date": digest_date.isoformat(), "title": f"{digest_date.isoformat()} 微信公众号日报",
                "summary": (f"截止 07:50，共汇总 {len(items)} 篇，迟到补录 {late_count} 篇；"
                            f"采集完成 {coverage['completed']}/{coverage['expected']} 个来源。"),
                "status": status, "coverage": coverage, "items": items,
                "ranking_version": "feedback-first-v3"}
    input_hash = hashlib.sha256(json.dumps(snapshot, ensure_ascii=False, sort_keys=True,
                                           separators=(",", ":"), allow_nan=False).encode()).hexdigest()
    digest = session.scalar(select(Digest).where(
        Digest.workspace_id == workspace_id, Digest.user_id == user_id,
        Digest.digest_date == digest_date.isoformat(),
    ))
    if digest is not None and digest.input_hash == input_hash:
        session.commit()
        return digest
    if digest is None:
        digest = Digest(workspace_id=workspace_id, user_id=user_id, digest_date=digest_date.isoformat(),
                        title=snapshot["title"], revision=0)
        session.add(digest)
        session.flush()
    revision = digest.revision + 1
    updated = session.execute(update(Digest).where(Digest.id == digest.id, Digest.revision == revision - 1)
        .values(revision=revision, input_hash=input_hash, coverage=coverage, daily_run_id=daily_run.id,
                status=status, title=snapshot["title"], summary=snapshot["summary"], generated_at=now))
    if updated.rowcount != 1:
        session.rollback()
        raise ValueError("digest revision changed concurrently; retry from current input")
    session.query(DigestItem).filter(DigestItem.digest_id == digest.id).delete(synchronize_session=False)
    for item in items:
        session.add(DigestItem(digest_id=digest.id, article_id=item["article"]["id"], rank=item["rank"],
                               relevance_score=item["relevance_score"], reason=item["reason"][:500],
                               is_late=item["is_late"]))
    snapshot["revision"] = revision
    session.add(DigestRevision(digest_id=digest.id, revision=revision, input_hash=input_hash,
                               snapshot=snapshot, created_at=now))
    session.add(OutboxEvent(
        workspace_id=workspace_id, event_type="digest.published" if revision == 1 else "digest.revised",
        aggregate_type="digest", aggregate_id=digest.id,
        payload={"digest_id": digest.id, "digest_date": digest.digest_date, "user_id": user_id,
                 "revision": revision, "status": status, "late_count": late_count},
        idempotency_key=f"digest:{digest.id}:revision:{revision}",
    ))
    session.commit()
    session.refresh(digest)
    return digest
