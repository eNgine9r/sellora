"""add sprint 8f phone address and provider write foundation

Revision ID: 202607160023
Revises: 202607150022
Create Date: 2026-07-16 00:23:00.000000
"""

from collections.abc import Sequence
import re

from alembic import op
import sqlalchemy as sa

revision: str = "202607160023"
down_revision: str | None = "202607150022"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_PHONE_RE = re.compile(r"^\+?[0-9\s()\-]+$")
_FORMAT_RE = re.compile(r"[\s()\-]")


def _normalize_phone(value: str | None) -> str | None:
    if value is None:
        return None
    raw = value.strip()
    if not raw:
        return None
    if not _PHONE_RE.fullmatch(raw) or raw.count("+") > 1 or ("+" in raw and not raw.startswith("+")):
        return value
    digits = _FORMAT_RE.sub("", raw[1:] if raw.startswith("+") else raw)
    if len(digits) == 10 and digits.startswith("0"):
        digits = f"38{digits}"
    if len(digits) == 12 and digits.startswith("380"):
        return f"+{digits}"
    return value


def upgrade() -> None:
    op.add_column("customer_addresses", sa.Column("delivery_provider", sa.String(length=40), nullable=True))
    op.add_column("customer_addresses", sa.Column("nova_poshta_city_ref", sa.String(length=120), nullable=True))
    op.add_column("customer_addresses", sa.Column("nova_poshta_warehouse_ref", sa.String(length=120), nullable=True))
    op.add_column("customer_addresses", sa.Column("warehouse_number", sa.String(length=40), nullable=True))
    op.add_column("integration_connections", sa.Column("provider_writes_allowed", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("integration_connections", sa.Column("provider_connection_verified_at", sa.DateTime(timezone=True), nullable=True))

    bind = op.get_bind()
    for table in ("customers", "customer_addresses", "shipments"):
        phone_column = "recipient_phone" if table == "shipments" else "phone"
        rows = bind.execute(sa.text(f"SELECT id, {phone_column} FROM {table} WHERE {phone_column} IS NOT NULL")).mappings()
        for row in rows:
            normalized = _normalize_phone(row[phone_column])
            if normalized != row[phone_column]:
                bind.execute(sa.text(f"UPDATE {table} SET {phone_column} = :phone WHERE id = :id"), {"phone": normalized, "id": row["id"]})

    bind.execute(sa.text("""
        WITH ranked_defaults AS (
            SELECT
                id,
                row_number() OVER (
                    PARTITION BY workspace_id, customer_id
                    ORDER BY updated_at DESC NULLS LAST, created_at DESC NULLS LAST, id DESC
                ) AS default_rank
            FROM customer_addresses
            WHERE is_default = true
              AND deleted_at IS NULL
        )
        UPDATE customer_addresses AS address
        SET is_default = false
        FROM ranked_defaults
        WHERE address.id = ranked_defaults.id
          AND ranked_defaults.default_rank > 1
    """))

    op.create_index(
        "uq_customer_addresses_one_active_default",
        "customer_addresses",
        ["workspace_id", "customer_id"],
        unique=True,
        postgresql_where=sa.text("is_default = true AND deleted_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_column("integration_connections", "provider_connection_verified_at")
    op.drop_column("integration_connections", "provider_writes_allowed")
    op.drop_index("uq_customer_addresses_one_active_default", table_name="customer_addresses", postgresql_where=sa.text("is_default = true AND deleted_at IS NULL"))
    op.drop_column("customer_addresses", "warehouse_number")
    op.drop_column("customer_addresses", "nova_poshta_warehouse_ref")
    op.drop_column("customer_addresses", "nova_poshta_city_ref")
    op.drop_column("customer_addresses", "delivery_provider")
