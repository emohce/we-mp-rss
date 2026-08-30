from __future__ import annotations

import html
import json
import re
from datetime import date
from typing import Annotated
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import distinct, func, select
from sqlalchemy.orm import Session

from core.auth import get_current_user_or_ak
from core.config import cfg
from core.db import DB
from core.intelligence.exporting import SingleArticleExporter
from core.intelligence.models import (
    ArticleTopic,
    Digest,
    DigestRevision,
    PreferenceRuleProposal,
    SourceProfile,
    Topic,
    WorkspaceArticle,
    WorkspaceSubscription,
)
from core.intelligence.scheduling import DEFAULT_SCHEDULE
from core.intelligence.services import (
    AccessDenied,
    AnalysisService,
    ArticleService,
    DigestService,
    FeedbackService,
    SubscriptionService,
    TenantService,
)
from core.intelligence.settings import InfrastructureSettings

from .base import error_response, success_response


router = APIRouter(tags=["智能聚合 v2"])
public_router = APIRouter(tags=["公开日报"])


def get_intelligence_session():
    session = DB.session_factory()
    try:
        yield session
    finally:
        session.close()


SessionDependency = Annotated[Session, Depends(get_intelligence_session)]
CurrentUser = Annotated[dict, Depends(get_current_user_or_ak)]


def _identity(current_user: dict) -> tuple[str, str]:
    original_user = current_user.get("original_user")
    user_id = current_user.get("user_id") or getattr(original_user, "id", None)
    username = current_user.get("username") or getattr(original_user, "username", None)
    if not user_id or not username:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=error_response(40301, "该认证主体不能访问个人智能聚合数据"),
        )
    return str(user_id), str(username)


def _service_error(exc: Exception) -> HTTPException:
    if isinstance(exc, AccessDenied):
        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=error_response(40401, str(exc)),
        )
    if isinstance(exc, (ValueError, TypeError)):
        return HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_response(40001, str(exc)),
        )
    if isinstance(exc, RuntimeError):
        return HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=error_response(50301, str(exc)),
        )
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=error_response(50001, "智能聚合服务执行失败"),
    )


class FeedbackRequest(BaseModel):
    event_type: str = Field(min_length=1, max_length=40)
    value: dict = Field(default_factory=dict)

    @field_validator("value")
    @classmethod
    def feedback_payload_is_bounded(cls, value: dict) -> dict:
        if len(json.dumps(value, ensure_ascii=False, default=str).encode("utf-8")) > 16_384:
            raise ValueError("feedback value must not exceed 16 KiB")
        return value


