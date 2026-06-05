"""import center

Revision ID: 202606020007
Revises: 202606020006
Create Date: 2026-06-02 00:07:00.000000
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "202606020007"
down_revision: str | None = "202606020006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

JOB_STATUSES = "'UPLOADED','PREVIEWED','VALIDATED','IMPORTING','COMPLETED','FAILED','PARTIALLY_COMPLETED','CANCELLED'"
LOG_STATUSES = "'SUCCESS','FAILED','SKIPPED','WARNING'"


def upgrade() -> None:
    op.create_table(
        "import_jobs",
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("file_type", sa.String(length=20), nullable=False),
        sa.Column("file_path", sa.String(length=1000), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("total_rows", sa.Integer(), server_default="0", nullable=False),
        sa.Column("processed_rows", sa.Integer(), server_default="0", nullable=False),
        sa.Column("success_rows", sa.Integer(), server_default="0", nullable=False),
        sa.Column("failed_rows", sa.Integer(), server_default="0", nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(f"status IN ({JOB_STATUSES})", name="ck_import_jobs_status"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], name=op.f("fk_import_jobs_created_by_users"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["deleted_by"], ["users.id"], name=op.f("fk_import_jobs_deleted_by_users"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], name=op.f("fk_import_jobs_workspace_id_workspaces"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_import_jobs")),
    )
    op.create_index(op.f("ix_import_jobs_workspace_id"), "import_jobs", ["workspace_id"], unique=False)
    op.create_index("ix_import_jobs_workspace_status", "import_jobs", ["workspace_id", "status"], unique=False)
    op.create_table(
        "import_job_logs",
        sa.Column("import_job_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("row_number", sa.Integer(), nullable=True),
        sa.Column("entity_type", sa.String(length=80), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("raw_data", postgresql.JSONB(), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(f"status IN ({LOG_STATUSES})", name="ck_import_job_logs_status"),
        sa.ForeignKeyConstraint(["import_job_id"], ["import_jobs.id"], name=op.f("fk_import_job_logs_import_job_id_import_jobs"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], name=op.f("fk_import_job_logs_workspace_id_workspaces"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_import_job_logs")),
    )
    op.create_index(op.f("ix_import_job_logs_workspace_id"), "import_job_logs", ["workspace_id"], unique=False)
    op.create_index("ix_import_job_logs_job_status", "import_job_logs", ["import_job_id", "status"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_import_job_logs_job_status", table_name="import_job_logs")
    op.drop_index(op.f("ix_import_job_logs_workspace_id"), table_name="import_job_logs")
    op.drop_table("import_job_logs")
    op.drop_index("ix_import_jobs_workspace_status", table_name="import_jobs")
    op.drop_index(op.f("ix_import_jobs_workspace_id"), table_name="import_jobs")
    op.drop_table("import_jobs")
