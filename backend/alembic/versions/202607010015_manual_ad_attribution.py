"""manual advertising attribution links

Revision ID: 202607010015
Revises: 202606110014
Create Date: 2026-07-01 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "202607010015"
down_revision = "202606110014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("leads", sa.Column("campaign_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_index("ix_leads_campaign_id", "leads", ["campaign_id"])
    op.create_foreign_key("fk_leads_campaign_id_ad_campaigns", "leads", "ad_campaigns", ["campaign_id"], ["id"], ondelete="SET NULL")

    op.add_column("orders", sa.Column("campaign_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_index("ix_orders_campaign_id", "orders", ["campaign_id"])
    op.create_foreign_key("fk_orders_campaign_id_ad_campaigns", "orders", "ad_campaigns", ["campaign_id"], ["id"], ondelete="SET NULL")


def downgrade() -> None:
    op.drop_constraint("fk_orders_campaign_id_ad_campaigns", "orders", type_="foreignkey")
    op.drop_index("ix_orders_campaign_id", table_name="orders")
    op.drop_column("orders", "campaign_id")

    op.drop_constraint("fk_leads_campaign_id_ad_campaigns", "leads", type_="foreignkey")
    op.drop_index("ix_leads_campaign_id", table_name="leads")
    op.drop_column("leads", "campaign_id")
