"""crm completion

Revision ID: 202606020006
Revises: 202606020005
Create Date: 2026-06-02 00:06:00.000000
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "202606020006"
down_revision: str | None = "202606020005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ATTACHMENT_TYPES = "'CUSTOMER', 'LEAD', 'ORDER', 'PRODUCT', 'SHIPMENT'"


def _tenant_columns() -> list[sa.Column]:
    return [
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "tags",
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("color", sa.String(length=30), server_default="#2563eb", nullable=False),
        *_tenant_columns(),
        sa.ForeignKeyConstraint(["deleted_by"], ["users.id"], name=op.f("fk_tags_deleted_by_users"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], name=op.f("fk_tags_workspace_id_workspaces"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_tags")),
    )
    op.create_index(op.f("ix_tags_workspace_id"), "tags", ["workspace_id"], unique=False)
    op.create_index("ix_tags_workspace_id_name", "tags", ["workspace_id", "name"], unique=False)

    op.create_table(
        "customer_tags",
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tag_id", postgresql.UUID(as_uuid=True), nullable=False),
        *_tenant_columns(),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], name=op.f("fk_customer_tags_customer_id_customers"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["deleted_by"], ["users.id"], name=op.f("fk_customer_tags_deleted_by_users"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["tag_id"], ["tags.id"], name=op.f("fk_customer_tags_tag_id_tags"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], name=op.f("fk_customer_tags_workspace_id_workspaces"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_customer_tags")),
        sa.UniqueConstraint("customer_id", "tag_id", name="uq_customer_tags_customer_id_tag_id"),
    )
    op.create_index(op.f("ix_customer_tags_workspace_id"), "customer_tags", ["workspace_id"], unique=False)

    op.create_table(
        "customer_notes",
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("note", sa.Text(), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        *_tenant_columns(),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], name=op.f("fk_customer_notes_created_by_users"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], name=op.f("fk_customer_notes_customer_id_customers"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["deleted_by"], ["users.id"], name=op.f("fk_customer_notes_deleted_by_users"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], name=op.f("fk_customer_notes_workspace_id_workspaces"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_customer_notes")),
    )
    op.create_index(op.f("ix_customer_notes_workspace_id"), "customer_notes", ["workspace_id"], unique=False)
    op.create_index("ix_customer_notes_customer_id_created_at", "customer_notes", ["customer_id", "created_at"], unique=False)

    op.create_table(
        "customer_addresses",
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("label", sa.String(length=100), nullable=True),
        sa.Column("recipient_name", sa.String(length=255), nullable=True),
        sa.Column("phone", sa.String(length=50), nullable=True),
        sa.Column("address_line1", sa.String(length=255), nullable=False),
        sa.Column("address_line2", sa.String(length=255), nullable=True),
        sa.Column("city", sa.String(length=120), nullable=True),
        sa.Column("region", sa.String(length=120), nullable=True),
        sa.Column("postal_code", sa.String(length=40), nullable=True),
        sa.Column("country", sa.String(length=120), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("is_default", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        *_tenant_columns(),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], name=op.f("fk_customer_addresses_customer_id_customers"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["deleted_by"], ["users.id"], name=op.f("fk_customer_addresses_deleted_by_users"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], name=op.f("fk_customer_addresses_workspace_id_workspaces"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_customer_addresses")),
    )
    op.create_index(op.f("ix_customer_addresses_workspace_id"), "customer_addresses", ["workspace_id"], unique=False)
    op.create_index("uq_customer_addresses_one_default", "customer_addresses", ["customer_id"], unique=True, postgresql_where=sa.text("is_default IS TRUE AND deleted_at IS NULL"))

    op.create_table(
        "attachments",
        sa.Column("entity_type", sa.String(length=30), nullable=False),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("file_url", sa.String(length=1000), nullable=False),
        sa.Column("file_name", sa.String(length=255), nullable=True),
        sa.Column("content_type", sa.String(length=120), nullable=True),
        sa.Column("uploaded_by", postgresql.UUID(as_uuid=True), nullable=True),
        *_tenant_columns(),
        sa.CheckConstraint(f"entity_type IN ({ATTACHMENT_TYPES})", name="ck_attachments_entity_type"),
        sa.ForeignKeyConstraint(["deleted_by"], ["users.id"], name=op.f("fk_attachments_deleted_by_users"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["uploaded_by"], ["users.id"], name=op.f("fk_attachments_uploaded_by_users"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], name=op.f("fk_attachments_workspace_id_workspaces"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_attachments")),
    )
    op.create_index(op.f("ix_attachments_workspace_id"), "attachments", ["workspace_id"], unique=False)
    op.create_index("ix_attachments_entity", "attachments", ["workspace_id", "entity_type", "entity_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_attachments_entity", table_name="attachments")
    op.drop_index(op.f("ix_attachments_workspace_id"), table_name="attachments")
    op.drop_table("attachments")
    op.drop_index("uq_customer_addresses_one_default", table_name="customer_addresses")
    op.drop_index(op.f("ix_customer_addresses_workspace_id"), table_name="customer_addresses")
    op.drop_table("customer_addresses")
    op.drop_index("ix_customer_notes_customer_id_created_at", table_name="customer_notes")
    op.drop_index(op.f("ix_customer_notes_workspace_id"), table_name="customer_notes")
    op.drop_table("customer_notes")
    op.drop_index(op.f("ix_customer_tags_workspace_id"), table_name="customer_tags")
    op.drop_table("customer_tags")
    op.drop_index("ix_tags_workspace_id_name", table_name="tags")
    op.drop_index(op.f("ix_tags_workspace_id"), table_name="tags")
    op.drop_table("tags")
