"""Frozen v2 intelligence baseline. Never import mutable application metadata."""
from alembic import op
import sqlalchemy as sa

revision = "int_v2_20260824"
down_revision = None
branch_labels = ("intelligence",)
depends_on = None


def upgrade():
    op.create_table('int_rate_limit_ledgers',
        sa.Column('id', sa.String(length=32), nullable=False, primary_key=True),
        sa.Column('provider', sa.String(length=40), nullable=False, primary_key=False),
        sa.Column('account_id', sa.String(length=32), nullable=False, primary_key=False),
        sa.Column('state', sa.String(length=24), nullable=False, primary_key=False),
        sa.Column('failure_count', sa.Integer(), nullable=False, primary_key=False),
        sa.Column('cooldown_until', sa.DateTime(), nullable=True, primary_key=False),
        sa.Column('last_signal', sa.String(length=80), nullable=False, primary_key=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False, primary_key=False),
        sa.UniqueConstraint('provider', 'account_id', name='uq_int_rate_limit_account'),
    )
    op.create_table('int_topics',
        sa.Column('id', sa.String(length=32), nullable=False, primary_key=True),
        sa.Column('slug', sa.String(length=120), nullable=False, primary_key=False),
        sa.Column('name', sa.String(length=120), nullable=False, primary_key=False),
        sa.Column('description', sa.Text(), nullable=False, primary_key=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, primary_key=False),
        sa.UniqueConstraint('slug', name=None),
    )
    op.create_table('int_workspaces',
        sa.Column('id', sa.String(length=32), nullable=False, primary_key=True),
        sa.Column('name', sa.String(length=120), nullable=False, primary_key=False),
        sa.Column('slug', sa.String(length=120), nullable=False, primary_key=False),
        sa.Column('owner_user_id', sa.String(length=255), nullable=False, primary_key=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, primary_key=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False, primary_key=False),
        sa.UniqueConstraint('slug', name=None),
    )
    op.create_index('ix_int_workspaces_owner_user_id', 'int_workspaces', ['owner_user_id'], unique=False)
    op.create_table('int_analysis_runs',
        sa.Column('id', sa.String(length=32), nullable=False, primary_key=True),
        sa.Column('workspace_id', sa.String(length=32), sa.ForeignKey('int_workspaces.id', ondelete='CASCADE'), nullable=True, primary_key=False),
        sa.Column('article_id', sa.String(length=255), sa.ForeignKey('articles.id', ondelete='CASCADE'), nullable=False, primary_key=False),
        sa.Column('provider', sa.String(length=40), nullable=False, primary_key=False),
        sa.Column('model', sa.String(length=120), nullable=False, primary_key=False),
        sa.Column('prompt_version', sa.String(length=80), nullable=False, primary_key=False),
        sa.Column('status', sa.String(length=24), nullable=False, primary_key=False),
        sa.Column('summary', sa.Text(), nullable=False, primary_key=False),
        sa.Column('output', sa.JSON(), nullable=False, primary_key=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, primary_key=False),
    )
    op.create_table('int_article_content_blobs',
        sa.Column('article_id', sa.String(length=255), sa.ForeignKey('articles.id', ondelete='CASCADE'), nullable=False, primary_key=True),
        sa.Column('content_hash', sa.String(length=64), nullable=False, primary_key=False),
        sa.Column('storage_backend', sa.String(length=20), nullable=False, primary_key=False),
        sa.Column('object_key', sa.String(length=600), nullable=False, primary_key=False),
        sa.Column('media_type', sa.String(length=100), nullable=False, primary_key=False),
        sa.Column('byte_size', sa.Integer(), nullable=False, primary_key=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, primary_key=False),
    )
    op.create_index('ix_int_article_content_blobs_content_hash', 'int_article_content_blobs', ['content_hash'], unique=True)
    op.create_table('int_article_topics',
        sa.Column('id', sa.String(length=32), nullable=False, primary_key=True),
        sa.Column('workspace_id', sa.String(length=32), sa.ForeignKey('int_workspaces.id', ondelete='CASCADE'), nullable=False, primary_key=False),
        sa.Column('article_id', sa.String(length=255), sa.ForeignKey('articles.id', ondelete='CASCADE'), nullable=False, primary_key=False),
        sa.Column('topic_id', sa.String(length=32), sa.ForeignKey('int_topics.id', ondelete='CASCADE'), nullable=False, primary_key=False),
        sa.Column('confidence', sa.Float(), nullable=False, primary_key=False),
        sa.Column('analysis_version', sa.String(length=80), nullable=False, primary_key=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, primary_key=False),
        sa.UniqueConstraint('workspace_id', 'article_id', 'topic_id', 'analysis_version', name='uq_int_article_topic_workspace'),
    )
    op.create_index('ix_int_article_topics_workspace_id', 'int_article_topics', ['workspace_id'], unique=False)
    op.create_table('int_collector_accounts',
        sa.Column('id', sa.String(length=32), nullable=False, primary_key=True),
        sa.Column('workspace_id', sa.String(length=32), sa.ForeignKey('int_workspaces.id', ondelete='CASCADE'), nullable=True, primary_key=False),
        sa.Column('provider', sa.String(length=40), nullable=False, primary_key=False),
        sa.Column('label', sa.String(length=120), nullable=False, primary_key=False),
        sa.Column('status', sa.String(length=24), nullable=False, primary_key=False),
        sa.Column('secret_ref', sa.String(length=255), nullable=False, primary_key=False),
        sa.Column('last_error_code', sa.String(length=80), nullable=False, primary_key=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, primary_key=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False, primary_key=False),
        sa.UniqueConstraint('workspace_id', 'provider', 'label', name='uq_int_collector_label'),
    )
    op.create_index('ix_int_collector_accounts_provider', 'int_collector_accounts', ['provider'], unique=False)
    op.create_index('ix_int_collector_accounts_status', 'int_collector_accounts', ['status'], unique=False)
    op.create_table('int_delivery_channels',
        sa.Column('id', sa.String(length=32), nullable=False, primary_key=True),
        sa.Column('workspace_id', sa.String(length=32), sa.ForeignKey('int_workspaces.id', ondelete='CASCADE'), nullable=False, primary_key=False),
        sa.Column('user_id', sa.String(length=255), nullable=False, primary_key=False),
        sa.Column('channel_type', sa.String(length=32), nullable=False, primary_key=False),
        sa.Column('name', sa.String(length=120), nullable=False, primary_key=False),
        sa.Column('secret_ref', sa.String(length=255), nullable=False, primary_key=False),
        sa.Column('config', sa.JSON(), nullable=False, primary_key=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, primary_key=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, primary_key=False),
    )
    op.create_index('ix_int_delivery_channels_user_id', 'int_delivery_channels', ['user_id'], unique=False)
    op.create_table('int_digests',
        sa.Column('id', sa.String(length=32), nullable=False, primary_key=True),
        sa.Column('workspace_id', sa.String(length=32), sa.ForeignKey('int_workspaces.id', ondelete='CASCADE'), nullable=False, primary_key=False),
        sa.Column('user_id', sa.String(length=255), nullable=False, primary_key=False),
        sa.Column('digest_date', sa.String(length=10), nullable=False, primary_key=False),
        sa.Column('status', sa.String(length=24), nullable=False, primary_key=False),
        sa.Column('title', sa.String(length=240), nullable=False, primary_key=False),
        sa.Column('summary', sa.Text(), nullable=False, primary_key=False),
        sa.Column('generated_at', sa.DateTime(), nullable=True, primary_key=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, primary_key=False),
        sa.UniqueConstraint('workspace_id', 'user_id', 'digest_date', name='uq_int_daily_digest'),
    )
    op.create_index('ix_int_digests_digest_date', 'int_digests', ['digest_date'], unique=False)
    op.create_index('ix_int_digests_user_id', 'int_digests', ['user_id'], unique=False)
    op.create_table('int_export_jobs',
        sa.Column('id', sa.String(length=32), nullable=False, primary_key=True),
        sa.Column('workspace_id', sa.String(length=32), sa.ForeignKey('int_workspaces.id', ondelete='CASCADE'), nullable=False, primary_key=False),
        sa.Column('user_id', sa.String(length=255), nullable=False, primary_key=False),
        sa.Column('article_id', sa.String(length=255), sa.ForeignKey('articles.id', ondelete='SET NULL'), nullable=True, primary_key=False),
        sa.Column('format', sa.String(length=20), nullable=False, primary_key=False),
        sa.Column('state', sa.String(length=24), nullable=False, primary_key=False),
        sa.Column('object_key', sa.String(length=600), nullable=False, primary_key=False),
        sa.Column('error_message', sa.String(length=500), nullable=False, primary_key=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, primary_key=False),
        sa.Column('completed_at', sa.DateTime(), nullable=True, primary_key=False),
    )
    op.create_index('ix_int_export_user_time', 'int_export_jobs', ['workspace_id', 'user_id', 'created_at'], unique=False)
    op.create_table('int_feedback_events',
        sa.Column('id', sa.String(length=32), nullable=False, primary_key=True),
        sa.Column('workspace_id', sa.String(length=32), sa.ForeignKey('int_workspaces.id', ondelete='CASCADE'), nullable=False, primary_key=False),
        sa.Column('user_id', sa.String(length=255), nullable=False, primary_key=False),
        sa.Column('article_id', sa.String(length=255), sa.ForeignKey('articles.id', ondelete='CASCADE'), nullable=False, primary_key=False),
        sa.Column('event_type', sa.String(length=40), nullable=False, primary_key=False),
        sa.Column('value', sa.JSON(), nullable=False, primary_key=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, primary_key=False),
    )
    op.create_index('ix_int_feedback_user_time', 'int_feedback_events', ['workspace_id', 'user_id', 'created_at'], unique=False)
    op.create_table('int_outbox_events',
        sa.Column('id', sa.String(length=32), nullable=False, primary_key=True),
        sa.Column('workspace_id', sa.String(length=32), sa.ForeignKey('int_workspaces.id', ondelete='CASCADE'), nullable=True, primary_key=False),
        sa.Column('event_type', sa.String(length=100), nullable=False, primary_key=False),
        sa.Column('aggregate_type', sa.String(length=60), nullable=False, primary_key=False),
        sa.Column('aggregate_id', sa.String(length=255), nullable=False, primary_key=False),
        sa.Column('payload', sa.JSON(), nullable=False, primary_key=False),
        sa.Column('idempotency_key', sa.String(length=160), nullable=False, primary_key=False),
        sa.Column('state', sa.String(length=24), nullable=False, primary_key=False),
        sa.Column('attempts', sa.Integer(), nullable=False, primary_key=False),
        sa.Column('max_attempts', sa.Integer(), nullable=False, primary_key=False),
        sa.Column('available_at', sa.DateTime(), nullable=False, primary_key=False),
        sa.Column('lease_token', sa.String(length=64), nullable=False, primary_key=False),
        sa.Column('lease_expires_at', sa.DateTime(), nullable=True, primary_key=False),
        sa.Column('last_error', sa.String(length=500), nullable=False, primary_key=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, primary_key=False),
        sa.Column('delivered_at', sa.DateTime(), nullable=True, primary_key=False),
        sa.UniqueConstraint('idempotency_key', name='uq_int_outbox_idempotency'),
    )
    op.create_index('ix_int_outbox_dispatch', 'int_outbox_events', ['state', 'available_at'], unique=False)
    op.create_table('int_preference_rule_proposals',
        sa.Column('id', sa.String(length=32), nullable=False, primary_key=True),
        sa.Column('workspace_id', sa.String(length=32), sa.ForeignKey('int_workspaces.id', ondelete='CASCADE'), nullable=False, primary_key=False),
        sa.Column('user_id', sa.String(length=255), nullable=False, primary_key=False),
        sa.Column('status', sa.String(length=24), nullable=False, primary_key=False),
        sa.Column('rule_type', sa.String(length=40), nullable=False, primary_key=False),
        sa.Column('condition', sa.JSON(), nullable=False, primary_key=False),
        sa.Column('action', sa.JSON(), nullable=False, primary_key=False),
        sa.Column('confidence', sa.Float(), nullable=False, primary_key=False),
        sa.Column('evidence', sa.JSON(), nullable=False, primary_key=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, primary_key=False),
        sa.Column('reviewed_at', sa.DateTime(), nullable=True, primary_key=False),
    )
    op.create_index('ix_int_preference_rule_proposals_user_id', 'int_preference_rule_proposals', ['user_id'], unique=False)
    op.create_table('int_source_profiles',
        sa.Column('id', sa.String(length=32), nullable=False, primary_key=True),
        sa.Column('workspace_id', sa.String(length=32), sa.ForeignKey('int_workspaces.id', ondelete='CASCADE'), nullable=False, primary_key=False),
        sa.Column('source_id', sa.String(length=255), nullable=False, primary_key=False),
        sa.Column('summary', sa.Text(), nullable=False, primary_key=False),
        sa.Column('topics', sa.JSON(), nullable=False, primary_key=False),
        sa.Column('sample_count', sa.Integer(), nullable=False, primary_key=False),
        sa.Column('confidence', sa.Float(), nullable=False, primary_key=False),
        sa.Column('window_start', sa.DateTime(), nullable=True, primary_key=False),
        sa.Column('window_end', sa.DateTime(), nullable=True, primary_key=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False, primary_key=False),
        sa.UniqueConstraint('workspace_id', 'source_id', name='uq_int_source_profile'),
    )
    op.create_index('ix_int_source_profiles_source_id', 'int_source_profiles', ['source_id'], unique=False)
    op.create_table('int_user_article_states',
        sa.Column('id', sa.String(length=32), nullable=False, primary_key=True),
        sa.Column('workspace_id', sa.String(length=32), sa.ForeignKey('int_workspaces.id', ondelete='CASCADE'), nullable=False, primary_key=False),
        sa.Column('user_id', sa.String(length=255), nullable=False, primary_key=False),
        sa.Column('article_id', sa.String(length=255), sa.ForeignKey('articles.id', ondelete='CASCADE'), nullable=False, primary_key=False),
        sa.Column('is_read', sa.Boolean(), nullable=False, primary_key=False),
        sa.Column('is_favorite', sa.Boolean(), nullable=False, primary_key=False),
        sa.Column('is_hidden', sa.Boolean(), nullable=False, primary_key=False),
        sa.Column('sentiment', sa.String(length=16), nullable=False, primary_key=False),
        sa.Column('relevance_override', sa.Float(), nullable=True, primary_key=False),
        sa.Column('read_progress', sa.Float(), nullable=False, primary_key=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False, primary_key=False),
        sa.UniqueConstraint('workspace_id', 'user_id', 'article_id', name='uq_int_user_article_state'),
    )
    op.create_index('ix_int_user_article_state_filter', 'int_user_article_states', ['workspace_id', 'user_id', 'is_hidden'], unique=False)
    op.create_index('ix_int_user_article_states_user_id', 'int_user_article_states', ['user_id'], unique=False)
    op.create_table('int_workflow_jobs',
        sa.Column('id', sa.String(length=32), nullable=False, primary_key=True),
        sa.Column('workspace_id', sa.String(length=32), sa.ForeignKey('int_workspaces.id', ondelete='CASCADE'), nullable=False, primary_key=False),
        sa.Column('user_id', sa.String(length=255), nullable=False, primary_key=False),
        sa.Column('kind', sa.String(length=40), nullable=False, primary_key=False),
        sa.Column('state', sa.String(length=24), nullable=False, primary_key=False),
        sa.Column('payload', sa.JSON(), nullable=False, primary_key=False),
        sa.Column('idempotency_key', sa.String(length=180), nullable=False, primary_key=False),
        sa.Column('priority', sa.Integer(), nullable=False, primary_key=False),
        sa.Column('attempts', sa.Integer(), nullable=False, primary_key=False),
        sa.Column('max_attempts', sa.Integer(), nullable=False, primary_key=False),
        sa.Column('due_at', sa.DateTime(), nullable=False, primary_key=False),
        sa.Column('lease_token', sa.String(length=64), nullable=False, primary_key=False),
        sa.Column('lease_expires_at', sa.DateTime(), nullable=True, primary_key=False),
        sa.Column('last_error', sa.String(length=500), nullable=False, primary_key=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, primary_key=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False, primary_key=False),
        sa.Column('completed_at', sa.DateTime(), nullable=True, primary_key=False),
        sa.UniqueConstraint('idempotency_key', name='uq_int_workflow_job_idempotency'),
    )
    op.create_index('ix_int_workflow_job_claim', 'int_workflow_jobs', ['state', 'due_at', 'priority'], unique=False)
    op.create_index('ix_int_workflow_jobs_kind', 'int_workflow_jobs', ['kind'], unique=False)
    op.create_index('ix_int_workflow_jobs_state', 'int_workflow_jobs', ['state'], unique=False)
    op.create_index('ix_int_workflow_jobs_user_id', 'int_workflow_jobs', ['user_id'], unique=False)
    op.create_table('int_workspace_articles',
        sa.Column('id', sa.String(length=32), nullable=False, primary_key=True),
        sa.Column('workspace_id', sa.String(length=32), sa.ForeignKey('int_workspaces.id', ondelete='CASCADE'), nullable=False, primary_key=False),
        sa.Column('article_id', sa.String(length=255), sa.ForeignKey('articles.id', ondelete='CASCADE'), nullable=False, primary_key=False),
        sa.Column('source_id', sa.String(length=255), nullable=False, primary_key=False),
        sa.Column('ingestion_source', sa.String(length=40), nullable=False, primary_key=False),
        sa.Column('added_at', sa.DateTime(), nullable=False, primary_key=False),
        sa.UniqueConstraint('workspace_id', 'article_id', name='uq_int_workspace_article'),
    )
    op.create_index('ix_int_workspace_articles_added', 'int_workspace_articles', ['workspace_id', 'added_at'], unique=False)
    op.create_index('ix_int_workspace_articles_article_id', 'int_workspace_articles', ['article_id'], unique=False)
    op.create_index('ix_int_workspace_articles_source_id', 'int_workspace_articles', ['source_id'], unique=False)
    op.create_table('int_workspace_memberships',
        sa.Column('id', sa.String(length=32), nullable=False, primary_key=True),
        sa.Column('workspace_id', sa.String(length=32), sa.ForeignKey('int_workspaces.id', ondelete='CASCADE'), nullable=False, primary_key=False),
        sa.Column('user_id', sa.String(length=255), nullable=False, primary_key=False),
        sa.Column('role', sa.String(length=24), nullable=False, primary_key=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, primary_key=False),
        sa.UniqueConstraint('workspace_id', 'user_id', name='uq_int_membership_workspace_user'),
    )
    op.create_index('ix_int_workspace_memberships_user_id', 'int_workspace_memberships', ['user_id'], unique=False)
    op.create_index('ix_int_workspace_memberships_workspace_id', 'int_workspace_memberships', ['workspace_id'], unique=False)
    op.create_table('int_workspace_subscriptions',
        sa.Column('id', sa.String(length=32), nullable=False, primary_key=True),
        sa.Column('workspace_id', sa.String(length=32), sa.ForeignKey('int_workspaces.id', ondelete='CASCADE'), nullable=False, primary_key=False),
        sa.Column('source_id', sa.String(length=255), nullable=False, primary_key=False),
        sa.Column('provider', sa.String(length=40), nullable=False, primary_key=False),
        sa.Column('status', sa.String(length=24), nullable=False, primary_key=False),
        sa.Column('discovery_mode', sa.String(length=24), nullable=False, primary_key=False),
        sa.Column('last_checked_at', sa.DateTime(), nullable=True, primary_key=False),
        sa.Column('next_due_at', sa.DateTime(), nullable=False, primary_key=False),
        sa.Column('max_staleness_hours', sa.Integer(), nullable=False, primary_key=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, primary_key=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False, primary_key=False),
        sa.UniqueConstraint('workspace_id', 'source_id', name='uq_int_workspace_subscription'),
    )
    op.create_index('ix_int_subscription_due', 'int_workspace_subscriptions', ['status', 'next_due_at'], unique=False)
    op.create_index('ix_int_workspace_subscriptions_source_id', 'int_workspace_subscriptions', ['source_id'], unique=False)
    op.create_table('int_collection_jobs',
        sa.Column('id', sa.String(length=32), nullable=False, primary_key=True),
        sa.Column('workspace_id', sa.String(length=32), sa.ForeignKey('int_workspaces.id', ondelete='CASCADE'), nullable=False, primary_key=False),
        sa.Column('account_id', sa.String(length=32), sa.ForeignKey('int_collector_accounts.id', ondelete='SET NULL'), nullable=True, primary_key=False),
        sa.Column('provider', sa.String(length=40), nullable=False, primary_key=False),
        sa.Column('source_id', sa.String(length=255), nullable=False, primary_key=False),
        sa.Column('kind', sa.String(length=40), nullable=False, primary_key=False),
        sa.Column('state', sa.String(length=24), nullable=False, primary_key=False),
        sa.Column('priority', sa.Integer(), nullable=False, primary_key=False),
        sa.Column('payload', sa.JSON(), nullable=False, primary_key=False),
        sa.Column('idempotency_key', sa.String(length=160), nullable=False, primary_key=False),
        sa.Column('attempts', sa.Integer(), nullable=False, primary_key=False),
        sa.Column('max_attempts', sa.Integer(), nullable=False, primary_key=False),
        sa.Column('due_at', sa.DateTime(), nullable=False, primary_key=False),
        sa.Column('lease_token', sa.String(length=64), nullable=False, primary_key=False),
        sa.Column('lease_expires_at', sa.DateTime(), nullable=True, primary_key=False),
        sa.Column('last_error_code', sa.String(length=80), nullable=False, primary_key=False),
        sa.Column('last_error_message', sa.String(length=500), nullable=False, primary_key=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, primary_key=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False, primary_key=False),
        sa.UniqueConstraint('idempotency_key', name='uq_int_collection_job_idempotency'),
    )
    op.create_index('ix_int_collection_job_claim', 'int_collection_jobs', ['state', 'due_at', 'priority'], unique=False)
    op.create_index('ix_int_collection_jobs_provider', 'int_collection_jobs', ['provider'], unique=False)
    op.create_index('ix_int_collection_jobs_source_id', 'int_collection_jobs', ['source_id'], unique=False)
    op.create_index('ix_int_collection_jobs_state', 'int_collection_jobs', ['state'], unique=False)
    op.create_table('int_collector_cursors',
        sa.Column('id', sa.String(length=32), nullable=False, primary_key=True),
        sa.Column('account_id', sa.String(length=32), sa.ForeignKey('int_collector_accounts.id', ondelete='CASCADE'), nullable=False, primary_key=False),
        sa.Column('source_id', sa.String(length=255), nullable=False, primary_key=False),
        sa.Column('cursor', sa.JSON(), nullable=False, primary_key=False),
        sa.Column('version', sa.Integer(), nullable=False, primary_key=False),
        sa.Column('last_persisted_at', sa.DateTime(), nullable=True, primary_key=False),
        sa.UniqueConstraint('account_id', 'source_id', name='uq_int_collector_cursor'),
    )
    op.create_index('ix_int_collector_cursors_source_id', 'int_collector_cursors', ['source_id'], unique=False)
    op.create_table('int_digest_items',
        sa.Column('id', sa.String(length=32), nullable=False, primary_key=True),
        sa.Column('digest_id', sa.String(length=32), sa.ForeignKey('int_digests.id', ondelete='CASCADE'), nullable=False, primary_key=False),
        sa.Column('article_id', sa.String(length=255), sa.ForeignKey('articles.id', ondelete='CASCADE'), nullable=False, primary_key=False),
        sa.Column('rank', sa.Integer(), nullable=False, primary_key=False),
        sa.Column('relevance_score', sa.Float(), nullable=False, primary_key=False),
        sa.Column('reason', sa.String(length=500), nullable=False, primary_key=False),
        sa.Column('is_late', sa.Boolean(), nullable=False, primary_key=False),
        sa.UniqueConstraint('digest_id', 'article_id', name='uq_int_digest_article'),
    )
    op.create_index('ix_int_digest_item_rank', 'int_digest_items', ['digest_id', 'rank'], unique=False)
    op.create_table('int_preference_rules',
        sa.Column('id', sa.String(length=32), nullable=False, primary_key=True),
        sa.Column('workspace_id', sa.String(length=32), sa.ForeignKey('int_workspaces.id', ondelete='CASCADE'), nullable=False, primary_key=False),
        sa.Column('user_id', sa.String(length=255), nullable=False, primary_key=False),
        sa.Column('proposal_id', sa.String(length=32), sa.ForeignKey('int_preference_rule_proposals.id', ondelete='SET NULL'), nullable=True, primary_key=False),
        sa.Column('rule_type', sa.String(length=40), nullable=False, primary_key=False),
        sa.Column('condition', sa.JSON(), nullable=False, primary_key=False),
        sa.Column('action', sa.JSON(), nullable=False, primary_key=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, primary_key=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, primary_key=False),
    )
    op.create_index('ix_int_preference_rules_user_id', 'int_preference_rules', ['user_id'], unique=False)
    op.create_table('int_share_links',
        sa.Column('id', sa.String(length=32), nullable=False, primary_key=True),
        sa.Column('workspace_id', sa.String(length=32), sa.ForeignKey('int_workspaces.id', ondelete='CASCADE'), nullable=False, primary_key=False),
        sa.Column('digest_id', sa.String(length=32), sa.ForeignKey('int_digests.id', ondelete='CASCADE'), nullable=False, primary_key=False),
        sa.Column('token_hash', sa.String(length=64), nullable=False, primary_key=False),
        sa.Column('expires_at', sa.DateTime(), nullable=True, primary_key=False),
        sa.Column('revoked_at', sa.DateTime(), nullable=True, primary_key=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, primary_key=False),
        sa.UniqueConstraint('token_hash', name=None),
    )


def downgrade():
    raise RuntimeError("Destructive downgrade is not supported; use the reviewed DBA recovery plan.")
