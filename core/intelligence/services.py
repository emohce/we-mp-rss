from __future__ import annotations

import base64
import copy
import hashlib
import json
import re
import secrets
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, aliased

from core.models.article import Article
from core.models.base import DATA_STATUS
from core.models.feed import Feed

from .analysis import AnalysisEnvelope, AnalyzerPipeline
from .daily import queue_reconciliations
from .idempotency import normalize_idempotency_key
from .models import (
    AnalysisRun,
    ArticleTopic,
    CollectionJob,
    CollectorAccount,
    Digest,
    DigestItem,
    DigestRevision,
    FeedbackEvent,
    OutboxEvent,
    PreferenceRule,
    PreferenceRuleProposal,
    ShareLink,
    SourceProfile,
    Topic,
    UserArticleState,
    Workspace,
    WorkspaceArticle,
    WorkspaceMembership,
    WorkspaceSubscription,
    utcnow,
)
from .scheduling import DEFAULT_SCHEDULE


class AccessDenied(ValueError):
    pass


def _topic_slug(name: str) -> str:
    ascii_slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    if ascii_slug:
        return ascii_slug[:100]
    return "topic-" + hashlib.sha256(name.encode("utf-8")).hexdigest()[:16]


def _encode_cursor(publish_time: int, article_id: str) -> str:
    raw = json.dumps([publish_time, article_id], separators=(",", ":")).encode()
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def _decode_cursor(value: str) -> tuple[int, str]:
    try:
        padded = value + "=" * (-len(value) % 4)
        publish_time, article_id = json.loads(base64.urlsafe_b64decode(padded).decode())
        return int(publish_time), str(article_id)
    except Exception as exc:
        raise ValueError("invalid article cursor") from exc


class TenantService:
    @staticmethod
    def bootstrap_personal_workspace(session: Session, user_id: str, username: str) -> Workspace:
        membership = session.scalar(
            select(WorkspaceMembership).where(WorkspaceMembership.user_id == user_id).limit(1)
        )
        if membership:
            workspace = session.get(Workspace, membership.workspace_id)
            if workspace:
                return workspace
        slug = "user-" + hashlib.sha256(user_id.encode()).hexdigest()[:16]
        workspace = session.scalar(select(Workspace).where(Workspace.slug == slug))
        if workspace is None:
            workspace = Workspace(
                name=f"{username or 'Personal'} 的工作区",
                slug=slug,
                owner_user_id=user_id,
            )
            session.add(workspace)
            session.flush()
        session.add(
            WorkspaceMembership(
                workspace_id=workspace.id,
                user_id=user_id,
                role="owner" if workspace.owner_user_id == user_id else "member",
            )
        )
        session.commit()
        session.refresh(workspace)
        return workspace

    @staticmethod
    def require_membership(session: Session, workspace_id: str, user_id: str) -> WorkspaceMembership:
        membership = session.scalar(
            select(WorkspaceMembership).where(
                WorkspaceMembership.workspace_id == workspace_id,
                WorkspaceMembership.user_id == user_id,
            )
        )
        if membership is None:
            raise AccessDenied("workspace is not accessible")
        return membership

    @staticmethod
    def attach_legacy_articles(
        session: Session,
        *,
        workspace_id: str,
        user_id: str,
        batch_size: int = 2000,
        authorized: bool = False,
    ) -> dict:
        """Expose pre-v2 global articles to a personal workspace in bounded batches."""

        if not authorized:
            raise AccessDenied("legacy global article backfill requires explicit admin authorization")
        TenantService.require_membership(session, workspace_id, user_id)
        existing_link = select(WorkspaceArticle.id).where(
            WorkspaceArticle.workspace_id == workspace_id,
            WorkspaceArticle.article_id == Article.id,
        ).exists()
        requested_size = min(max(batch_size, 1), 5000)
        rows = session.execute(
            select(Article.id, Article.mp_id)
            .where(
                ~existing_link,
                Article.status != DATA_STATUS.DELETED,
            )
            .order_by(Article.publish_time.desc(), Article.id.desc())
            .limit(requested_size + 1)
        ).all()
        for article_id, source_id in rows[:requested_size]:
            session.add(
                WorkspaceArticle(
                    workspace_id=workspace_id,
                    article_id=article_id,
                    source_id=str(source_id or ""),
                    ingestion_source="legacy-backfill",
                )
            )
        session.commit()
        return {
            "attached": min(len(rows), requested_size),
            "has_more": len(rows) > requested_size,
        }

    @staticmethod
    def require_article(session: Session, workspace_id: str, article_id: str) -> Article:
        article = session.scalar(
            select(Article)
            .join(WorkspaceArticle, WorkspaceArticle.article_id == Article.id)
            .where(
                WorkspaceArticle.workspace_id == workspace_id,
                Article.id == article_id,
                Article.status != DATA_STATUS.DELETED,
            )
        )
        if article is None:
            raise AccessDenied("article is not accessible")
        return article


