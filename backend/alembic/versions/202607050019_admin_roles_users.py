"""admin roles users workspace management

Revision ID: 202607050019
Revises: 202607030018
Create Date: 2026-07-05
"""
from alembic import op
import sqlalchemy as sa

revision: str = "202607050019"
down_revision: str | None = "202607030018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("workspaces", sa.Column("timezone", sa.String(length=80), server_default="Europe/Kyiv", nullable=False))
    op.add_column("workspace_users", sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False))
    op.add_column("workspace_users", sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
    op.add_column("workspace_users", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_workspace_users_workspace_id", "workspace_users", ["workspace_id"])
    op.create_index("ix_workspace_users_user_id", "workspace_users", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_workspace_users_user_id", table_name="workspace_users")
    op.drop_index("ix_workspace_users_workspace_id", table_name="workspace_users")
    op.drop_column("workspace_users", "deleted_at")
    op.drop_column("workspace_users", "updated_at")
    op.drop_column("workspace_users", "is_active")
    op.drop_column("workspaces", "timezone")
