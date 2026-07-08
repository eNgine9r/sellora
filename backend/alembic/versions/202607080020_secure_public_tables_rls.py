"""secure public tables with row-level security

Revision ID: 202607080020
Revises: 202607050019
Create Date: 2026-07-08 00:20:00.000000
"""

from collections.abc import Sequence

from alembic import op

revision: str = "202607080020"
down_revision: str | None = "202607050019"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_TABLES = (
    "pilot_feedback",
    "finance_adjustments",
    "meta_ad_connections",
)


def upgrade() -> None:
    for table_name in _TABLES:
        op.execute(f'ALTER TABLE IF EXISTS public."{table_name}" ENABLE ROW LEVEL SECURITY')
        op.execute(
            f'REVOKE ALL PRIVILEGES ON TABLE public."{table_name}" FROM anon, authenticated'
        )


def downgrade() -> None:
    # Security hardening is intentionally irreversible through Alembic.
    # Restoring public access must be an explicit, separately reviewed change.
    pass