class ArticleService:
    @staticmethod
    def _relevance(
        analysis: AnalysisRun | None,
        state: UserArticleState | None,
    ) -> tuple[float, float]:
        ai_relevance = (
            float((analysis.output or {}).get("relevance_score", 0.5))
            if analysis
            else 0.5
        )
        effective = (
            float(state.relevance_override)
            if state and state.relevance_override is not None
            else ai_relevance
        )
        return ai_relevance, max(0.0, min(1.0, effective))

    @staticmethod
    def _serialize(
        article: Article,
        state: UserArticleState | None,
        analysis: AnalysisRun | None,
        topics: list[dict],
        *,
        include_content: bool,
    ) -> dict:
        if include_content:
            result = article.to_dict()
        else:
            result = {column.name: getattr(article, column.name) for column in Article.__table__.columns
                      if column.name not in {"content", "content_html"}}
            result = {key: value.isoformat() if isinstance(value, datetime) else value for key, value in result.items()}
        ai_relevance, effective_relevance = ArticleService._relevance(analysis, state)
        result.update(
            {
                "is_read": bool(state and state.is_read),
                "is_favorite": bool(state and state.is_favorite),
                "is_hidden": bool(state and state.is_hidden),
                "read_progress": float(state.read_progress if state else 0),
                "feedback_sentiment": str(state.sentiment if state else ""),
                "user_relevance_override": state.relevance_override if state else None,
                "ai_summary": analysis.summary if analysis else "",
                "ai_relevance": ai_relevance,
                "effective_relevance": effective_relevance,
                "ai_reason": str((analysis.output or {}).get("reason", "")) if analysis else "",
                "topics": topics,
            }
        )
        return result

    @classmethod
    def list_articles(
        cls, session: Session, *, workspace_id: str, user_id: str, limit: int = 50,
        cursor: str = "", search: str = "", source_id: str = "", topic: str = "",
        state_filter: str = "", min_relevance: float | None = None,
        date_from: int | None = None, date_to: int | None = None, order: str = "relevance",
    ) -> dict:
        from .ranking import list_ranked
        TenantService.require_membership(session, workspace_id, user_id)
        return list_ranked(session, workspace_id=workspace_id, user_id=user_id, limit=limit,
                           cursor=cursor, order=order, search=search, source_id=source_id, topic=topic,
                           state_filter=state_filter, min_relevance=min_relevance,
                           date_from=date_from, date_to=date_to)

    @classmethod
    def get_article(cls, session: Session, *, workspace_id: str, user_id: str, article_id: str,
                    content_store_factory=None) -> dict:
        from .content import resolve_content
        from .ranking import RankingQuery
        TenantService.require_membership(session, workspace_id, user_id)
        TenantService.require_article(session, workspace_id, article_id)
        ranking = RankingQuery(session, workspace_id, user_id)
        rows = session.execute(ranking.filtered(article_id=article_id, state_filter="all")).all()
        if not rows:
            raise AccessDenied("article is not visible in this workspace")
        data = ranking.serialize(rows, include_content=True)[0]
        body, content_status, warning = resolve_content(session, rows[0][0], store_factory=content_store_factory)
        data.update(content=body, content_html=body, content_status=content_status, content_warning=warning)
        return data


