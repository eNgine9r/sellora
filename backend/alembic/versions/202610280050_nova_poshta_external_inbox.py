"""Provider-only external TTN inbox; never create synthetic orders.

Revision ID: 202610280050
Revises: 202610270049
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "202610280050"
down_revision = "202610270049"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if op.get_bind().dialect.name == "postgresql":
        op.execute("SET LOCAL lock_timeout = '5s'")
    op.create_table(
        "nova_poshta_external_documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tracking_number", sa.String(32), nullable=False),
        sa.Column("document_ref", sa.String(120), nullable=True),
        sa.Column("provider_status", sa.String(255), nullable=True),
        sa.Column("match_state", sa.String(20), nullable=False, server_default="UNMATCHED"),
        sa.Column("matched_shipment_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["matched_shipment_id"], ["shipments.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["deleted_by"], ["users.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("workspace_id", "tracking_number", name="uq_np_external_workspace_tracking"),
        sa.CheckConstraint("match_state IN ('UNMATCHED','LINKED','CONFLICT')", name="match_state"),
    )
    op.create_index("ix_nova_poshta_external_documents_workspace_id", "nova_poshta_external_documents", ["workspace_id"])
    op.create_index("ix_np_external_workspace_match", "nova_poshta_external_documents", ["workspace_id", "match_state"])
    op.execute('ALTER TABLE public.nova_poshta_external_documents ENABLE ROW LEVEL SECURITY')
    for role_name in ("anon", "authenticated"):
        op.execute(f"""DO $$ BEGIN
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{role_name}') THEN
                REVOKE ALL PRIVILEGES ON TABLE public.nova_poshta_external_documents FROM "{role_name}";
            END IF;
        END $$""")


def downgrade() -> None:
    # No silent deletion of imported provider history.
    conn = op.get_bind()
    count = conn.execute(sa.text("SELECT count(*) FROM nova_poshta_external_documents")).scalar()
    if count:
        raise RuntimeError("External shipment evidence exists; rollback requires manual review")
    op.drop_index("ix_np_external_workspace_match", table_name="nova_poshta_external_documents")
    op.drop_index("ix_nova_poshta_external_documents_workspace_id", table_name="nova_poshta_external_documents")
    op.drop_table("nova_poshta_external_documents")
