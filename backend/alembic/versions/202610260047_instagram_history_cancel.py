"""Allow cancelling Instagram history scans without waiting for the worker row lock.

Revision ID: 202610260047
Revises: 202610240046
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "202610260047"
down_revision = "202610240046"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "instagram_history_sync_cancel_requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sync_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("requested_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["sync_id"], ["instagram_history_syncs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["requested_by"], ["users.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("workspace_id", name="uq_ig_history_cancel_workspace"),
    )
    # Migration updates only the status check; it does not touch saved messages.
    op.drop_constraint("ck_instagram_history_syncs_status", "instagram_history_syncs", type_="check")
    op.create_check_constraint(
        "ck_instagram_history_syncs_status",
        "instagram_history_syncs",
        "status IN ('PENDING','RUNNING','COMPLETED','PARTIAL','RETRY_PENDING','FAILED_SAFE','CANCELLED')",
    )
    op.execute("ALTER TABLE instagram_history_sync_cancel_requests ENABLE ROW LEVEL SECURITY")


def downgrade() -> None:
    # Data-loss safe downgrade only when there are no CANCELLED status rows.
    op.create_check_constraint(
        "ck_instagram_history_syncs_status_old_guard",
        "instagram_history_syncs",
        "status IN ('PENDING','RUNNING','COMPLETED','PARTIAL','RETRY_PENDING','FAILED_SAFE')",
    )
    op.drop_constraint("ck_instagram_history_syncs_status", "instagram_history_syncs", type_="check")
    op.execute(
        "ALTER TABLE instagram_history_syncs RENAME CONSTRAINT "
        "ck_instagram_history_syncs_status_old_guard TO ck_instagram_history_syncs_status"
    )
    op.drop_table("instagram_history_sync_cancel_requests")