class FeedbackService:
    ALLOWED_EVENTS = {
        "like",
        "dislike",
        "favorite",
        "unfavorite",
        "read",
        "unread",
        "neutral",
        "hide",
        "unhide",
        "irrelevant",
        "topic_correction",
        "summary_preference",
        "free_text",
    }

    @classmethod
    def record(
        cls,
        session: Session,
        *,
        workspace_id: str,
        user_id: str,
        article_id: str,
        event_type: str,
        value: dict | None = None,
    ) -> FeedbackEvent:
        TenantService.require_membership(session, workspace_id, user_id)
        TenantService.require_article(session, workspace_id, article_id)
        if event_type not in cls.ALLOWED_EVENTS:
            raise ValueError("unsupported feedback event")
        from .preferences import feedback_value
        value = feedback_value(event_type, value)
        state = session.scalar(
            select(UserArticleState).where(
                UserArticleState.workspace_id == workspace_id,
                UserArticleState.user_id == user_id,
                UserArticleState.article_id == article_id,
            )
        )
        if state is None:
            state = UserArticleState(
                workspace_id=workspace_id, user_id=user_id, article_id=article_id
            )
            session.add(state)
        if event_type == "like":
            state.sentiment = "like"
            state.relevance_override = 1.0
        elif event_type == "favorite":
            state.is_favorite = True
        elif event_type in {"dislike", "irrelevant"}:
            state.sentiment = "dislike"
            state.relevance_override = 0.0
        elif event_type == "neutral":
            state.sentiment = ""
            state.relevance_override = None
        elif event_type == "unfavorite":
            state.is_favorite = False
        elif event_type == "read":
            state.is_read = True
        elif event_type == "unread":
            state.is_read = False
        elif event_type == "hide":
            state.is_hidden = True
        elif event_type == "unhide":
            state.is_hidden = False
        event = FeedbackEvent(
            workspace_id=workspace_id,
            user_id=user_id,
            article_id=article_id,
            event_type=event_type,
            value=value or {},
        )
        session.add(event)
        session.flush()
        queue_reconciliations(session, workspace_ids=[workspace_id], article_ids=[article_id],
                              cause=f"feedback:{event.id}", now=utcnow(), user_ids=(user_id,))
        session.commit()
        session.refresh(event)
        return event

    @staticmethod
    def propose_preferences(session: Session, *, workspace_id: str, user_id: str) -> list[PreferenceRuleProposal]:
        from .preferences import propose_rules
        return propose_rules(session, workspace_id=workspace_id, user_id=user_id)

    @staticmethod
    def review_proposal(session: Session, *, workspace_id: str, user_id: str,
                        proposal_id: str, approve: bool) -> PreferenceRuleProposal:
        from .preferences import review_rule
        return review_rule(session, workspace_id=workspace_id, user_id=user_id,
                           proposal_id=proposal_id, approve=approve)