class SubscribeRequest(BaseModel):
    source_id: str = Field(min_length=1, max_length=255)
    provider: str = Field(default="we-mp-rss", pattern="^(we-mp-rss|paid-api)$")

    @field_validator("source_id")
    @classmethod
    def source_id_is_not_blank(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("source_id must not be blank")
        return normalized


class ProposalReviewRequest(BaseModel):
    approve: bool


class ShareRequest(BaseModel):
    expires_in_hours: int = Field(default=168, ge=1, le=2160)


def _proposal_data(proposal: PreferenceRuleProposal) -> dict:
    return {
        "id": proposal.id,
        "status": proposal.status,
        "rule_type": proposal.rule_type,
        "condition": proposal.condition,
        "action": proposal.action,
        "confidence": proposal.confidence,
        "evidence": proposal.evidence,
        "created_at": proposal.created_at,
        "reviewed_at": proposal.reviewed_at,
    }


@router.get("/infrastructure", summary="查看无密钥的基础设施状态")
def infrastructure_status(current_user: CurrentUser):
    _identity(current_user)
    settings = InfrastructureSettings.from_env(cfg.get)
    issues = settings.validate()
    return success_response(
        {
            **settings.describe(),
            "valid": not issues,
            "issues": issues,
            "schedule": {
                "timezone": str(DEFAULT_SCHEDULE.timezone),
                "collect_at": DEFAULT_SCHEDULE.collect_at.isoformat(timespec="minutes"),
                "cutoff_at": DEFAULT_SCHEDULE.cutoff_at.isoformat(timespec="minutes"),
                "digest_at": DEFAULT_SCHEDULE.digest_at.isoformat(timespec="minutes"),
                "next_run": DEFAULT_SCHEDULE.next_run(),
            },
        }
    )


@router.post("/workspaces/bootstrap", summary="创建或返回个人工作区")
def bootstrap_workspace(session: SessionDependency, current_user: CurrentUser):
    user_id, username = _identity(current_user)
    try:
        workspace = TenantService.bootstrap_personal_workspace(session, user_id, username)
        if current_user.get("role") == "admin":
            backfill = TenantService.attach_legacy_articles(
                session,
                workspace_id=workspace.id,
                user_id=user_id,
                authorized=True,
            )
        else:
            backfill = {
                "attached": 0,
                "has_more": False,
                "skipped": "admin_required",
            }
        return success_response(
            {
                "id": workspace.id,
                "name": workspace.name,
                "slug": workspace.slug,
                "legacy_backfill": backfill,
            }
        )
    except Exception as exc:
        raise _service_error(exc) from exc


@router.get("/articles", summary="按主题、状态、来源和相关度过滤文章")
def list_articles(
    session: SessionDependency,
    current_user: CurrentUser,
    workspace_id: str = Query(min_length=1, max_length=32),
    limit: int = Query(default=30, ge=1, le=100),
    cursor: str = Query(default="", max_length=400),
    search: str = Query(default="", max_length=120),
    source_id: str = Query(default="", max_length=255),
    topic: str = Query(default="", max_length=120),
    state_filter: str = Query(default="", pattern="^(|favorite|unread|hidden)$"),
    min_relevance: float | None = Query(default=None, ge=0, le=1),
    date_from: int | None = Query(default=None, ge=0),
    date_to: int | None = Query(default=None, ge=0),
):
    user_id, _ = _identity(current_user)
    try:
        return success_response(
            ArticleService.list_articles(
                session,
                workspace_id=workspace_id,
                user_id=user_id,
                limit=limit,
                cursor=cursor,
                search=search,
                source_id=source_id,
                topic=topic,
                state_filter=state_filter,
                min_relevance=min_relevance,
                date_from=date_from,
                date_to=date_to,
            )
        )
    except Exception as exc:
        raise _service_error(exc) from exc


@router.get("/articles/{article_id}", summary="查看单篇文章及智能分析")
def get_article(
    article_id: str,
    session: SessionDependency,
    current_user: CurrentUser,
    workspace_id: str = Query(min_length=1, max_length=32),
):
    user_id, _ = _identity(current_user)
    try:
        return success_response(
            ArticleService.get_article(
                session,
                workspace_id=workspace_id,
                user_id=user_id,
                article_id=article_id,
            )
        )
    except Exception as exc:
        raise _service_error(exc) from exc


@router.get("/articles/{article_id}/download", summary="下载单篇文章")
def download_article(
    article_id: str,
    session: SessionDependency,
    current_user: CurrentUser,
    workspace_id: str = Query(min_length=1, max_length=32),
    format_name: str = Query(default="md", alias="format", pattern="^(md|html|json|pdf|docx)$"),
):
    user_id, _ = _identity(current_user)
    try:
        article = ArticleService.get_article(
            session,
            workspace_id=workspace_id,
            user_id=user_id,
            article_id=article_id,
        )
        artifact = SingleArticleExporter().export(article, format_name)
        return Response(
            content=artifact.content,
            media_type=artifact.media_type,
            headers={
                "Content-Disposition": f"attachment; filename*=UTF-8''{quote(artifact.filename)}",
                "X-Content-Type-Options": "nosniff",
            },
        )
    except Exception as exc:
        raise _service_error(exc) from exc


@router.post("/articles/{article_id}/feedback", summary="记录不可变的文章反馈")
def record_feedback(
    article_id: str,
    payload: FeedbackRequest,
    session: SessionDependency,
    current_user: CurrentUser,
    workspace_id: str = Query(min_length=1, max_length=32),
):
    user_id, _ = _identity(current_user)
    try:
        event = FeedbackService.record(
            session,
            workspace_id=workspace_id,
            user_id=user_id,
            article_id=article_id,
            event_type=payload.event_type,
            value=payload.value,
        )
        return success_response(
            {
                "id": event.id,
                "article_id": event.article_id,
                "event_type": event.event_type,
                "value": event.value,
                "created_at": event.created_at,
            }
        )
    except Exception as exc:
        raise _service_error(exc) from exc


@router.post("/articles/{article_id}/analyze", summary="分析文章主题和摘要")
def analyze_article(
    article_id: str,
    session: SessionDependency,
    current_user: CurrentUser,
    workspace_id: str = Query(min_length=1, max_length=32),
):
    user_id, _ = _identity(current_user)
    try:
        result = AnalysisService().analyze_article(
            session,
            workspace_id=workspace_id,
            user_id=user_id,
            article_id=article_id,
        )
        return success_response(result.to_dict())
    except Exception as exc:
        raise _service_error(exc) from exc


@router.get("/topics", summary="汇总当前工作区的文章主题")
def list_topics(
    session: SessionDependency,
    current_user: CurrentUser,
    workspace_id: str = Query(min_length=1, max_length=32),
):
    user_id, _ = _identity(current_user)
    try:
        TenantService.require_membership(session, workspace_id, user_id)
        rows = session.execute(
            select(
                Topic.slug,
                Topic.name,
                func.count(distinct(ArticleTopic.article_id)),
                func.avg(ArticleTopic.confidence),
            )
            .join(ArticleTopic, ArticleTopic.topic_id == Topic.id)
            .join(WorkspaceArticle, WorkspaceArticle.article_id == ArticleTopic.article_id)
            .where(
                ArticleTopic.workspace_id == workspace_id,
                WorkspaceArticle.workspace_id == workspace_id,
            )
            .group_by(Topic.id, Topic.slug, Topic.name)
            .order_by(func.count(distinct(ArticleTopic.article_id)).desc(), Topic.name)
            .limit(100)
        ).all()
        return success_response(
            [
                {
                    "slug": slug,
                    "name": name,
                    "article_count": article_count,
                    "average_confidence": float(average_confidence or 0),
                }
                for slug, name, article_count, average_confidence in rows
            ]
        )
    except Exception as exc:
        raise _service_error(exc) from exc


@router.post("/sources/{source_id}/profile", summary="刷新公众号近期主题画像")
def refresh_source_profile(
    source_id: str,
    session: SessionDependency,
    current_user: CurrentUser,
    workspace_id: str = Query(min_length=1, max_length=32),
):
    user_id, _ = _identity(current_user)
    try:
        profile = AnalysisService.refresh_source_profile(
            session, workspace_id=workspace_id, user_id=user_id, source_id=source_id
        )
        return success_response(
            {
                "source_id": profile.source_id,
                "summary": profile.summary,
                "topics": profile.topics,
                "sample_count": profile.sample_count,
                "confidence": profile.confidence,
                "window_start": profile.window_start,
                "window_end": profile.window_end,
            }
        )
    except Exception as exc:
        raise _service_error(exc) from exc


@router.post("/subscriptions", summary="订阅公众号并排队单页发现任务")
def subscribe(
    payload: SubscribeRequest,
    session: SessionDependency,
    current_user: CurrentUser,
    workspace_id: str = Query(min_length=1, max_length=32),
):
    user_id, _ = _identity(current_user)
    try:
        subscription, job = SubscriptionService.subscribe(
            session,
            workspace_id=workspace_id,
            user_id=user_id,
            source_id=payload.source_id.strip(),
            provider=payload.provider.strip().lower(),
        )
        return success_response(
            {
                "subscription": {
                    "id": subscription.id,
                    "source_id": subscription.source_id,
                    "provider": subscription.provider,
                    "status": subscription.status,
                    "discovery_mode": subscription.discovery_mode,
                    "next_due_at": subscription.next_due_at,
                },
                "job": {"id": job.id, "state": job.state} if job else None,
            }
        )
    except Exception as exc:
        raise _service_error(exc) from exc


@router.get("/subscriptions", summary="列出当前工作区订阅")
def list_subscriptions(
    session: SessionDependency,
    current_user: CurrentUser,
    workspace_id: str = Query(min_length=1, max_length=32),
):
    user_id, _ = _identity(current_user)
    try:
        TenantService.require_membership(session, workspace_id, user_id)
        subscriptions = session.scalars(
            select(WorkspaceSubscription)
            .where(WorkspaceSubscription.workspace_id == workspace_id)
            .order_by(WorkspaceSubscription.created_at.desc())
        ).all()
        return success_response(
            [
                {
                    "id": item.id,
                    "source_id": item.source_id,
                    "provider": item.provider,
                    "status": item.status,
                    "discovery_mode": item.discovery_mode,
                    "last_checked_at": item.last_checked_at,
                    "next_due_at": item.next_due_at,
                }
                for item in subscriptions
            ]
        )
    except Exception as exc:
        raise _service_error(exc) from exc


@router.post("/preference-proposals/generate", summary="从反馈生成待确认偏好规则")
def generate_preference_proposals(
    session: SessionDependency,
    current_user: CurrentUser,
    workspace_id: str = Query(min_length=1, max_length=32),
):
    user_id, _ = _identity(current_user)
    try:
        proposals = FeedbackService.propose_preferences(
            session, workspace_id=workspace_id, user_id=user_id
        )
        return success_response([_proposal_data(item) for item in proposals])
    except Exception as exc:
        raise _service_error(exc) from exc


@router.get("/preference-proposals", summary="列出偏好规则建议")
def list_preference_proposals(
    session: SessionDependency,
    current_user: CurrentUser,
    workspace_id: str = Query(min_length=1, max_length=32),
    proposal_status: str = Query(default="pending", alias="status", pattern="^(pending|approved|rejected|all)$"),
):
    user_id, _ = _identity(current_user)
    try:
        TenantService.require_membership(session, workspace_id, user_id)
        query = select(PreferenceRuleProposal).where(
            PreferenceRuleProposal.workspace_id == workspace_id,
            PreferenceRuleProposal.user_id == user_id,
        )
        if proposal_status != "all":
            query = query.where(PreferenceRuleProposal.status == proposal_status)
        proposals = session.scalars(query.order_by(PreferenceRuleProposal.created_at.desc())).all()
        return success_response([_proposal_data(item) for item in proposals])
    except Exception as exc:
        raise _service_error(exc) from exc


@router.post("/preference-proposals/{proposal_id}/review", summary="批准或拒绝偏好规则")
def review_preference_proposal(
    proposal_id: str,
    payload: ProposalReviewRequest,
    session: SessionDependency,
    current_user: CurrentUser,
    workspace_id: str = Query(min_length=1, max_length=32),
):
    user_id, _ = _identity(current_user)
    try:
        proposal = FeedbackService.review_proposal(
            session,
            workspace_id=workspace_id,
            user_id=user_id,
            proposal_id=proposal_id,
            approve=payload.approve,
        )
        return success_response(_proposal_data(proposal))
    except Exception as exc:
        raise _service_error(exc) from exc


@router.post("/digests/{digest_date}/generate", summary="生成指定日期的个人日报")
def generate_digest(
    digest_date: date,
    session: SessionDependency,
    current_user: CurrentUser,
    workspace_id: str = Query(min_length=1, max_length=32),
):
    user_id, _ = _identity(current_user)
    try:
        DigestService.generate(
            session,
            workspace_id=workspace_id,
            user_id=user_id,
            digest_date=digest_date,
        )
        return success_response(
            DigestService.serialize(
                session,
                workspace_id=workspace_id,
                user_id=user_id,
                digest_date=digest_date.isoformat(),
            )
        )
    except Exception as exc:
        raise _service_error(exc) from exc


@router.get("/digests", summary="按日期倒序列出个人日报")
def list_digests(
    session: SessionDependency,
    current_user: CurrentUser,
    workspace_id: str = Query(min_length=1, max_length=32),
    limit: int = Query(default=60, ge=1, le=366),
):
    user_id, _ = _identity(current_user)
    try:
        return success_response(
            DigestService.list_digests(
                session,
                workspace_id=workspace_id,
                user_id=user_id,
                limit=limit,
            )
        )
    except Exception as exc:
        raise _service_error(exc) from exc


@router.get("/digests/{digest_date}", summary="查看指定日期的个人日报")
def get_digest(
    digest_date: date,
    session: SessionDependency,
    current_user: CurrentUser,
    workspace_id: str = Query(min_length=1, max_length=32),
):
    user_id, _ = _identity(current_user)
    try:
        return success_response(
            DigestService.serialize(
                session,
                workspace_id=workspace_id,
                user_id=user_id,
                digest_date=digest_date.isoformat(),
            )
        )
    except Exception as exc:
        raise _service_error(exc) from exc


@router.post("/digests/{digest_date}/share", summary="创建可过期的日报链接")
def share_digest(
    digest_date: date,
    payload: ShareRequest,
    session: SessionDependency,
    current_user: CurrentUser,
    workspace_id: str = Query(min_length=1, max_length=32),
):
    user_id, _ = _identity(current_user)
    try:
        link, token = DigestService.create_share_link(
            session,
            workspace_id=workspace_id,
            user_id=user_id,
            digest_date=digest_date.isoformat(),
            expires_in_hours=payload.expires_in_hours,
        )
        settings = InfrastructureSettings.from_env(cfg.get)
        relative_url = f"/share/digest/{token}"
        return success_response(
            {
                "id": link.id,
                "url": f"{settings.public_base_url}{relative_url}"
                if settings.public_base_url
                else relative_url,
                "expires_at": link.expires_at,
            }
        )
    except Exception as exc:
        raise _service_error(exc) from exc


@router.get("/share/digests/{token}", summary="读取公开日报 JSON")
def public_digest_json(token: str, session: SessionDependency):
    try:
        return success_response(DigestService.serialize_public_share(session, token))
    except Exception as exc:
        raise _service_error(exc) from exc


@router.post("/shares/{share_id}/revoke", summary="撤销自己创建的日报分享")
def revoke_digest_share(share_id: str, session: SessionDependency, current_user: CurrentUser,
                        workspace_id: str = Query(min_length=1, max_length=32)):
    user_id, _ = _identity(current_user)
    try:
        link = DigestService.revoke_share(session, workspace_id=workspace_id, user_id=user_id, share_id=share_id)
        return success_response({"id": link.id, "revoked_at": link.revoked_at})
    except Exception as exc:
        raise _service_error(exc) from exc


@router.get("/digests/{digest_date}/revisions", summary="读取日报修订历史")
def list_digest_revisions(digest_date: date, session: SessionDependency, current_user: CurrentUser,
                          workspace_id: str = Query(min_length=1, max_length=32)):
    user_id, _ = _identity(current_user)
    try:
        TenantService.require_membership(session, workspace_id, user_id)
        rows = session.scalars(select(DigestRevision).join(Digest, Digest.id == DigestRevision.digest_id).where(
            Digest.workspace_id == workspace_id, Digest.user_id == user_id,
            Digest.digest_date == digest_date.isoformat(),
        ).order_by(DigestRevision.revision.desc()).limit(100))
        return success_response([{"revision": row.revision, "created_at": row.created_at,
                                  "status": row.snapshot.get("status"), "coverage": row.snapshot.get("coverage", {}),
                                  "item_count": len(row.snapshot.get("items", []))} for row in rows])
    except Exception as exc:
        raise _service_error(exc) from exc


def _safe_web_url(value: object) -> str:
    url = str(value or "").strip()
    return url if re.match(r"^https?://", url, flags=re.I) else "#"


def _render_digest_page(data: dict) -> str:
    cards: list[str] = []
    for item in data.get("items", []):
        article = item.get("article") or {}
        title = html.escape(str(article.get("title") or "未命名文章"))
        summary = html.escape(str(article.get("ai_summary") or article.get("description") or ""))
        source = html.escape(str(article.get("mp_id") or ""))
        url = html.escape(_safe_web_url(article.get("url")), quote=True)
        topics = "".join(
            f"<span>{html.escape(str(topic.get('name') or ''))}</span>"
            for topic in article.get("topics") or []
        )
        cards.append(
            "<article class='card'>"
            f"<div class='rank'>{int(item.get('rank') or 0):02d}</div>"
            "<div class='card-body'>"
            f"<div class='meta'>{source}{topics}{'<span>迟到补录</span>' if item.get('is_late') else ''}</div>"
            f"<h2><a href='{url}' rel='noopener noreferrer' target='_blank'>{title}</a></h2>"
            f"<p>{summary}</p>"
            f"<small>{html.escape(str(item.get('reason') or ''))}</small>"
            "</div></article>"
        )
    day = html.escape(str(data.get("date") or ""))
    title = html.escape(str(data.get("title") or "微信公众号日报"))
    summary = html.escape(str(data.get("summary") or ""))
    completeness = "采集与分析已完成" if (data.get("coverage") or {}).get("complete") else "部分完成 · 尚有待采集或待分析内容"
    revision = int(data.get("revision") or 0)
    card_markup = "".join(cards) if cards else '<div class="empty">这一天暂无入选文章</div>'
    return (
        "<!doctype html><html lang='zh-CN'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        f"<title>{title}</title><style>"
        ":root{color-scheme:light;background:#f4f6f2;color:#172018;font-family:Inter,system-ui,-apple-system,'PingFang SC',sans-serif}"
        "*{box-sizing:border-box}body{margin:0}.shell{max-width:880px;margin:auto;padding:48px 20px 80px}"
        ".date{font:700 13px/1.2 ui-monospace,monospace;letter-spacing:.12em;color:#52735c}"
        "h1{font-size:clamp(30px,6vw,54px);line-height:1.05;margin:12px 0 16px}.lead{color:#5c685e;margin:0 0 36px}"
        ".card{display:flex;gap:18px;background:#fff;border:1px solid #dce4dc;border-radius:18px;padding:22px;margin:14px 0;box-shadow:0 8px 30px #203a2410}"
        ".rank{font:700 18px/1 ui-monospace;color:#7d9b84;padding-top:5px}.card-body{min-width:0}.meta{font-size:12px;color:#6d786f}"
        ".meta span{display:inline-block;margin-left:8px;padding:3px 8px;border-radius:99px;background:#edf4ee;color:#31563a}"
        "h2{font-size:20px;line-height:1.35;margin:8px 0}a{color:#172018;text-decoration:none}a:hover{text-decoration:underline}"
        "p{line-height:1.7;color:#475149;margin:8px 0}small{color:#768078}.empty{text-align:center;padding:56px;color:#768078}"
        "</style></head><body><main class='shell'>"
        f"<div class='date'>{day} · 修订 {revision}</div><h1>{title}</h1>"
        f"<p>{completeness}</p><p class='lead'>{summary}</p>"
        f"{card_markup}"
        "</main></body></html>"
    )


@public_router.get("/digest/{token}", response_class=HTMLResponse, include_in_schema=False)
def public_digest_page(token: str, session: SessionDependency):
    try:
        data = DigestService.serialize_public_share(session, token)
        return HTMLResponse(
            _render_digest_page(data),
            headers={
                "Cache-Control": "no-store",
                "Content-Security-Policy": (
                    "default-src 'none'; style-src 'unsafe-inline'; img-src https: data:; "
                    "base-uri 'none'; form-action 'none'; frame-ancestors 'none'"
                ),
                "Referrer-Policy": "no-referrer",
                "X-Content-Type-Options": "nosniff",
            },
        )
    except Exception as exc:
        raise _service_error(exc) from exc
