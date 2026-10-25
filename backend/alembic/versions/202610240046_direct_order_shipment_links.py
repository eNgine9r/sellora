"""Add provenance-preserving 1:N shipment/order links for Direct conversations.

Revision ID: 202610240046
Revises: 202610230045
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "202610240046"
down_revision = "202610230045"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "direct_order_shipment_links",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", UUID(as_uuid=True),
                  sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False),
        sa.Column("conversation_id", UUID(as_uuid=True),
                  sa.ForeignKey("direct_conversations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("order_id", UUID(as_uuid=True),
                  sa.ForeignKey("orders.id", ondelete="CASCADE"), nullable=False),
        sa.Column("shipment_id", UUID(as_uuid=True),
                  sa.ForeignKey("shipments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_message_id", UUID(as_uuid=True),
                  sa.ForeignKey("direct_messages.id", ondelete="SET NULL")),
        sa.Column("evidence_type", sa.String(40), nullable=False),
        sa.Column("created_by", UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
        sa.Column("deleted_by", UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.UniqueConstraint("workspace_id", "conversation_id", "shipment_id",
                            name="uq_direct_order_shipment_links_workspace_conversation_shipment"),
        sa.CheckConstraint("evidence_type = 'EXACT_SHIPMENT_TTN'",
                           name="direct_order_shipment_links_exact_evidence"),
    )
    for col in ("workspace_id", "conversation_id", "order_id", "shipment_id"):
        op.create_index(
            f"ix_direct_order_shipment_links_{col}",
            "direct_order_shipment_links", [col]
        )
    op.execute("ALTER TABLE public.direct_order_shipment_links ENABLE ROW LEVEL SECURITY")
    for role in ("anon", "authenticated"):
        op.execute(f"""
            DO $$ BEGIN
              IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{role}') THEN
                REVOKE ALL PRIVILEGES ON TABLE public.direct_order_shipment_links FROM "{role}";
              END IF;
            END $$
        """)


def downgrade() -> None:
    # Never silently destroy reviewed historical linkage.
    bind = op.get_bind()
    if bind.execute(sa.text("SELECT EXISTS(SELECT 1 FROM direct_order_shipment_links)")).scalar():
        raise RuntimeError("Cannot drop existing historical Direct order links")
    op.drop_table("direct_order_shipment_links")