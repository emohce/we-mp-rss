"""Validated personal filters and approval-gated, reversible learning rules."""
from collections import Counter, defaultdict
from datetime import timedelta
import json
import math

from sqlalchemy import select, update

from core.models.article import Article
from .daily import queue_run
from .models import (DailyRun, Digest, FeedbackEvent, PreferenceRule, PreferenceRuleProposal,
                     SavedFilter, UserArticleState, Workspace, utcnow)
from .ranking import RankingQuery, topic_slug


def feedback_value(event_type, value):
    value = dict(value or {})
    if len(json.dumps(value, ensure_ascii=False, allow_nan=False).encode()) > 16_384:
        raise ValueError("feedback value exceeds 16 KiB")
    if event_type == "topic_correction":
        if value.get("reset") is True:
            return {"reset": True}
        topics = value.get("topics")
        if not isinstance(topics, list) or len(topics) > 8 or any(
            not isinstance(item, str) or not item.strip() or len(item) > 80 for item in topics
        ):
            raise ValueError("topic correction requires up to eight non-empty names")
        names = list({topic_slug(item.strip()): item.strip() for item in topics}.values())
        return {"topics": names, "topic_slugs": [topic_slug(item) for item in names]}
    if event_type == "summary_preference":
        if value.get("style") not in {"brief", "detailed"}:
            raise ValueError("summary style must be brief or detailed")
        return {"style": value["style"]}
    if event_type == "free_text" and (not isinstance(value.get("text"), str) or len(value["text"]) > 2000):
        raise ValueError("feedback text must be a string of at most 2000 characters")
    return value


def validate_rule(rule_type, condition, action):
    if rule_type == "reading_preference":
        if condition or set(action) != {"summary_style"} or action["summary_style"] not in {"brief", "detailed"}:
            raise ValueError("invalid reading preference")
        return
    field = {"source_preference": "source_ids", "topic_preference": "topic_slugs"}.get(rule_type)
    values = condition.get(field) if field else None
    if (not field or set(condition) != {field} or not isinstance(values, list) or not 1 <= len(values) <= 8
            or any(not isinstance(value, str) or not value or len(value) > 255 for value in values)):
        raise ValueError("invalid preference condition")
    boost = action.get("rank_boost")
    if (set(action) - {"rank_boost", "collapse"} or not isinstance(boost, (int, float))
            or isinstance(boost, bool) or not math.isfinite(boost) or not -0.5 <= boost <= 0.5
            or ("collapse" in action and not isinstance(action["collapse"], bool))):
        raise ValueError("invalid preference action")


def queue_preference_revisions(session, workspace_id, user_id, cause):
    for run in session.scalars(select(DailyRun).join(Digest, Digest.daily_run_id == DailyRun.id).where(
        DailyRun.workspace_id == workspace_id, Digest.user_id == user_id,
    ).distinct()):
        queue_run(session, run, cause=cause, now=utcnow(), user_ids=(user_id,))


def propose_rules(session, *, workspace_id, user_id):
    from .services import TenantService
    TenantService.require_membership(session, workspace_id, user_id)
    session.execute(update(Workspace).where(Workspace.id == workspace_id).values(updated_at=Workspace.updated_at))
    events = list(session.scalars(select(FeedbackEvent).where(
        FeedbackEvent.workspace_id == workspace_id, FeedbackEvent.user_id == user_id,
    ).order_by(FeedbackEvent.created_at, FeedbackEvent.id)))
    # Retain and consider the entire event history; only current explicit state contributes direction.
    distinct = {event.article_id for event in events}
    if len(distinct) < 20 or events[-1].created_at - events[0].created_at < timedelta(days=7):
        return []
    latest_opinion, latest_style = {}, {}
    for event in events:
        if event.event_type in {"like", "dislike", "irrelevant", "hide", "unhide", "favorite", "unfavorite", "neutral"}:
            latest_opinion[event.article_id] = event
        if event.event_type == "summary_preference":
            latest_style[event.article_id] = event
    groups = defaultdict(list)
    ranking = RankingQuery(session, workspace_id, user_id)
    opinion_ids = list(latest_opinion)
    for offset in range(0, len(opinion_ids), 400):
        rows = session.execute(ranking.filtered(state_filter="all").where(
            Article.id.in_(opinion_ids[offset:offset + 400]),
        )).all()
        for row, item in zip(rows, ranking.serialize(rows)):
            article, state = row[0], row[1]
            if state is None:
                continue
            score = -1 if state.is_hidden or state.sentiment == "dislike" else (
                1 if state.sentiment == "like" or state.is_favorite else 0)
            if not score:
                continue
            event = latest_opinion[article.id]
            groups[("source_preference", str(article.mp_id or ""))].append((event, score))
            for topic in item["topics"]:
                groups[("topic_preference", topic["slug"])].append((event, score))
    candidates = []
    for (rule_type, value), scored in groups.items():
        if not value or len(scored) < 3:
            continue
        total = sum(score for _, score in scored)
        confidence = abs(total) / len(scored)
        if confidence < 0.7:
            continue
        condition = {"source_ids" if rule_type == "source_preference" else "topic_slugs": [value]}
        action = {"rank_boost": 0.25} if total > 0 else {"rank_boost": -0.4, "collapse": True}
        candidates.append((rule_type, condition, action, confidence, [event.id for event, _ in scored[-10:]]))
    style_events = [event for event in latest_style.values() if event.value.get("style") in {"brief", "detailed"}]
    if len(style_events) >= 3:
        style, count = Counter(event.value["style"] for event in style_events).most_common(1)[0]
        if count / len(style_events) >= 0.7:
            candidates.append(("reading_preference", {}, {"summary_style": style}, count / len(style_events),
                               [event.id for event in style_events[-10:]]))
    previous = list(session.scalars(select(PreferenceRuleProposal).where(
        PreferenceRuleProposal.workspace_id == workspace_id, PreferenceRuleProposal.user_id == user_id)))
    active_proposals = set(session.scalars(select(PreferenceRule.proposal_id).where(
        PreferenceRule.workspace_id == workspace_id, PreferenceRule.user_id == user_id, PreferenceRule.is_active.is_(True))))
    created = []
    for kind, condition, action, confidence, evidence in candidates:
        key = (kind, json.dumps(condition, sort_keys=True), json.dumps(action, sort_keys=True))
        if any((row.rule_type, json.dumps(row.condition, sort_keys=True), json.dumps(row.action, sort_keys=True)) == key
               and (row.status == "pending" or row.id in active_proposals or set(row.evidence or []) == set(evidence))
               for row in previous):
            continue
        proposal = PreferenceRuleProposal(workspace_id=workspace_id, user_id=user_id, rule_type=kind,
                                          condition=condition, action=action, confidence=confidence, evidence=evidence)
        session.add(proposal)
        created.append(proposal)
    session.commit()
    for proposal in created:
        session.refresh(proposal)
    return created


