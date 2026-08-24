from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)

from core.models.base import Base


def new_id() -> str:
    return uuid.uuid4().hex


def utcnow() -> datetime:
    return datetime.utcnow()


class Workspace(Base):
    __tablename__ = "int_workspaces"

    id = Column(String(32), primary_key=True, default=new_id)
    name = Column(String(120), nullable=False)
    slug = Column(String(120), nullable=False, unique=True)
    owner_user_id = Column(String(255), nullable=False, index=True)
    created_at = Column(DateTime, nullable=False, default=utcnow)
    updated_at = Column(DateTime, nullable=False, default=utcnow, onupdate=utcnow)


class WorkspaceMembership(Base):
    __tablename__ = "int_workspace_memberships"
    __table_args__ = (
        UniqueConstraint("workspace_id", "user_id", name="uq_int_membership_workspace_user"),
    )

    id = Column(String(32), primary_key=True, default=new_id)
    workspace_id = Column(
        String(32), ForeignKey("int_workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id = Column(String(255), nullable=False, index=True)
    role = Column(String(24), nullable=False, default="member")
    created_at = Column(DateTime, nullable=False, default=utcnow)


class WorkspaceArticle(Base):
    __tablename__ = "int_workspace_articles"
    __table_args__ = (
        UniqueConstraint("workspace_id", "article_id", name="uq_int_workspace_article"),
        Index("ix_int_workspace_articles_added", "workspace_id", "added_at"),
    )

    id = Column(String(32), primary_key=True, default=new_id)
    workspace_id = Column(
        String(32), ForeignKey("int_workspaces.id", ondelete="CASCADE"), nullable=False
    )
    article_id = Column(
        String(255), ForeignKey("articles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    source_id = Column(String(255), nullable=False, index=True)
    ingestion_source = Column(String(40), nullable=False, default="we-mp-rss")
    added_at = Column(DateTime, nullable=False, default=utcnow)


class WorkspaceSubscription(Base):
    __tablename__ = "int_workspace_subscriptions"
    __table_args__ = (
        UniqueConstraint("workspace_id", "source_id", name="uq_int_workspace_subscription"),
        Index("ix_int_subscription_due", "status", "next_due_at"),
    )

    id = Column(String(32), primary_key=True, default=new_id)
    workspace_id = Column(
        String(32), ForeignKey("int_workspaces.id", ondelete="CASCADE"), nullable=False
    )
    source_id = Column(String(255), nullable=False, index=True)
    provider = Column(String(40), nullable=False, default="we-mp-rss")
    status = Column(String(24), nullable=False, default="active")
    discovery_mode = Column(String(24), nullable=False, default="latest_page")
    last_checked_at = Column(DateTime)
    next_due_at = Column(DateTime, nullable=False, default=utcnow)
    max_staleness_hours = Column(Integer, nullable=False, default=72)
    created_at = Column(DateTime, nullable=False, default=utcnow)
    updated_at = Column(DateTime, nullable=False, default=utcnow, onupdate=utcnow)


class UserArticleState(Base):
    __tablename__ = "int_user_article_states"
    __table_args__ = (
        UniqueConstraint(
            "workspace_id", "user_id", "article_id", name="uq_int_user_article_state"
        ),
        Index("ix_int_user_article_state_filter", "workspace_id", "user_id", "is_hidden"),
    )

    id = Column(String(32), primary_key=True, default=new_id)
    workspace_id = Column(
        String(32), ForeignKey("int_workspaces.id", ondelete="CASCADE"), nullable=False
    )
    user_id = Column(String(255), nullable=False, index=True)
    article_id = Column(
        String(255), ForeignKey("articles.id", ondelete="CASCADE"), nullable=False
    )
    is_read = Column(Boolean, nullable=False, default=False)
    is_favorite = Column(Boolean, nullable=False, default=False)
    is_hidden = Column(Boolean, nullable=False, default=False)
    sentiment = Column(String(16), nullable=False, default="")
    relevance_override = Column(Float)
    read_progress = Column(Float, nullable=False, default=0.0)
    updated_at = Column(DateTime, nullable=False, default=utcnow, onupdate=utcnow)


class ArticleContentBlob(Base):
    __tablename__ = "int_article_content_blobs"

    article_id = Column(
        String(255), ForeignKey("articles.id", ondelete="CASCADE"), primary_key=True
    )
    content_hash = Column(String(64), nullable=False, unique=True, index=True)
    storage_backend = Column(String(20), nullable=False, default="local")
    object_key = Column(String(600), nullable=False)
    media_type = Column(String(100), nullable=False, default="text/html")
    byte_size = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, nullable=False, default=utcnow)


class CollectorAccount(Base):
    __tablename__ = "int_collector_accounts"
    __table_args__ = (
        UniqueConstraint("workspace_id", "provider", "label", name="uq_int_collector_label"),
    )

    id = Column(String(32), primary_key=True, default=new_id)
    workspace_id = Column(String(32), ForeignKey("int_workspaces.id", ondelete="CASCADE"))
    provider = Column(String(40), nullable=False, index=True)
    label = Column(String(120), nullable=False)
    status = Column(String(24), nullable=False, default="healthy", index=True)
    secret_ref = Column(String(255), nullable=False, default="")
    last_error_code = Column(String(80), nullable=False, default="")
    created_at = Column(DateTime, nullable=False, default=utcnow)
    updated_at = Column(DateTime, nullable=False, default=utcnow, onupdate=utcnow)


class CollectorCursor(Base):
    __tablename__ = "int_collector_cursors"
    __table_args__ = (
        UniqueConstraint("account_id", "source_id", name="uq_int_collector_cursor"),
    )

    id = Column(String(32), primary_key=True, default=new_id)
    account_id = Column(
        String(32), ForeignKey("int_collector_accounts.id", ondelete="CASCADE"), nullable=False
    )
    source_id = Column(String(255), nullable=False, index=True)
    cursor = Column(JSON, nullable=False, default=dict)
    version = Column(Integer, nullable=False, default=0)
    last_persisted_at = Column(DateTime)


class CollectionJob(Base):
    __tablename__ = "int_collection_jobs"
    __table_args__ = (
        UniqueConstraint("idempotency_key", name="uq_int_collection_job_idempotency"),
        Index("ix_int_collection_job_claim", "state", "due_at", "priority"),
    )

    id = Column(String(32), primary_key=True, default=new_id)
    workspace_id = Column(
        String(32), ForeignKey("int_workspaces.id", ondelete="CASCADE"), nullable=False
    )
    account_id = Column(String(32), ForeignKey("int_collector_accounts.id", ondelete="SET NULL"))
    provider = Column(String(40), nullable=False, index=True)
    source_id = Column(String(255), nullable=False, index=True)
    kind = Column(String(40), nullable=False, default="discover")
    state = Column(String(24), nullable=False, default="queued", index=True)
    priority = Column(Integer, nullable=False, default=0)
    payload = Column(JSON, nullable=False, default=dict)
    idempotency_key = Column(String(160), nullable=False)
    attempts = Column(Integer, nullable=False, default=0)
    max_attempts = Column(Integer, nullable=False, default=8)
    due_at = Column(DateTime, nullable=False, default=utcnow)
    lease_token = Column(String(64), nullable=False, default="")
    lease_expires_at = Column(DateTime)
    last_error_code = Column(String(80), nullable=False, default="")
    last_error_message = Column(String(500), nullable=False, default="")
    created_at = Column(DateTime, nullable=False, default=utcnow)
    updated_at = Column(DateTime, nullable=False, default=utcnow, onupdate=utcnow)


class RateLimitLedger(Base):
    __tablename__ = "int_rate_limit_ledgers"
    __table_args__ = (
        UniqueConstraint("provider", "account_id", name="uq_int_rate_limit_account"),
    )

    id = Column(String(32), primary_key=True, default=new_id)
    provider = Column(String(40), nullable=False)
    account_id = Column(String(32), nullable=False)
    state = Column(String(24), nullable=False, default="healthy")
    failure_count = Column(Integer, nullable=False, default=0)
    cooldown_until = Column(DateTime)
    last_signal = Column(String(80), nullable=False, default="")
    updated_at = Column(DateTime, nullable=False, default=utcnow, onupdate=utcnow)


class Topic(Base):
    __tablename__ = "int_topics"

    id = Column(String(32), primary_key=True, default=new_id)
    slug = Column(String(120), nullable=False, unique=True)
    name = Column(String(120), nullable=False)
    description = Column(Text, nullable=False, default="")
    created_at = Column(DateTime, nullable=False, default=utcnow)


class ArticleTopic(Base):
    __tablename__ = "int_article_topics"
    __table_args__ = (
        UniqueConstraint(
            "workspace_id",
            "article_id",
            "topic_id",
            "analysis_version",
            name="uq_int_article_topic_workspace",
        ),
    )

    id = Column(String(32), primary_key=True, default=new_id)
    workspace_id = Column(
        String(32), ForeignKey("int_workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    article_id = Column(String(255), ForeignKey("articles.id", ondelete="CASCADE"), nullable=False)
    topic_id = Column(String(32), ForeignKey("int_topics.id", ondelete="CASCADE"), nullable=False)
    confidence = Column(Float, nullable=False, default=0.0)
    analysis_version = Column(String(80), nullable=False, default="heuristic-v1")
    created_at = Column(DateTime, nullable=False, default=utcnow)


class AnalysisRun(Base):
    __tablename__ = "int_analysis_runs"

    id = Column(String(32), primary_key=True, default=new_id)
    workspace_id = Column(String(32), ForeignKey("int_workspaces.id", ondelete="CASCADE"))
    article_id = Column(String(255), ForeignKey("articles.id", ondelete="CASCADE"), nullable=False)
    provider = Column(String(40), nullable=False)
    model = Column(String(120), nullable=False, default="")
    prompt_version = Column(String(80), nullable=False)
    status = Column(String(24), nullable=False, default="completed")
    summary = Column(Text, nullable=False, default="")
    output = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime, nullable=False, default=utcnow)


class SourceProfile(Base):
    __tablename__ = "int_source_profiles"
    __table_args__ = (
        UniqueConstraint("workspace_id", "source_id", name="uq_int_source_profile"),
    )

    id = Column(String(32), primary_key=True, default=new_id)
    workspace_id = Column(String(32), ForeignKey("int_workspaces.id", ondelete="CASCADE"), nullable=False)
    source_id = Column(String(255), nullable=False, index=True)
    summary = Column(Text, nullable=False, default="")
    topics = Column(JSON, nullable=False, default=list)
    sample_count = Column(Integer, nullable=False, default=0)
    confidence = Column(Float, nullable=False, default=0.0)
    window_start = Column(DateTime)
    window_end = Column(DateTime)
    updated_at = Column(DateTime, nullable=False, default=utcnow, onupdate=utcnow)


class FeedbackEvent(Base):
    __tablename__ = "int_feedback_events"
    __table_args__ = (
        Index("ix_int_feedback_user_time", "workspace_id", "user_id", "created_at"),
    )

    id = Column(String(32), primary_key=True, default=new_id)
    workspace_id = Column(String(32), ForeignKey("int_workspaces.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(String(255), nullable=False)
    article_id = Column(String(255), ForeignKey("articles.id", ondelete="CASCADE"), nullable=False)
    event_type = Column(String(40), nullable=False)
    value = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime, nullable=False, default=utcnow)


class PreferenceRuleProposal(Base):
    __tablename__ = "int_preference_rule_proposals"

    id = Column(String(32), primary_key=True, default=new_id)
    workspace_id = Column(String(32), ForeignKey("int_workspaces.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(String(255), nullable=False, index=True)
    status = Column(String(24), nullable=False, default="pending")
    rule_type = Column(String(40), nullable=False)
    condition = Column(JSON, nullable=False, default=dict)
    action = Column(JSON, nullable=False, default=dict)
    confidence = Column(Float, nullable=False, default=0.0)
    evidence = Column(JSON, nullable=False, default=list)
    created_at = Column(DateTime, nullable=False, default=utcnow)
    reviewed_at = Column(DateTime)


class PreferenceRule(Base):
    __tablename__ = "int_preference_rules"

    id = Column(String(32), primary_key=True, default=new_id)
    workspace_id = Column(String(32), ForeignKey("int_workspaces.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(String(255), nullable=False, index=True)
    proposal_id = Column(String(32), ForeignKey("int_preference_rule_proposals.id", ondelete="SET NULL"))
    rule_type = Column(String(40), nullable=False)
    condition = Column(JSON, nullable=False, default=dict)
    action = Column(JSON, nullable=False, default=dict)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=utcnow)


class Digest(Base):
    __tablename__ = "int_digests"
    __table_args__ = (
        UniqueConstraint("workspace_id", "user_id", "digest_date", name="uq_int_daily_digest"),
    )

    id = Column(String(32), primary_key=True, default=new_id)
    workspace_id = Column(String(32), ForeignKey("int_workspaces.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(String(255), nullable=False, index=True)
    digest_date = Column(String(10), nullable=False, index=True)
    status = Column(String(24), nullable=False, default="draft")
    title = Column(String(240), nullable=False)
    summary = Column(Text, nullable=False, default="")
    generated_at = Column(DateTime)
    created_at = Column(DateTime, nullable=False, default=utcnow)


class DigestItem(Base):
    __tablename__ = "int_digest_items"
    __table_args__ = (
        UniqueConstraint("digest_id", "article_id", name="uq_int_digest_article"),
        Index("ix_int_digest_item_rank", "digest_id", "rank"),
    )

    id = Column(String(32), primary_key=True, default=new_id)
    digest_id = Column(String(32), ForeignKey("int_digests.id", ondelete="CASCADE"), nullable=False)
    article_id = Column(String(255), ForeignKey("articles.id", ondelete="CASCADE"), nullable=False)
    rank = Column(Integer, nullable=False, default=0)
    relevance_score = Column(Float, nullable=False, default=0.0)
    reason = Column(String(500), nullable=False, default="")
    is_late = Column(Boolean, nullable=False, default=False)


class ShareLink(Base):
    __tablename__ = "int_share_links"

    id = Column(String(32), primary_key=True, default=new_id)
    workspace_id = Column(String(32), ForeignKey("int_workspaces.id", ondelete="CASCADE"), nullable=False)
    digest_id = Column(String(32), ForeignKey("int_digests.id", ondelete="CASCADE"), nullable=False)
    token_hash = Column(String(64), nullable=False, unique=True)
    expires_at = Column(DateTime)
    revoked_at = Column(DateTime)
    created_at = Column(DateTime, nullable=False, default=utcnow)


class ExportJob(Base):
    __tablename__ = "int_export_jobs"
    __table_args__ = (Index("ix_int_export_user_time", "workspace_id", "user_id", "created_at"),)

    id = Column(String(32), primary_key=True, default=new_id)
    workspace_id = Column(String(32), ForeignKey("int_workspaces.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(String(255), nullable=False)
    article_id = Column(String(255), ForeignKey("articles.id", ondelete="SET NULL"))
    format = Column(String(20), nullable=False)
    state = Column(String(24), nullable=False, default="queued")
    object_key = Column(String(600), nullable=False, default="")
    error_message = Column(String(500), nullable=False, default="")
    created_at = Column(DateTime, nullable=False, default=utcnow)
    completed_at = Column(DateTime)


class WorkflowJob(Base):
    __tablename__ = "int_workflow_jobs"
    __table_args__ = (
        UniqueConstraint("idempotency_key", name="uq_int_workflow_job_idempotency"),
        Index("ix_int_workflow_job_claim", "state", "due_at", "priority"),
    )

    id = Column(String(32), primary_key=True, default=new_id)
    workspace_id = Column(
        String(32), ForeignKey("int_workspaces.id", ondelete="CASCADE"), nullable=False
    )
    user_id = Column(String(255), nullable=False, default="", index=True)
    kind = Column(String(40), nullable=False, index=True)
    state = Column(String(24), nullable=False, default="queued", index=True)
    payload = Column(JSON, nullable=False, default=dict)
    idempotency_key = Column(String(180), nullable=False)
    priority = Column(Integer, nullable=False, default=0)
    attempts = Column(Integer, nullable=False, default=0)
    max_attempts = Column(Integer, nullable=False, default=8)
    due_at = Column(DateTime, nullable=False, default=utcnow)
    lease_token = Column(String(64), nullable=False, default="")
    lease_expires_at = Column(DateTime)
    last_error = Column(String(500), nullable=False, default="")
    created_at = Column(DateTime, nullable=False, default=utcnow)
    updated_at = Column(DateTime, nullable=False, default=utcnow, onupdate=utcnow)
    completed_at = Column(DateTime)


class DeliveryChannel(Base):
    __tablename__ = "int_delivery_channels"

    id = Column(String(32), primary_key=True, default=new_id)
    workspace_id = Column(String(32), ForeignKey("int_workspaces.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(String(255), nullable=False, index=True)
    channel_type = Column(String(32), nullable=False)
    name = Column(String(120), nullable=False)
    secret_ref = Column(String(255), nullable=False, default="")
    config = Column(JSON, nullable=False, default=dict)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=utcnow)


class OutboxEvent(Base):
    __tablename__ = "int_outbox_events"
    __table_args__ = (
        UniqueConstraint("idempotency_key", name="uq_int_outbox_idempotency"),
        Index("ix_int_outbox_dispatch", "state", "available_at"),
    )

    id = Column(String(32), primary_key=True, default=new_id)
    workspace_id = Column(String(32), ForeignKey("int_workspaces.id", ondelete="CASCADE"))
    event_type = Column(String(100), nullable=False)
    aggregate_type = Column(String(60), nullable=False)
    aggregate_id = Column(String(255), nullable=False)
    payload = Column(JSON, nullable=False, default=dict)
    idempotency_key = Column(String(160), nullable=False)
    state = Column(String(24), nullable=False, default="pending")
    attempts = Column(Integer, nullable=False, default=0)
    max_attempts = Column(Integer, nullable=False, default=12)
    available_at = Column(DateTime, nullable=False, default=utcnow)
    lease_token = Column(String(64), nullable=False, default="")
    lease_expires_at = Column(DateTime)
    last_error = Column(String(500), nullable=False, default="")
    created_at = Column(DateTime, nullable=False, default=utcnow)
    delivered_at = Column(DateTime)
