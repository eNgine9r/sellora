"""add meta instagram messaging integration

Revision ID: 202607180028
Revises: 202607180027
Create Date: 2026-07-18 10:00:00.000000
"""
from collections.abc import Sequence
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "202607180028"
down_revision: str | None = "202607180027"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

def uuid(name: str, nullable: bool = False):
    return sa.Column(name, postgresql.UUID(as_uuid=True), nullable=nullable)

def now_col(name: str):
    return sa.Column(name, sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False)

def upgrade() -> None:
    op.create_table(
        "instagram_connections",
        uuid("id"), uuid("workspace_id"),
        sa.Column("provider", sa.String(40), server_default="INSTAGRAM", nullable=False),
        sa.Column("login_type", sa.String(40), server_default="INSTAGRAM_LOGIN", nullable=False),
        sa.Column("status", sa.String(40), server_default="PENDING", nullable=False),
        sa.Column("instagram_account_id", sa.String(120)), sa.Column("instagram_username", sa.String(160)),
        sa.Column("instagram_account_type", sa.String(40)), sa.Column("meta_app_id", sa.String(120)),
        sa.Column("granted_permissions", postgresql.JSONB(), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("subscribed_webhook_fields", postgresql.JSONB(), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("access_token_ciphertext", sa.Text()), sa.Column("access_token_nonce", sa.String(120)), sa.Column("access_token_key_version", sa.String(80)),
        sa.Column("token_expires_at", sa.DateTime(timezone=True)), sa.Column("token_last_validated_at", sa.DateTime(timezone=True)),
        sa.Column("connected_at", sa.DateTime(timezone=True)), sa.Column("disconnected_at", sa.DateTime(timezone=True)),
        sa.Column("last_webhook_at", sa.DateTime(timezone=True)), sa.Column("last_message_received_at", sa.DateTime(timezone=True)), sa.Column("last_message_sent_at", sa.DateTime(timezone=True)),
        sa.Column("last_error_code", sa.String(120)), sa.Column("last_error_message", sa.Text()),
        now_col("created_at"), now_col("updated_at"), uuid("created_by", True), uuid("updated_by", True), sa.Column("deleted_at", sa.DateTime(timezone=True)), uuid("deleted_by", True),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"), sa.ForeignKeyConstraint(["updated_by"], ["users.id"], ondelete="SET NULL"), sa.ForeignKeyConstraint(["deleted_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"), sa.UniqueConstraint("workspace_id", "instagram_account_id", name="uq_instagram_connections_workspace_account"),
        sa.CheckConstraint("status in ('PENDING','CONNECTED','TOKEN_EXPIRED','PERMISSION_MISSING','WEBHOOK_INACTIVE','RECONNECT_REQUIRED','DISCONNECTED','FAILED')", name="ck_instagram_connections_status"),
    )
    op.create_table("meta_oauth_states", uuid("id"), uuid("workspace_id"), uuid("user_id"), sa.Column("state_hash", sa.String(64), nullable=False), sa.Column("code_verifier_ciphertext", sa.Text()), sa.Column("redirect_uri", sa.String(500), nullable=False), sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False), sa.Column("consumed_at", sa.DateTime(timezone=True)), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False), sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"), sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"), sa.PrimaryKeyConstraint("id"), sa.UniqueConstraint("state_hash", name="uq_meta_oauth_states_state_hash"))
    op.create_table("meta_webhook_events", uuid("id"), sa.Column("provider", sa.String(40), server_default="INSTAGRAM", nullable=False), uuid("workspace_id", True), uuid("instagram_connection_id", True), sa.Column("event_external_id", sa.String(180)), sa.Column("object_type", sa.String(80), nullable=False), sa.Column("event_type", sa.String(80), nullable=False), sa.Column("event_date_bucket", sa.Date()), sa.Column("payload_hash", sa.String(64), nullable=False), sa.Column("payload", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False), sa.Column("signature_verified", sa.Boolean(), server_default=sa.false(), nullable=False), sa.Column("status", sa.String(40), server_default="RECEIVED", nullable=False), sa.Column("attempt_count", sa.Integer(), server_default="0", nullable=False), sa.Column("received_at", sa.DateTime(timezone=True), nullable=False), sa.Column("processing_started_at", sa.DateTime(timezone=True)), sa.Column("processed_at", sa.DateTime(timezone=True)), sa.Column("next_retry_at", sa.DateTime(timezone=True)), sa.Column("safe_error_code", sa.String(120)), sa.Column("safe_error_message", sa.Text()), now_col("created_at"), now_col("updated_at"), sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"), sa.ForeignKeyConstraint(["instagram_connection_id"], ["instagram_connections.id"], ondelete="SET NULL"), sa.PrimaryKeyConstraint("id"), sa.UniqueConstraint("provider", "event_external_id", name="uq_meta_webhook_events_provider_external_id"), sa.CheckConstraint("attempt_count >= 0", name="ck_meta_webhook_events_attempt_count_nonnegative"))
    op.create_table("meta_message_operations", uuid("id"), uuid("workspace_id"), uuid("instagram_connection_id"), uuid("conversation_id"), uuid("direct_message_id", True), sa.Column("recipient_scoped_id", sa.String(180), nullable=False), sa.Column("operation_type", sa.String(60), server_default="SEND_MESSAGE", nullable=False), sa.Column("status", sa.String(40), server_default="PREPARED", nullable=False), sa.Column("idempotency_key", sa.String(160), nullable=False), sa.Column("request_fingerprint", sa.String(64), nullable=False), sa.Column("provider_request_id", sa.String(180)), sa.Column("provider_message_id", sa.String(180)), sa.Column("attempt_count", sa.Integer(), server_default="0", nullable=False), sa.Column("messaging_window_expires_at", sa.DateTime(timezone=True)), sa.Column("human_agent_allowed", sa.Boolean(), server_default=sa.false(), nullable=False), sa.Column("manual_reconciliation_required", sa.Boolean(), server_default=sa.false(), nullable=False), sa.Column("blind_retry_blocked", sa.Boolean(), server_default=sa.false(), nullable=False), sa.Column("safe_request_metadata", postgresql.JSONB()), sa.Column("safe_result_metadata", postgresql.JSONB()), sa.Column("last_error_code", sa.String(120)), sa.Column("last_error_message", sa.Text()), sa.Column("started_at", sa.DateTime(timezone=True)), sa.Column("provider_succeeded_at", sa.DateTime(timezone=True)), sa.Column("completed_at", sa.DateTime(timezone=True)), sa.Column("cancelled_at", sa.DateTime(timezone=True)), now_col("created_at"), now_col("updated_at"), uuid("created_by", True), sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"), sa.ForeignKeyConstraint(["instagram_connection_id"], ["instagram_connections.id"], ondelete="CASCADE"), sa.ForeignKeyConstraint(["conversation_id"], ["direct_conversations.id"], ondelete="CASCADE"), sa.ForeignKeyConstraint(["direct_message_id"], ["direct_messages.id"], ondelete="SET NULL"), sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"), sa.PrimaryKeyConstraint("id"), sa.UniqueConstraint("workspace_id", "idempotency_key", name="uq_meta_message_operations_workspace_idempotency_key"), sa.CheckConstraint("attempt_count >= 0", name="ck_meta_message_operations_attempt_count_nonnegative"))
    for column in [
        sa.Column("instagram_connection_id", postgresql.UUID(as_uuid=True)), sa.Column("external_thread_id", sa.String(180)), sa.Column("participant_scoped_id", sa.String(180)), sa.Column("messaging_window_expires_at", sa.DateTime(timezone=True)), sa.Column("human_agent_window_expires_at", sa.DateTime(timezone=True)), sa.Column("provider_sync_status", sa.String(40)),
    ]: op.add_column("direct_conversations", column)
    for column in [
        sa.Column("provider", sa.String(40)), sa.Column("provider_message_id", sa.String(180)), sa.Column("provider_event_id", sa.String(180)), sa.Column("delivery_status", sa.String(40)), sa.Column("message_payload_type", sa.String(40)), sa.Column("attachment_metadata", postgresql.JSONB()), sa.Column("provider_created_at", sa.DateTime(timezone=True)), sa.Column("sent_by_user_id", postgresql.UUID(as_uuid=True)),
    ]: op.add_column("direct_messages", column)
    op.create_foreign_key("fk_direct_conversations_instagram_connection", "direct_conversations", "instagram_connections", ["instagram_connection_id"], ["id"], ondelete="SET NULL")
    op.create_foreign_key("fk_direct_messages_sent_by_user", "direct_messages", "users", ["sent_by_user_id"], ["id"], ondelete="SET NULL")
    op.create_unique_constraint("uq_direct_messages_workspace_provider_message", "direct_messages", ["workspace_id", "provider", "provider_message_id"])
    op.create_index("ix_instagram_connections_workspace_status", "instagram_connections", ["workspace_id", "status"])
    op.create_index("ix_meta_webhook_events_status_retry", "meta_webhook_events", ["status", "next_retry_at"])
    op.create_index("ix_meta_webhook_events_payload_bucket", "meta_webhook_events", ["provider", "payload_hash", "event_date_bucket"])
    op.create_index("ix_meta_message_operations_workspace_status", "meta_message_operations", ["workspace_id", "status"])
    op.create_index("ix_direct_conversations_instagram_participant", "direct_conversations", ["workspace_id", "instagram_connection_id", "participant_scoped_id"])
    for table in ["instagram_connections", "meta_oauth_states", "meta_webhook_events", "meta_message_operations"]:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")

def downgrade() -> None:
    op.drop_index("ix_direct_conversations_instagram_participant", table_name="direct_conversations")
    op.drop_constraint("uq_direct_messages_workspace_provider_message", "direct_messages", type_="unique")
    op.drop_constraint("fk_direct_messages_sent_by_user", "direct_messages", type_="foreignkey")
    op.drop_constraint("fk_direct_conversations_instagram_connection", "direct_conversations", type_="foreignkey")
    for column in ["sent_by_user_id", "provider_created_at", "attachment_metadata", "message_payload_type", "delivery_status", "provider_event_id", "provider_message_id", "provider"]: op.drop_column("direct_messages", column)
    for column in ["provider_sync_status", "human_agent_window_expires_at", "messaging_window_expires_at", "participant_scoped_id", "external_thread_id", "instagram_connection_id"]: op.drop_column("direct_conversations", column)
    op.drop_table("meta_message_operations")
    op.drop_table("meta_webhook_events")
    op.drop_table("meta_oauth_states")
    op.drop_table("instagram_connections")