def review_rule(session, *, workspace_id, user_id, proposal_id, approve):
    from .services import TenantService
    TenantService.require_membership(session, workspace_id, user_id)
    session.execute(update(Workspace).where(Workspace.id == workspace_id).values(updated_at=Workspace.updated_at))
    proposal = session.scalar(select(PreferenceRuleProposal).where(
        PreferenceRuleProposal.id == proposal_id, PreferenceRuleProposal.workspace_id == workspace_id,
        PreferenceRuleProposal.user_id == user_id,
    ).execution_options(populate_existing=True))
    if proposal is None:
        raise ValueError("preference proposal not found")
    requested = "approved" if approve else "rejected"
    if proposal.status != "pending":
        if proposal.status != requested:
            raise ValueError("proposal already reviewed with a different decision")
        session.commit()
        return proposal
    validate_rule(proposal.rule_type, proposal.condition, proposal.action)
    proposal.status, proposal.reviewed_at = requested, utcnow()
    if approve:
        for rule in session.scalars(select(PreferenceRule).where(
            PreferenceRule.workspace_id == workspace_id, PreferenceRule.user_id == user_id,
            PreferenceRule.rule_type == proposal.rule_type, PreferenceRule.is_active.is_(True),
        )):
            if rule.condition == proposal.condition:
                rule.is_active, rule.revoked_at, rule.version = False, utcnow(), rule.version + 1
        session.add(PreferenceRule(workspace_id=workspace_id, user_id=user_id, proposal_id=proposal.id,
                                   rule_type=proposal.rule_type, condition=proposal.condition, action=proposal.action))
        queue_preference_revisions(session, workspace_id, user_id, f"rule-approved:{proposal.id}")
    session.commit()
    session.refresh(proposal)
    return proposal


def revoke_rule(session, *, workspace_id, user_id, rule_id):
    from .services import AccessDenied, TenantService
    TenantService.require_membership(session, workspace_id, user_id)
    rule = session.scalar(select(PreferenceRule).where(PreferenceRule.id == rule_id,
        PreferenceRule.workspace_id == workspace_id, PreferenceRule.user_id == user_id))
    if rule is None:
        raise AccessDenied("preference rule not found")
    if rule.is_active:
        rule.is_active, rule.revoked_at, rule.version = False, utcnow(), rule.version + 1
        queue_preference_revisions(session, workspace_id, user_id, f"rule-revoked:{rule.id}:{rule.version}")
        session.commit()
    return rule


def validate_filter(value):
    value = dict(value)
    allowed = {"search", "source_id", "topic", "state_filter", "min_relevance", "date_from", "date_to", "order"}
    if set(value) - allowed:
        raise ValueError("unsupported saved filter field")
    for key, max_length in (("search", 120), ("source_id", 255), ("topic", 120)):
        if key in value and (not isinstance(value[key], str) or len(value[key]) > max_length):
            raise ValueError(f"invalid {key} filter")
    if value.get("state_filter", "") not in {"", "unread", "favorite", "hidden"}:
        raise ValueError("invalid state filter")
    if value.get("order", "relevance") not in {"relevance", "newest"}:
        raise ValueError("invalid filter order")
    if value.get("min_relevance") is not None:
        score = value["min_relevance"]
        if isinstance(score, bool) or not isinstance(score, (float, int)) or not math.isfinite(score) or not 0 <= score <= 1:
            raise ValueError("invalid relevance filter")
    for key in ("date_from", "date_to"):
        if value.get(key) is not None and (type(value[key]) is not int or value[key] < 0):
            raise ValueError("invalid date filter")
    if value.get("date_from") is not None and value.get("date_to") is not None and value["date_from"] > value["date_to"]:
        raise ValueError("filter start date must not follow end date")
    return value


def save_filter(session, *, workspace_id, user_id, name, filters):
    from .services import TenantService
    TenantService.require_membership(session, workspace_id, user_id)
    name = name.strip()
    if not name or len(name) > 100:
        raise ValueError("filter name must be 1..100 characters")
    filters = validate_filter(filters)
    session.execute(update(Workspace).where(Workspace.id == workspace_id).values(updated_at=Workspace.updated_at))
    saved = session.scalar(select(SavedFilter).where(SavedFilter.workspace_id == workspace_id,
        SavedFilter.user_id == user_id, SavedFilter.name == name))
    if saved is None:
        saved = SavedFilter(workspace_id=workspace_id, user_id=user_id, name=name)
        session.add(saved)
    saved.filters, saved.updated_at = filters, utcnow()
    session.commit()
    session.refresh(saved)
    return saved
