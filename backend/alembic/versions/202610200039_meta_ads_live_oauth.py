"""Durable Meta Ads OAuth state and connection generation.

Revision ID: 202610200039
Revises: 202610200038
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "202610200039"
down_revision = "202610200038"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("meta_ad_connections", sa.Column("generation", sa.String(36), nullable=True))
    op.add_column("meta_ad_connections", sa.Column("last_sync_attempt_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("uq_meta_live_campaign_identity", "ad_campaigns",
        ["workspace_id", "external_account_id", "external_campaign_id"], unique=True,
        postgresql_where=sa.text("sync_source = 'meta_live' AND external_source = 'meta_ads'"))
    op.create_index("uq_meta_live_metric_identity", "ad_metrics",
        ["workspace_id", "external_account_id", "external_campaign_id", "metric_date"], unique=True,
        postgresql_where=sa.text("source_type = 'meta_live' AND external_source = 'meta_ads'"))
    op.create_table("meta_ads_oauth_states",
        sa.Column("state_hash", sa.String(64), primary_key=True),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("generation", sa.String(36), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_meta_ads_oauth_states_workspace_id", "meta_ads_oauth_states", ["workspace_id"])
    op.create_index("ix_meta_ads_oauth_states_expires_at", "meta_ads_oauth_states", ["expires_at"])
    op.execute("ALTER TABLE meta_ads_oauth_states ENABLE ROW LEVEL SECURITY")
    # RLS does not govern TRUNCATE. Remove inherited Supabase defaults as well.
    op.execute("REVOKE ALL PRIVILEGES ON TABLE public.meta_ads_oauth_states FROM PUBLIC")
    for role_name in ("anon", "authenticated"):
        op.execute(f"""
            DO $$ BEGIN
                IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{role_name}') THEN
                    REVOKE ALL PRIVILEGES ON TABLE public.meta_ads_oauth_states FROM "{role_name}";
                END IF;
            END $$
        """)
    # Backend table owner/service role keeps its established access; no public policy.


def downgrade():
    op.drop_index("uq_meta_live_metric_identity", table_name="ad_metrics")
    op.drop_index("uq_meta_live_campaign_identity", table_name="ad_campaigns")
    op.drop_table("meta_ads_oauth_states")
    op.drop_column("meta_ad_connections", "last_sync_attempt_at")
    op.drop_column("meta_ad_connections", "generation")
