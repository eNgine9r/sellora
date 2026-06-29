"""database mixins foundation

Revision ID: 202606020002
Revises: 202606020001
Create Date: 2026-06-02 00:02:00.000000
"""
from collections.abc import Sequence

revision: str = "202606020002"
down_revision: str | None = "202606020001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """No schema changes are required for reusable future-entity mixins."""


def downgrade() -> None:
    """No schema changes are required for reusable future-entity mixins."""
