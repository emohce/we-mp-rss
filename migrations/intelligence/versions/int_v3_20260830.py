"""Frozen v3 correctness schema; DBA execution only, no business-data rewrite."""
from alembic import op
import sqlalchemy as sa

revision = "int_v3_20260830"
down_revision = "int_v2_20260824"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('int_request_budgets',
        sa.Column('scope_key', sa.String(length=240), nullable=False, primary_key=True),
        sa.Column('next_allowed_at', sa.DateTime(), nullable=False, primary_key=False),
        sa.Column('admitted_count', sa.Integer(), nullable=False, primary_key=False),
        sa.Column('version', sa.Integer(), nullable=False, primary_key=False),
    )
    op.create_table('int_connector_identities',
        sa.Column('identity_key', sa.String(length=64), nullable=False, primary_key=True),
        sa.Column('provider', sa.String(length=40), nullable=False, primary_key=False),
        sa.Column('source_id', sa.String(length=255), nullable=False, primary_key=False),
        sa.Column('external_id', sa.String(length=512), nullable=False, primary_key=False),
        sa.Column('article_id', sa.String(length=255), sa.ForeignKey('articles.id', ondelete='CASCADE'), nullable=False, primary_key=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, primary_key=False),
    )
    op.create_index('ix_int_connector_identities_article_id', 'int_connector_identities', ['article_id'], unique=False)
    op.create_index('ix_int_connector_identities_provider', 'int_connector_identities', ['provider'], unique=False)
    op.create_table('int_connector_usage',
        sa.Column('id', sa.String(length=32), nullable=False, primary_key=True),
        sa.Column('workspace_id', sa.String(length=32), sa.ForeignKey('int_workspaces.id', ondelete=None), nullable=False, primary_key=False),
        sa.Column('provider', sa.String(length=40), nullable=False, primary_key=False),
        sa.Column('operation', sa.String(length=40), nullable=False, primary_key=False),
        sa.Column('idempotency_key', sa.String(length=180), nullable=False, primary_key=False),
        sa.Column('status', sa.String(length=24), nullable=False, primary_key=False),
        sa.Column('units', sa.Integer(), nullable=False, primary_key=False),
        sa.Column('billable', sa.Boolean(), nullable=False, primary_key=False),
        sa.Column('error_code', sa.String(length=80), nullable=False, primary_key=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, primary_key=False),
        sa.Column('completed_at', sa.DateTime(), nullable=True, primary_key=False),
        sa.UniqueConstraint('idempotency_key', name=None),
    )
    op.create_index('ix_int_connector_usage_time', 'int_connector_usage', ['workspace_id', 'provider', 'created_at'], unique=False)
    op.create_table('int_daily_runs',
        sa.Column('id', sa.String(length=32), nullable=False, primary_key=True),
        sa.Column('workspace_id', sa.String(length=32), sa.ForeignKey('int_workspaces.id', ondelete=None), nullable=False, primary_key=False),
        sa.Column('run_date', sa.String(length=10), nullable=False, primary_key=False),
        sa.Column('cutoff_at', sa.DateTime(), nullable=False, primary_key=False),
        sa.Column('publish_after', sa.DateTime(), nullable=False, primary_key=False),
        sa.Column('collection_enabled', sa.Boolean(), nullable=False, primary_key=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, primary_key=False),
        sa.UniqueConstraint('workspace_id', 'run_date', name='uq_int_daily_run'),
    )
    op.create_table('int_saved_filters',
        sa.Column('id', sa.String(length=32), nullable=False, primary_key=True),
        sa.Column('workspace_id', sa.String(length=32), sa.ForeignKey('int_workspaces.id', ondelete=None), nullable=False, primary_key=False),
        sa.Column('user_id', sa.String(length=255), nullable=False, primary_key=False),
        sa.Column('name', sa.String(length=100), nullable=False, primary_key=False),
        sa.Column('filters', sa.JSON(), nullable=False, primary_key=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False, primary_key=False),
        sa.UniqueConstraint('workspace_id', 'user_id', 'name', name='uq_int_saved_filter'),
    )
    op.create_table('int_search_documents',
        sa.Column('article_id', sa.String(length=255), sa.ForeignKey('articles.id', ondelete='CASCADE'), nullable=False, primary_key=True),
        sa.Column('search_text', sa.Text(), nullable=False, primary_key=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False, primary_key=False),
    )
    op.create_table('int_source_checkpoints',
        sa.Column('id', sa.String(length=32), nullable=False, primary_key=True),
        sa.Column('account_id', sa.String(length=32), sa.ForeignKey('int_collector_accounts.id', ondelete=None), nullable=False, primary_key=False),
        sa.Column('source_id', sa.String(length=255), nullable=False, primary_key=False),
        sa.Column('mode', sa.String(length=20), nullable=False, primary_key=False),
        sa.Column('cursor', sa.JSON(), nullable=False, primary_key=False),
        sa.Column('head_ids', sa.JSON(), nullable=False, primary_key=False),
        sa.Column('version', sa.Integer(), nullable=False, primary_key=False),
        sa.Column('last_success_at', sa.DateTime(), nullable=True, primary_key=False),
        sa.Column('lease_token', sa.String(length=64), nullable=False, primary_key=False),
        sa.Column('lease_expires_at', sa.DateTime(), nullable=True, primary_key=False),
        sa.UniqueConstraint('account_id', 'source_id', 'mode', name='uq_int_checkpoint_mode'),
    )
    op.create_table('int_collection_runs',
        sa.Column('id', sa.String(length=32), nullable=False, primary_key=True),
        sa.Column('job_id', sa.String(length=32), sa.ForeignKey('int_collection_jobs.id', ondelete=None), nullable=False, primary_key=False),
        sa.Column('checkpoint_id', sa.String(length=32), sa.ForeignKey('int_source_checkpoints.id', ondelete=None), nullable=False, primary_key=False),
        sa.Column('mode', sa.String(length=20), nullable=False, primary_key=False),
        sa.Column('state', sa.String(length=24), nullable=False, primary_key=False),
        sa.Column('start_version', sa.Integer(), nullable=False, primary_key=False),
        sa.Column('cursor', sa.JSON(), nullable=False, primary_key=False),
        sa.Column('head_ids', sa.JSON(), nullable=False, primary_key=False),
        sa.Column('boundary_ids', sa.JSON(), nullable=False, primary_key=False),
        sa.Column('pages', sa.Integer(), nullable=False, primary_key=False),
        sa.Column('article_count', sa.Integer(), nullable=False, primary_key=False),
        sa.Column('started_at', sa.DateTime(), nullable=False, primary_key=False),
        sa.Column('finished_at', sa.DateTime(), nullable=True, primary_key=False),
        sa.Column('error_code', sa.String(length=80), nullable=False, primary_key=False),
        sa.UniqueConstraint('job_id', name=None),
    )
    op.create_table('int_daily_run_sources',
        sa.Column('id', sa.String(length=32), nullable=False, primary_key=True),
        sa.Column('daily_run_id', sa.String(length=32), sa.ForeignKey('int_daily_runs.id', ondelete='CASCADE'), nullable=False, primary_key=False),
        sa.Column('provider', sa.String(length=40), nullable=False, primary_key=False),
        sa.Column('source_id', sa.String(length=255), nullable=False, primary_key=False),
        sa.Column('job_id', sa.String(length=32), sa.ForeignKey('int_collection_jobs.id', ondelete='SET NULL'), nullable=True, primary_key=False),
        sa.Column('skipped_reason', sa.String(length=80), nullable=False, primary_key=False),
        sa.UniqueConstraint('daily_run_id', 'provider', 'source_id', name='uq_int_daily_source'),
    )
    op.create_table('int_digest_revisions',
        sa.Column('id', sa.String(length=32), nullable=False, primary_key=True),
        sa.Column('digest_id', sa.String(length=32), sa.ForeignKey('int_digests.id', ondelete='CASCADE'), nullable=False, primary_key=False),
        sa.Column('revision', sa.Integer(), nullable=False, primary_key=False),
        sa.Column('input_hash', sa.String(length=64), nullable=False, primary_key=False),
        sa.Column('snapshot', sa.JSON(), nullable=False, primary_key=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, primary_key=False),
        sa.UniqueConstraint('digest_id', 'revision', name='uq_int_digest_revision'),
    )
    op.add_column("int_preference_rules", sa.Column("version", sa.Integer(), nullable=False, server_default="1"))
    op.add_column("int_preference_rules", sa.Column("revoked_at", sa.DateTime(), nullable=True))
    op.add_column("int_digests", sa.Column("revision", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("int_digests", sa.Column("input_hash", sa.String(64), nullable=False, server_default=""))
    op.add_column("int_digests", sa.Column("coverage", sa.JSON(), nullable=False, server_default="{}"))
    op.create_index("uq_int_global_collector", "int_collector_accounts", ["provider", "label"],
                    unique=True, sqlite_where=sa.text("workspace_id IS NULL"),
                    postgresql_where=sa.text("workspace_id IS NULL"))
    dialect = op.get_context().dialect.name
    if dialect == "sqlite":
        op.execute("ALTER TABLE int_digests ADD COLUMN daily_run_id VARCHAR(32) REFERENCES int_daily_runs(id) ON DELETE SET NULL")
    else:
        op.add_column("int_digests", sa.Column("daily_run_id", sa.String(32), sa.ForeignKey("int_daily_runs.id", name="fk_int_digest_daily_run", ondelete="SET NULL")))
    op.drop_index("ix_int_article_content_blobs_content_hash", table_name="int_article_content_blobs")
    op.create_index("ix_int_article_content_blobs_content_hash", "int_article_content_blobs", ["content_hash"], unique=False)
    if dialect == "sqlite":
        op.execute("CREATE VIRTUAL TABLE int_search_fts USING fts5(article_id UNINDEXED, search_text, tokenize='trigram')")
        op.execute("CREATE TRIGGER int_search_ai AFTER INSERT ON int_search_documents BEGIN INSERT INTO int_search_fts(article_id, search_text) VALUES (new.article_id, new.search_text); END")
        op.execute("CREATE TRIGGER int_search_ad AFTER DELETE ON int_search_documents BEGIN DELETE FROM int_search_fts WHERE article_id = old.article_id; END")
        op.execute("CREATE TRIGGER int_search_au AFTER UPDATE ON int_search_documents BEGIN DELETE FROM int_search_fts WHERE article_id = old.article_id; INSERT INTO int_search_fts(article_id, search_text) VALUES (new.article_id, new.search_text); END")
    elif dialect == "postgresql":
        op.execute("CREATE INDEX ix_int_search_gin ON int_search_documents USING gin (to_tsvector('simple', search_text))")


def downgrade():
    raise RuntimeError("Destructive downgrade is not supported; use the reviewed DBA recovery plan.")
