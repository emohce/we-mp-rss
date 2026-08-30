"""One SQL ranking/filter contract for inbox, detail and dated digests."""
from __future__ import annotations

import base64
import hashlib
import json
import math
from collections import defaultdict

from sqlalchemy import and_, case, func, or_, select
from sqlalchemy.orm import aliased, defer

from core.models.article import Article
from core.models.base import DATA_STATUS
from .models import (AnalysisRun, ArticleTopic, FeedbackEvent, PreferenceRule, Topic,
                     UserArticleState, WorkspaceArticle)


def topic_slug(name):
    import re
    ascii_slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return ascii_slug[:100] or "topic-" + hashlib.sha256(name.encode()).hexdigest()[:16]


def bounded(value):
    return case((value < 0, 0.0), (value > 1, 1.0), else_=func.coalesce(value, 0.5))


class RankingQuery:
    def __init__(self, session, workspace_id, user_id):
        self.session, self.workspace_id, self.user_id = session, workspace_id, user_id
        self.state = aliased(UserArticleState)
        self.analysis = aliased(AnalysisRun)
        self.correction = aliased(FeedbackEvent)
        latest_analysis = select(AnalysisRun.id).where(
            AnalysisRun.workspace_id == workspace_id, AnalysisRun.article_id == Article.id,
            AnalysisRun.status == "completed",
        ).order_by(AnalysisRun.created_at.desc(), AnalysisRun.id.desc()).limit(1).correlate(Article).scalar_subquery()
        latest_correction = select(FeedbackEvent.id).where(
            FeedbackEvent.workspace_id == workspace_id, FeedbackEvent.user_id == user_id,
            FeedbackEvent.article_id == Article.id, FeedbackEvent.event_type == "topic_correction",
        ).order_by(FeedbackEvent.created_at.desc(), FeedbackEvent.id.desc()).limit(1).correlate(Article).scalar_subquery()
        self.has_correction = and_(self.correction.id.is_not(None),
                                  func.coalesce(self.correction.value["reset"].as_boolean(), False).is_(False))
        self.rules = list(session.scalars(select(PreferenceRule).where(
            PreferenceRule.workspace_id == workspace_id, PreferenceRule.user_id == user_id,
            PreferenceRule.is_active.is_(True), PreferenceRule.revoked_at.is_(None),
        ).order_by(PreferenceRule.created_at, PreferenceRule.id)))
        boosts, collapses = [], []
        self.summary_style = ""
        for rule in self.rules:
            condition, action = rule.condition or {}, rule.action or {}
            if rule.rule_type == "reading_preference":
                style = action.get("summary_style")
                if style in {"brief", "detailed"}:
                    self.summary_style = style
                continue
            if rule.rule_type == "source_preference":
                values = condition.get("source_ids")
                predicate = Article.mp_id.in_(values) if isinstance(values, list) and values else None
            elif rule.rule_type == "topic_preference":
                values = condition.get("topic_slugs")
                predicate = self.topic_matches(values) if isinstance(values, list) and values else None
            else:
                continue
            try:
                boost = float(action.get("rank_boost", 0))
            except (ValueError, TypeError):
                continue
            if predicate is None or not math.isfinite(boost) or not -0.5 <= boost <= 0.5:
                continue  # malformed historical rules cannot silently become authority
            boosts.append(case((predicate, boost), else_=0.0))
            if action.get("collapse") is True:
                collapses.append(predicate)
        boost = sum(boosts, 0.0) + case((self.state.is_favorite.is_(True), 0.25), else_=0.0)
        ai = bounded(self.analysis.output["relevance_score"].as_float())
        explicit = self.state.relevance_override.is_not(None)
        self.score = case((explicit, bounded(self.state.relevance_override)), else_=bounded(ai + boost))
        self.boost = case((explicit, 0.0), else_=boost)
        self.collapsed = and_(~explicit, or_(*collapses)) if collapses else case((explicit, False), else_=False)
        self.query = (select(Article, self.state, self.analysis, self.correction,
                             self.score.label("score"), self.collapsed.label("collapsed"),
                             WorkspaceArticle.added_at.label("added_at"), self.boost.label("boost"))
            .join(WorkspaceArticle, WorkspaceArticle.article_id == Article.id)
            .outerjoin(self.state, and_(self.state.workspace_id == workspace_id,
                                       self.state.user_id == user_id, self.state.article_id == Article.id))
            .outerjoin(self.analysis, self.analysis.id == latest_analysis)
            .outerjoin(self.correction, self.correction.id == latest_correction)
            .where(WorkspaceArticle.workspace_id == workspace_id, Article.status != DATA_STATUS.DELETED))

    def topic_matches(self, values):
        automatic = select(ArticleTopic.id).join(Topic, Topic.id == ArticleTopic.topic_id).where(
            ArticleTopic.workspace_id == self.workspace_id, ArticleTopic.article_id == Article.id,
            or_(self.analysis.id.is_(None), ArticleTopic.analysis_version == self.analysis.prompt_version),
            or_(Topic.slug.in_(values), Topic.name.in_(values)),
        ).correlate(Article, self.analysis).exists()
        corrected = or_(*[self.correction.value[key][index].as_string().in_(values)
                          for key in ("topics", "topic_slugs") for index in range(8)])
        return or_(and_(self.has_correction, corrected), and_(~self.has_correction, automatic))

    def filtered(self, *, search="", source_id="", topic="", state_filter="", min_relevance=None,
                 date_from=None, date_to=None, article_id=""):
        query = self.query
        if article_id:
            query = query.where(Article.id == article_id)
        if source_id:
            query = query.where(Article.mp_id == source_id)
        if topic:
            query = query.where(self.topic_matches([topic]))
        if date_from is not None:
            query = query.where(Article.publish_time >= date_from)
        if date_to is not None:
            query = query.where(Article.publish_time <= date_to)
        if state_filter == "hidden":
            query = query.where(self.state.is_hidden.is_(True))
        elif state_filter != "all":
            query = query.where(or_(self.state.id.is_(None), self.state.is_hidden.is_(False)))
        if state_filter == "favorite":
            query = query.where(self.state.is_favorite.is_(True))
        elif state_filter == "unread":
            query = query.where(or_(self.state.id.is_(None), self.state.is_read.is_(False)))
        if min_relevance is not None:
            query = query.where(self.score >= min_relevance)
        if search:
            from .search import search_predicate
            query = query.where(search_predicate(self.session, search[:120]))
        return query.options(defer(Article.content), defer(Article.content_html))

    def ordered(self, query, order="relevance"):
        stamp = func.coalesce(Article.publish_time, 0)
        return query.order_by(*([self.score.desc()] if order == "relevance" else []), stamp.desc(), Article.id.desc())

    def topic_choices(self):
        from collections import Counter
        rows = self.session.execute(self.query.with_only_columns(
            Article.id, self.correction.value, self.analysis.prompt_version,
        )).all()
        versions = {row[0]: row[2] for row in rows}
        names, topics = {}, defaultdict(set)
        ids = list(versions)
        for start in range(0, len(ids), 400):
            for link, topic in self.session.execute(select(ArticleTopic, Topic).join(Topic, Topic.id == ArticleTopic.topic_id)
                .where(ArticleTopic.workspace_id == self.workspace_id, ArticleTopic.article_id.in_(ids[start:start + 400]))):
                if versions[link.article_id] in {None, link.analysis_version}:
                    topics[link.article_id].add(topic.slug)
                    names[topic.slug] = topic.name
        for article_id, correction, _ in rows:
            if correction is not None and not correction.get("reset"):
                corrected = {topic_slug(name): name for name in correction.get("topics", [])}
                topics[article_id] = set(corrected)
                names.update(corrected)
        counts = Counter(slug for values in topics.values() for slug in values)
        return [{"slug": slug, "name": names[slug], "article_count": count}
                for slug, count in sorted(counts.items(), key=lambda value: (-value[1], value[0]))]

    def serialize(self, rows, *, include_content=False):
        from .services import ArticleService
        ids = [row[0].id for row in rows]
        analysis_versions = {row[0].id: row[2].prompt_version if row[2] else None for row in rows}
        topics = defaultdict(dict)
        styles = {}
        for start in range(0, len(ids), 400):
            batch = ids[start:start + 400]
            for link, topic in self.session.execute(select(ArticleTopic, Topic).join(Topic, Topic.id == ArticleTopic.topic_id)
                .where(ArticleTopic.workspace_id == self.workspace_id, ArticleTopic.article_id.in_(batch))
                .order_by(ArticleTopic.confidence.desc(), Topic.slug)):
                if analysis_versions[link.article_id] not in {None, link.analysis_version}:
                    continue
                topics[link.article_id].setdefault(topic.slug, {"slug": topic.slug, "name": topic.name,
                                                               "confidence": link.confidence})
            for event in self.session.scalars(select(FeedbackEvent).where(
                FeedbackEvent.workspace_id == self.workspace_id, FeedbackEvent.user_id == self.user_id,
                FeedbackEvent.article_id.in_(batch), FeedbackEvent.event_type == "summary_preference",
            ).order_by(FeedbackEvent.created_at.desc(), FeedbackEvent.id.desc())):
                styles.setdefault(event.article_id, event.value.get("style", ""))
        items = []
        for article, state, analysis, correction, score, collapsed, added_at, boost in rows:
            effective_topics = list(topics[article.id].values())
            if correction is not None and not correction.value.get("reset"):
                effective_topics = [{"name": name, "slug": topic_slug(name), "confidence": 1.0,
                                     "source": "user_feedback"} for name in correction.value.get("topics", [])]
            item = ArticleService._serialize(article, state, analysis, effective_topics, include_content=include_content)
            item.update(effective_relevance=float(score), rank_adjustment=float(boost),
                        display_collapsed=bool(collapsed),
                        rank_reason="单篇明确反馈" if state and state.relevance_override is not None else
                                    ("已批准偏好与收藏" if boost else "文章分析与时间"))
            style = styles.get(article.id, self.summary_style) or "detailed"
            item["summary_style"] = style
            if style == "brief" and len(item["ai_summary"]) > 160:
                item["ai_summary"] = item["ai_summary"][:160] + "…"
            items.append(item)
        return items