class AnalysisService:
    def __init__(self, pipeline: AnalyzerPipeline | None = None):
        self.pipeline = pipeline or AnalyzerPipeline()

    def analyze_article(
        self,
        session: Session,
        *,
        workspace_id: str,
        user_id: str,
        article_id: str,
    ) -> AnalysisEnvelope:
        TenantService.require_membership(session, workspace_id, user_id)
        article = TenantService.require_article(session, workspace_id, article_id)
        envelope = self.pipeline.analyze(article.to_dict())
        from .search import index_article
        index_article(session, article)
        output = envelope.to_dict()
        analysis_run = AnalysisRun(
                workspace_id=workspace_id,
                article_id=article_id,
                provider=envelope.provider,
                model=envelope.model,
                prompt_version=envelope.prompt_version,
                status="completed",
                summary=envelope.summary,
                output=output,
        )
        session.add(analysis_run)
        session.flush()
        session.query(ArticleTopic).filter(
            ArticleTopic.workspace_id == workspace_id, ArticleTopic.article_id == article_id,
            ArticleTopic.analysis_version == envelope.prompt_version,
        ).delete(synchronize_session=False)
        for topic_score in envelope.topics:
            slug = _topic_slug(topic_score.name)
            topic = session.scalar(select(Topic).where(Topic.slug == slug))
            if topic is None:
                topic = Topic(slug=slug, name=topic_score.name)
                session.add(topic)
                session.flush()
            link = session.scalar(
                select(ArticleTopic).where(
                    ArticleTopic.workspace_id == workspace_id,
                    ArticleTopic.article_id == article_id,
                    ArticleTopic.topic_id == topic.id,
                    ArticleTopic.analysis_version == envelope.prompt_version,
                )
            )
            if link is None:
                session.add(
                    ArticleTopic(
                        workspace_id=workspace_id,
                        article_id=article_id,
                        topic_id=topic.id,
                        confidence=topic_score.confidence,
                        analysis_version=envelope.prompt_version,
                    )
                )
            else:
                link.confidence = topic_score.confidence
        event_key = f"analysis:{analysis_run.id}"
        if session.scalar(select(OutboxEvent.id).where(OutboxEvent.idempotency_key == event_key)) is None:
            session.add(
                OutboxEvent(
                    workspace_id=workspace_id,
                    event_type="analysis.article.completed",
                    aggregate_type="article",
                    aggregate_id=article_id,
                    payload={"article_id": article_id, "provider": envelope.provider},
                    idempotency_key=event_key,
                )
            )
        queue_reconciliations(session, workspace_ids=[workspace_id], article_ids=[article_id],
                              cause=f"analysis-result:{analysis_run.id}", now=utcnow())
        session.commit()
        return envelope

    @staticmethod
    def refresh_source_profile(
        session: Session, *, workspace_id: str, user_id: str, source_id: str
    ) -> SourceProfile:
        TenantService.require_membership(session, workspace_id, user_id)
        cutoff = int((utcnow() - timedelta(days=90)).timestamp())
        articles = session.scalars(
            select(Article)
            .join(WorkspaceArticle, WorkspaceArticle.article_id == Article.id)
            .where(
                WorkspaceArticle.workspace_id == workspace_id,
                Article.mp_id == source_id,
                Article.publish_time >= cutoff,
                Article.status != DATA_STATUS.DELETED,
            )
            .order_by(Article.publish_time.desc())
            .limit(30)
        ).all()
        article_ids = [article.id for article in articles]
        topic_counts: Counter[str] = Counter()
        if article_ids:
            for topic_name, _ in session.execute(
                select(Topic.name, ArticleTopic.article_id)
                .join(ArticleTopic, ArticleTopic.topic_id == Topic.id)
                .where(
                    ArticleTopic.workspace_id == workspace_id,
                    ArticleTopic.article_id.in_(article_ids),
                )
                .distinct()
            ):
                topic_counts[topic_name] += 1
        topics = [
            {"name": name, "weight": count / max(1, len(article_ids))}
            for name, count in topic_counts.most_common(8)
        ]
        profile = session.scalar(
            select(SourceProfile).where(
                SourceProfile.workspace_id == workspace_id,
                SourceProfile.source_id == source_id,
            )
        )
        if profile is None:
            profile = SourceProfile(workspace_id=workspace_id, source_id=source_id)
            session.add(profile)
        profile.topics = topics
        profile.sample_count = len(article_ids)
        profile.confidence = min(1.0, len(article_ids) / 5) if article_ids else 0.0
        profile.summary = "、".join(item["name"] for item in topics[:4]) or "样本不足"
        profile.window_start = utcnow() - timedelta(days=90)
        profile.window_end = utcnow()
        session.commit()
        session.refresh(profile)
        return profile


