"""advertising roas engine

Revision ID: 202606020008
Revises: 202606020007
Create Date: 2026-06-02 00:08:00.000000
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "202606020008"
down_revision: str | None = "202606020007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

PLATFORMS = "'META','INSTAGRAM','FACEBOOK','TIKTOK','GOOGLE','TELEGRAM','OTHER'"
CAMPAIGN_STATUSES = "'ACTIVE','PAUSED','COMPLETED','ARCHIVED'"
OBJECTIVES = "'MESSAGES','SALES','TRAFFIC','AWARENESS','FOLLOWERS','OTHER'"
BUDGET_TYPES = "'DAILY','LIFETIME','MANUAL'"


def upgrade() -> None:
    op.create_table(
        "ad_campaigns",
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("platform", sa.String(length=30), server_default="INSTAGRAM", nullable=False),
        sa.Column("status", sa.String(length=30), server_default="ACTIVE", nullable=False),
        sa.Column("objective", sa.String(length=30), server_default="MESSAGES", nullable=False),
        sa.Column("budget_type", sa.String(length=30), server_default="MANUAL", nullable=False),
        sa.Column("daily_budget", sa.Numeric(12, 2), nullable=True),
        sa.Column("total_budget", sa.Numeric(12, 2), nullable=True),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(f"platform IN ({PLATFORMS})", name="ck_ad_campaigns_platform"),
        sa.CheckConstraint(f"status IN ({CAMPAIGN_STATUSES})", name="ck_ad_campaigns_status"),
        sa.CheckConstraint(f"objective IN ({OBJECTIVES})", name="ck_ad_campaigns_objective"),
        sa.CheckConstraint(f"budget_type IN ({BUDGET_TYPES})", name="ck_ad_campaigns_budget_type"),
        sa.CheckConstraint("daily_budget IS NULL OR daily_budget >= 0", name="ck_ad_campaigns_daily_budget_non_negative"),
        sa.CheckConstraint("total_budget IS NULL OR total_budget >= 0", name="ck_ad_campaigns_total_budget_non_negative"),
        sa.ForeignKeyConstraint(["deleted_by"], ["users.id"], name=op.f("fk_ad_campaigns_deleted_by_users"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], name=op.f("fk_ad_campaigns_workspace_id_workspaces"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ad_campaigns")),
    )
    op.create_index(op.f("ix_ad_campaigns_workspace_id"), "ad_campaigns", ["workspace_id"], unique=False)
    op.create_index("ix_ad_campaigns_workspace_status", "ad_campaigns", ["workspace_id", "status"], unique=False)

    op.create_table(
        "ad_metrics",
        sa.Column("campaign_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("metric_date", sa.Date(), nullable=False),
        sa.Column("spend", sa.Numeric(12, 2), server_default="0", nullable=False),
        sa.Column("impressions", sa.Integer(), server_default="0", nullable=False),
        sa.Column("reach", sa.Integer(), server_default="0", nullable=False),
        sa.Column("clicks", sa.Integer(), server_default="0", nullable=False),
        sa.Column("messages", sa.Integer(), server_default="0", nullable=False),
        sa.Column("leads", sa.Integer(), server_default="0", nullable=False),
        sa.Column("orders", sa.Integer(), server_default="0", nullable=False),
        sa.Column("revenue", sa.Numeric(12, 2), server_default="0", nullable=False),
        sa.Column("net_profit", sa.Numeric(12, 2), server_default="0", nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("spend >= 0", name="ck_ad_metrics_spend_non_negative"),
        sa.CheckConstraint("impressions >= 0", name="ck_ad_metrics_impressions_non_negative"),
        sa.CheckConstraint("reach >= 0", name="ck_ad_metrics_reach_non_negative"),
        sa.CheckConstraint("clicks >= 0", name="ck_ad_metrics_clicks_non_negative"),
        sa.CheckConstraint("messages >= 0", name="ck_ad_metrics_messages_non_negative"),
        sa.CheckConstraint("leads >= 0", name="ck_ad_metrics_leads_non_negative"),
        sa.CheckConstraint("orders >= 0", name="ck_ad_metrics_orders_non_negative"),
        sa.CheckConstraint("revenue >= 0", name="ck_ad_metrics_revenue_non_negative"),
        sa.ForeignKeyConstraint(["campaign_id"], ["ad_campaigns.id"], name=op.f("fk_ad_metrics_campaign_id_ad_campaigns"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["deleted_by"], ["users.id"], name=op.f("fk_ad_metrics_deleted_by_users"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], name=op.f("fk_ad_metrics_workspace_id_workspaces"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ad_metrics")),
        sa.UniqueConstraint("campaign_id", "metric_date", name="uq_ad_metrics_campaign_id_metric_date"),
    )
    op.create_index(op.f("ix_ad_metrics_campaign_id"), "ad_metrics", ["campaign_id"], unique=False)
    op.create_index(op.f("ix_ad_metrics_metric_date"), "ad_metrics", ["metric_date"], unique=False)
    op.create_index(op.f("ix_ad_metrics_workspace_id"), "ad_metrics", ["workspace_id"], unique=False)
    op.create_index("ix_ad_metrics_workspace_date", "ad_metrics", ["workspace_id", "metric_date"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_ad_metrics_workspace_date", table_name="ad_metrics")
    op.drop_index(op.f("ix_ad_metrics_workspace_id"), table_name="ad_metrics")
    op.drop_index(op.f("ix_ad_metrics_metric_date"), table_name="ad_metrics")
    op.drop_index(op.f("ix_ad_metrics_campaign_id"), table_name="ad_metrics")
    op.drop_table("ad_metrics")
    op.drop_index("ix_ad_campaigns_workspace_status", table_name="ad_campaigns")
    op.drop_index(op.f("ix_ad_campaigns_workspace_id"), table_name="ad_campaigns")
    op.drop_table("ad_campaigns")