def list_ranked(session, *, workspace_id, user_id, limit=50, cursor="", order="relevance", **filters):
    if order not in {"relevance", "newest"}:
        raise ValueError("unsupported article order")
    ranking = RankingQuery(session, workspace_id, user_id)
    query = ranking.filtered(**filters)
    scope = hashlib.sha256(json.dumps([workspace_id, user_id, order, filters], sort_keys=True).encode()).hexdigest()[:16]
    total = session.scalar(select(func.count()).select_from(query.subquery()))
    stamp = func.coalesce(Article.publish_time, 0)
    if cursor:
        try:
            data = json.loads(base64.urlsafe_b64decode(cursor + "=" * (-len(cursor) % 4)))
            score, published, item_id = float(data["score"]), int(data["time"]), str(data["id"])
            if data["scope"] != scope or not math.isfinite(score) or len(item_id) > 255:
                raise ValueError()
        except Exception as exc:
            raise ValueError("invalid or stale article cursor; refresh this filter") from exc
        older = or_(stamp < published, and_(stamp == published, Article.id < item_id))
        query = query.where(or_(ranking.score < score, and_(ranking.score == score, older)) if order == "relevance" else older)
    limit = min(100, max(1, limit))
    rows = session.execute(ranking.ordered(query, order).limit(limit + 1)).all()
    has_more = len(rows) > limit
    rows = rows[:limit]
    next_cursor = ""
    if has_more:
        last = rows[-1]
        data = {"scope": scope, "score": float(last.score), "time": int(last[0].publish_time or 0), "id": last[0].id}
        next_cursor = base64.urlsafe_b64encode(json.dumps(data, separators=(",", ":")).encode()).decode().rstrip("=")
    return {"items": ranking.serialize(rows), "total": total, "has_more": has_more,
            "next_cursor": next_cursor, "order": order, "ranking_version": "feedback-first-v3"}
