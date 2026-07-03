"""meta ads external identity fields

Revision ID: 202607010016
Revises: 202607010015
Create Date: 2026-07-01 00:16:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "202607010016"
down_revision: str | None = "202607010015"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("ad_campaigns", sa.Column("external_source", sa.String(length=50), nullable=True))
    op.add_column("ad_campaigns", sa.Column("external_account_id", sa.String(length=128), nullable=True))
    op.add_column("ad_campaigns", sa.Column("external_campaign_id", sa.String(length=128), nullable=True))
    op.add_column("ad_campaigns", sa.Column("external_status", sa.String(length=64), nullable=True))
    op.add_column("ad_campaigns", sa.Column("external_objective", sa.String(length=128), nullable=True))
    op.add_column("ad_campaigns", sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("ad_campaigns", sa.Column("sync_source", sa.String(length=32), nullable=True))
    op.create_index(
        "ix_ad_campaigns_workspace_external_identity",
        "ad_campaigns",
        ["workspace_id", "external_source", "external_account_id", "external_campaign_id"],
        unique=False,
    )

    op.add_column("ad_metrics", sa.Column("source_type", sa.String(length=32), nullable=True))
    op.add_column("ad_metrics", sa.Column("external_source", sa.String(length=50), nullable=True))
    op.add_column("ad_metrics", sa.Column("external_account_id", sa.String(length=128), nullable=True))
    op.add_column("ad_metrics", sa.Column("external_campaign_id", sa.String(length=128), nullable=True))
    op.add_column("ad_metrics", sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("ad_metrics", sa.Column("sync_run_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_index(
        "ix_ad_metrics_workspace_external_identity_date",
        "ad_metrics",
        ["workspace_id", "external_source", "external_account_id", "external_campaign_id", "metric_date"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_ad_metrics_workspace_external_identity_date", table_name="ad_metrics")
    op.drop_column("ad_metrics", "sync_run_id")
    op.drop_column("ad_metrics", "last_synced_at")
    op.drop_column("ad_metrics", "external_campaign_id")
    op.drop_column("ad_metrics", "external_account_id")
    op.drop_column("ad_metrics", "external_source")
    op.drop_column("ad_metrics", "source_type")

    op.drop_index("ix_ad_campaigns_workspace_external_identity", table_name="ad_campaigns")
    op.drop_column("ad_campaigns", "sync_source")
    op.drop_column("ad_campaigns", "last_synced_at")
    op.drop_column("ad_campaigns", "external_objective")
    op.drop_column("ad_campaigns", "external_status")
    op.drop_column("ad_campaigns", "external_campaign_id")
    op.drop_column("ad_campaigns", "external_account_id")
    op.drop_column("ad_campaigns", "external_source")
