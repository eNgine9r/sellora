"""enforce unique connected Instagram account routing

Revision ID: 202607190030
Revises: 202607180029
Create Date: 2026-07-19 13:00:00.000000
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "202607190030"
down_revision: str | None = "202607180029"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Preserve the most recently validated connection for each Instagram account.
    # Older active duplicates are made non-operational before the partial unique
    # index is created, so upgrades remain deployable on existing staging data.
    op.execute(
        """
        WITH ranked_connections AS (
            SELECT
                id,
                row_number() OVER (
                    PARTITION BY instagram_account_id
                    ORDER BY
                        token_last_validated_at DESC NULLS LAST,
                        connected_at DESC NULLS LAST,
                        updated_at DESC NULLS LAST,
                        created_at DESC NULLS LAST,
                        id DESC
                ) AS position
            FROM instagram_connections
            WHERE instagram_account_id IS NOT NULL
              AND deleted_at IS NULL
              AND status = 'CONNECTED'
        )
        UPDATE instagram_connections AS connection
        SET status = 'DISCONNECTED',
            subscribed_webhook_fields = '[]'::jsonb,
            access_token_ciphertext = NULL,
            access_token_nonce = NULL,
            access_token_key_version = NULL,
            disconnected_at = COALESCE(connection.disconnected_at, now()),
            last_error_code = 'META_DUPLICATE_CONNECTED_ACCOUNT_CLEANUP',
            last_error_message = 'Duplicate connected Instagram account was deactivated during webhook runtime migration.',
            updated_at = now()
        FROM ranked_connections AS ranked
        WHERE connection.id = ranked.id
          AND ranked.position > 1
        """
    )
    op.create_index(
        "uq_instagram_connections_connected_account",
        "instagram_connections",
        ["instagram_account_id"],
        unique=True,
        postgresql_where=sa.text(
            "instagram_account_id IS NOT NULL AND deleted_at IS NULL AND status = 'CONNECTED'"
        ),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_instagram_connections_connected_account",
        table_name="instagram_connections",
    )