class SubscriptionService:
    GLOBAL_WE_MP_RSS_ACCOUNT_ID = "builtin-we-mp-rss"

    @staticmethod
    def subscribe(
        session: Session,
        *,
        workspace_id: str,
        user_id: str,
        source_id: str,
        provider: str = "we-mp-rss",
    ) -> tuple[WorkspaceSubscription, CollectionJob | None]:
        TenantService.require_membership(session, workspace_id, user_id)
        if provider != "we-mp-rss":
            raise ValueError("provider runtime subscription is disabled pending capability and account acceptance")
        session.execute(update(Workspace).where(Workspace.id == workspace_id).values(updated_at=Workspace.updated_at))
        if provider == "we-mp-rss":
            feed = session.get(Feed, source_id)
            if feed is None or not feed.faker_id or feed.status == DATA_STATUS.DELETED:
                raise ValueError("select a locally resolved public-account source first")
        subscription = session.scalar(
            select(WorkspaceSubscription).where(
                WorkspaceSubscription.workspace_id == workspace_id,
                WorkspaceSubscription.source_id == source_id,
            )
        )
        if subscription is None:
            subscription = WorkspaceSubscription(
                workspace_id=workspace_id,
                source_id=source_id,
                provider=provider,
                discovery_mode="latest_page",
            )
            session.add(subscription)
            session.flush()
        else:
            subscription.status = "active"
            subscription.provider = provider
        if provider == "we-mp-rss":
            account = session.get(
                CollectorAccount,
                SubscriptionService.GLOBAL_WE_MP_RSS_ACCOUNT_ID,
            )
        else:
            account = session.scalar(
                select(CollectorAccount)
                .where(
                    CollectorAccount.provider == provider,
                    CollectorAccount.workspace_id == workspace_id,
                )
                .limit(1)
            )
        if account is None and provider == "we-mp-rss":
            try:
                with session.begin_nested():
                    account = CollectorAccount(
                        id=SubscriptionService.GLOBAL_WE_MP_RSS_ACCOUNT_ID,
                        workspace_id=None, provider=provider, label="现有 we-mp-rss 授权",
                        secret_ref="driver.token",
                    )
                    session.add(account)
                    session.flush()
            except IntegrityError:
                account = session.get(CollectorAccount, SubscriptionService.GLOBAL_WE_MP_RSS_ACCOUNT_ID)
                if account is None:
                    raise
        existing_link = select(WorkspaceArticle.id).where(
            WorkspaceArticle.workspace_id == workspace_id,
            WorkspaceArticle.article_id == Article.id,
        ).exists()
        known_articles = session.execute(
            select(Article.id, Article.mp_id)
            .where(
                Article.mp_id == source_id,
                Article.status != DATA_STATUS.DELETED,
                ~existing_link,
            )
            .order_by(Article.publish_time.desc(), Article.id.desc())
            .limit(500)
        ).all() if provider == "we-mp-rss" else []
        for article_id, known_source_id in known_articles:
            session.add(
                WorkspaceArticle(
                    workspace_id=workspace_id,
                    article_id=article_id,
                    source_id=str(known_source_id or source_id),
                    ingestion_source="shared-source-backfill",
                )
            )
        schedule_date = datetime.now(DEFAULT_SCHEDULE.timezone).date().isoformat()
        account_key = account.id if account else "unconfigured"
        idempotency_key = normalize_idempotency_key(
            f"source-discovery:{account_key}:{source_id}:{schedule_date}",
            160,
        )
        job = session.scalar(select(CollectionJob).where(CollectionJob.idempotency_key == idempotency_key))
        if job is None:
            job = CollectionJob(
                workspace_id=workspace_id,
                account_id=account.id if account else None,
                provider=provider,
                source_id=source_id,
                kind="head",
                payload={"page_budget": 3, "reason": "new_subscription"},
                idempotency_key=idempotency_key,
                priority=50,
            )
            try:
                with session.begin_nested():
                    session.add(job)
                    session.flush()
            except IntegrityError:
                job = session.scalar(select(CollectionJob).where(CollectionJob.idempotency_key == idempotency_key))
                if job is None:
                    raise
        session.commit()
        session.refresh(subscription)
        return subscription, job

    @staticmethod
    def enqueue_backfill(session, *, workspace_id, user_id, subscription_id, request_id, page_budget=3):
        TenantService.require_membership(session, workspace_id, user_id)
        session.execute(update(Workspace).where(Workspace.id == workspace_id).values(updated_at=Workspace.updated_at))
        subscription = session.scalar(select(WorkspaceSubscription).where(
            WorkspaceSubscription.id == subscription_id, WorkspaceSubscription.workspace_id == workspace_id,
            WorkspaceSubscription.status == "active", WorkspaceSubscription.provider == "we-mp-rss",
        ))
        if subscription is None:
            raise AccessDenied("active supported subscription not found")
        key = normalize_idempotency_key(f"manual-backfill:{subscription_id}:{request_id}", 160)
        job = session.scalar(select(CollectionJob).where(CollectionJob.idempotency_key == key))
        if job is None:
            account = session.get(CollectorAccount, SubscriptionService.GLOBAL_WE_MP_RSS_ACCOUNT_ID)
            if account is None or account.status not in {"healthy", "probe"}:
                raise ValueError("collector account is unavailable")
            job = CollectionJob(workspace_id=workspace_id, account_id=account.id, provider="we-mp-rss",
                                source_id=subscription.source_id, kind="backfill", priority=5,
                                payload={"page_budget": min(20, max(1, page_budget)), "reason": "explicit_backfill"},
                                idempotency_key=key)
            session.add(job)
            session.commit()
            session.refresh(job)
        return job


