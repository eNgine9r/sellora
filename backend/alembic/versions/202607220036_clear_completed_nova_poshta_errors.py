"""clear stale errors from completed Nova Poshta operations

Revision ID: 202607220036
Revises: 202607220035
"""

from alembic import op


revision: str = "202607220036"
down_revision: str | None = "202607220035"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE nova_poshta_operations
        SET last_error_code = NULL,
            last_error_message = NULL
        WHERE state = 'COMPLETED'
          AND provider_document_ref IS NOT NULL
          AND provider_document_number IS NOT NULL
          AND (last_error_code IS NOT NULL OR last_error_message IS NOT NULL)
        """
    )


def downgrade() -> None:
    # Cleared legacy errors described a previous transient state and must not be
    # reconstructed after the provider result has been confirmed.
    pass
