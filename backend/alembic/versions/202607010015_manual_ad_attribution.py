"""manual advertising attribution

Revision ID: 202607010015
Revises: 202606110014
Create Date: 2026-07-01 00:15:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "202607010015"
down_revision: str | None = "202606110014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("leads", sa.Column("campaign_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("orders", sa.Column("campaign_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_index(op.f("ix_leads_campaign_id"), "leads", ["campaign_id"], unique=False)
    op.create_index(op.f("ix_orders_campaign_id"), "orders", ["campaign_id"], unique=False)
    op.create_foreign_key(op.f("fk_leads_campaign_id_ad_campaigns"), "leads", "ad_campaigns", ["campaign_id"], ["id"], ondelete="SET NULL")
    op.create_foreign_key(op.f("fk_orders_campaign_id_ad_campaigns"), "orders", "ad_campaigns", ["campaign_id"], ["id"], ondelete="SET NULL")


def downgrade() -> None:
    op.drop_constraint(op.f("fk_orders_campaign_id_ad_campaigns"), "orders", type_="foreignkey")
    op.drop_constraint(op.f("fk_leads_campaign_id_ad_campaigns"), "leads", type_="foreignkey")
    op.drop_index(op.f("ix_orders_campaign_id"), table_name="orders")
    op.drop_index(op.f("ix_leads_campaign_id"), table_name="leads")
    op.drop_column("orders", "campaign_id")
    op.drop_column("leads", "campaign_id")
