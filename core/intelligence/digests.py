"""Revisioned, local-only daily digest generation."""
from datetime import datetime, timezone
import hashlib
import json

from sqlalchemy import and_, or_, select, update
from sqlalchemy.orm import aliased

from core.models.article import Article
from core.models.base import DATA_STATUS
from .daily import coverage_for
from .models import (AnalysisRun, ArticleTopic, DailyRun, DailyRunSource, Digest, DigestItem,
                     DigestRevision, OutboxEvent, PreferenceRule, Topic, UserArticleState,
                     Workspace, WorkspaceArticle, WorkspaceSubscription, utcnow)
from .scheduling import DEFAULT_SCHEDULE


def generate_digest(session, *, workspace_id, user_id, digest_date, now=None):
    from .services import ArticleService, TenantService

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
    state_alias = aliased(UserArticleState)
    rows = session.execute(select(Article, state_alias, WorkspaceArticle.added_at)
        .join(WorkspaceArticle, WorkspaceArticle.article_id == Article.id)
        .outerjoin(state_alias, and_(state_alias.workspace_id == workspace_id,
                                    state_alias.user_id == user_id, state_alias.article_id == Article.id))
        .where(WorkspaceArticle.workspace_id == workspace_id,
               Article.publish_time >= start_ts, Article.publish_time <= cutoff_ts,
               Article.status != DATA_STATUS.DELETED,
               or_(state_alias.id.is_(None), state_alias.is_hidden.is_(False)))
    ).all()
    ids = [article.id for article, _, _ in rows]
    latest = {}
    topic_map = {}
    if ids:
        for analysis in session.scalars(select(AnalysisRun).where(
            AnalysisRun.workspace_id == workspace_id, AnalysisRun.article_id.in_(ids),
            AnalysisRun.status == "completed",
        ).order_by(AnalysisRun.created_at.desc(), AnalysisRun.id.desc())):
            latest.setdefault(analysis.article_id, analysis)
        for link, topic in session.execute(select(ArticleTopic, Topic).join(Topic, Topic.id == ArticleTopic.topic_id)
            .where(ArticleTopic.workspace_id == workspace_id, ArticleTopic.article_id.in_(ids))
            .order_by(ArticleTopic.confidence.desc(), Topic.slug)):
            topic_map.setdefault(link.article_id, {}).setdefault(topic.slug, {
                "slug": topic.slug, "name": topic.name, "confidence": link.confidence,
            })
    source_boosts = {}
    for rule in session.scalars(select(PreferenceRule).where(
        PreferenceRule.workspace_id == workspace_id, PreferenceRule.user_id == user_id,
        PreferenceRule.is_active.is_(True), PreferenceRule.revoked_at.is_(None),
    )):
        if rule.rule_type == "source_preference":
            for source_id in (rule.condition or {}).get("source_ids", []):
                source_boosts[str(source_id)] = float((rule.action or {}).get("rank_boost", 0))
    items = []
    for article, state, added_at in rows:
        analysis = latest.get(article.id)
        data = ArticleService._serialize(article, state, analysis, list(topic_map.get(article.id, {}).values()),
                                         include_content=False)
        score = data["effective_relevance"] + source_boosts.get(str(article.mp_id or ""), 0)
        if state and state.is_favorite:
            score += 0.25
        items.append({"article": data, "relevance_score": score,
                      "reason": data["ai_reason"] or "按时间与来源进入当日汇总",
                      "is_late": bool(added_at and added_at > daily_run.cutoff_at)})
    items.sort(key=lambda item: (item["relevance_score"], item["article"]["publish_time"] or 0,
                                 item["article"]["id"]), reverse=True)
    for rank, item in enumerate(items, 1):
        item["rank"] = rank
    coverage = coverage_for(session, daily_run, ids)
    status = "published" if coverage["complete"] else "partial"
    late_count = sum(item["is_late"] for item in items)
    snapshot = {"date": digest_date.isoformat(), "title": f"{digest_date.isoformat()} 微信公众号日报",
                "summary": (f"截止 07:50，共汇总 {len(items)} 篇，迟到补录 {late_count} 篇；"
                            f"采集完成 {coverage['completed']}/{coverage['expected']} 个来源。"),
                "status": status, "coverage": coverage, "items": items}
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