class DigestService:
    @staticmethod
    def generate(
        session: Session,
        *,
        workspace_id: str,
        user_id: str,
        digest_date: date,
        now: datetime | None = None,
    ) -> Digest:
        from .digests import generate_digest
        return generate_digest(session, workspace_id=workspace_id, user_id=user_id,
                               digest_date=digest_date, now=now)

    @staticmethod
    def serialize(session: Session, *, workspace_id: str, user_id: str, digest_date: str) -> dict:
        TenantService.require_membership(session, workspace_id, user_id)
        digest = session.scalar(
            select(Digest).where(
                Digest.workspace_id == workspace_id,
                Digest.user_id == user_id,
                Digest.digest_date == digest_date,
            )
        )
        if digest is None:
            raise ValueError("digest not found")
        revision = session.scalar(select(DigestRevision).where(
            DigestRevision.digest_id == digest.id, DigestRevision.revision == digest.revision,
        ))
        if revision is not None:
            result = copy.deepcopy(revision.snapshot)
            result.update(id=digest.id, generated_at=digest.generated_at)
            visible_ids = set(session.scalars(select(WorkspaceArticle.article_id).join(
                Article, Article.id == WorkspaceArticle.article_id,
            ).where(WorkspaceArticle.workspace_id == workspace_id, Article.status != DATA_STATUS.DELETED)))
            result["items"] = [item for item in result.get("items", []) if item["article"]["id"] in visible_ids]
            return result
        items = []
        for item in session.scalars(
            select(DigestItem)
            .where(DigestItem.digest_id == digest.id)
            .order_by(DigestItem.rank)
        ):
            article = ArticleService.get_article(
                session,
                workspace_id=workspace_id,
                user_id=user_id,
                article_id=item.article_id,
            )
            article.pop("content", None)
            article.pop("content_html", None)
            items.append(
                {
                    "rank": item.rank,
                    "relevance_score": item.relevance_score,
                    "reason": item.reason,
                    "is_late": item.is_late,
                    "article": article,
                }
            )
        return {
            "id": digest.id,
            "date": digest.digest_date,
            "title": digest.title,
            "summary": digest.summary,
            "status": digest.status,
            "revision": digest.revision,
            "coverage": digest.coverage or {},
            "generated_at": digest.generated_at,
            "items": items,
        }

    @staticmethod
    def list_digests(
        session: Session,
        *,
        workspace_id: str,
        user_id: str,
        limit: int = 60,
    ) -> list[dict]:
        TenantService.require_membership(session, workspace_id, user_id)
        item_count = (
            select(func.count(DigestItem.id))
            .where(DigestItem.digest_id == Digest.id)
            .correlate(Digest)
            .scalar_subquery()
        )
        rows = session.execute(
            select(Digest, item_count.label("item_count"))
            .where(
                Digest.workspace_id == workspace_id,
                Digest.user_id == user_id,
            )
            .order_by(Digest.digest_date.desc())
            .limit(min(max(limit, 1), 366))
        ).all()
        return [
            {
                "id": digest.id,
                "date": digest.digest_date,
                "title": digest.title,
                "summary": digest.summary,
                "status": digest.status,
                "revision": digest.revision,
                "coverage": digest.coverage or {},
                "generated_at": digest.generated_at,
                "item_count": int(count or 0),
            }
            for digest, count in rows
        ]

    @staticmethod
    def create_share_link(
        session: Session,
        *,
        workspace_id: str,
        user_id: str,
        digest_date: str,
        expires_in_hours: int = 168,
    ) -> tuple[ShareLink, str]:
        digest_data = DigestService.serialize(
            session, workspace_id=workspace_id, user_id=user_id, digest_date=digest_date
        )
        token = secrets.token_urlsafe(36)
        link = ShareLink(
            workspace_id=workspace_id,
            digest_id=digest_data["id"],
            token_hash=hashlib.sha256(token.encode()).hexdigest(),
            expires_at=utcnow() + timedelta(hours=max(1, min(expires_in_hours, 24 * 90))),
        )
        session.add(link)
        session.commit()
        session.refresh(link)
        return link, token

    @staticmethod
    def resolve_share(session: Session, token: str) -> tuple[ShareLink, Digest]:
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        link = session.scalar(select(ShareLink).where(ShareLink.token_hash == token_hash))
        if link is None or link.revoked_at is not None or (link.expires_at and link.expires_at <= utcnow()):
            raise AccessDenied("share link is invalid or expired")
        digest = session.get(Digest, link.digest_id)
        if digest is None:
            raise AccessDenied("shared digest no longer exists")
        return link, digest

    @staticmethod
    def revoke_share(session, *, workspace_id, user_id, share_id):
        TenantService.require_membership(session, workspace_id, user_id)
        link = session.scalar(select(ShareLink).join(Digest, Digest.id == ShareLink.digest_id).where(
            ShareLink.id == share_id, ShareLink.workspace_id == workspace_id,
            Digest.workspace_id == workspace_id, Digest.user_id == user_id,
        ))
        if link is None:
            raise AccessDenied("share link not found")
        link.revoked_at = link.revoked_at or utcnow()
        session.commit()
        return link

    @staticmethod
    def serialize_public_share(session: Session, token: str) -> dict:
        link, digest = DigestService.resolve_share(session, token)
        data = DigestService.serialize(
            session,
            workspace_id=digest.workspace_id,
            user_id=digest.user_id,
            digest_date=digest.digest_date,
        )
        for item in data["items"]:
            article = item["article"]
            item["article"] = {
                key: article.get(key)
                for key in (
                    "id",
                    "mp_id",
                    "title",
                    "pic_url",
                    "url",
                    "description",
                    "publish_time",
                    "ai_summary",
                    "topics",
                )
            }
        data["share"] = {
            "expires_at": link.expires_at,
            "created_at": link.created_at,
        }
        return data
