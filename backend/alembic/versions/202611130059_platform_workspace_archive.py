"""Add reversible workspace archival metadata for Platform Admin."""

import sqlalchemy as sa
from alembic import op

revision = "202611130059"
down_revision = "202611130058"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("SET LOCAL lock_timeout = '5s'")
    op.add_column("workspaces", sa.Column("archived_at", sa.DateTime(timezone=True)))
    op.add_column("workspaces", sa.Column("archived_was_active", sa.Boolean()))


def downgrade() -> None:
    op.execute("SET LOCAL lock_timeout = '5s'")
    op.execute("LOCK TABLE public.workspaces IN ACCESS EXCLUSIVE MODE")
    if op.get_bind().scalar(sa.text("SELECT EXISTS (SELECT 1 FROM public.workspaces WHERE archived_at IS NOT NULL)")):
        raise RuntimeError("Restore archived workspaces before dropping archive metadata")
    op.drop_column("workspaces", "archived_was_active")
    op.drop_column("workspaces", "archived_at")
