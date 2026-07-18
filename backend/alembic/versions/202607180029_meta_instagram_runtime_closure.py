"""harden meta instagram runtime closure

Revision ID: 202607180029
Revises: 202607180028
Create Date: 2026-07-18 12:00:00.000000
"""
from collections.abc import Sequence
from alembic import op
import sqlalchemy as sa

revision: str = "202607180029"
down_revision: str | None = "202607180028"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLES = ["instagram_connections", "meta_oauth_states", "meta_webhook_events", "meta_message_operations"]

def upgrade() -> None:
    op.create_index("uq_direct_conversations_instagram_participant", "direct_conversations", ["workspace_id", "instagram_connection_id", "participant_scoped_id"], unique=True, postgresql_where=sa.text("instagram_connection_id IS NOT NULL AND participant_scoped_id IS NOT NULL AND deleted_at IS NULL"))
    op.create_index("ix_meta_webhook_events_claim", "meta_webhook_events", ["status", "next_retry_at", "received_at"])
    op.create_index("ix_meta_webhook_events_connection_status", "meta_webhook_events", ["instagram_connection_id", "status"])
    op.create_index("ix_meta_message_operations_active", "meta_message_operations", ["workspace_id", "conversation_id", "status"])
    op.create_index("ix_meta_message_operations_provider_message", "meta_message_operations", ["workspace_id", "provider_message_id"])
    op.create_index("ix_instagram_connections_account_lookup", "instagram_connections", ["instagram_account_id", "status"])
    op.create_index("ix_instagram_connections_token_expiry", "instagram_connections", ["workspace_id", "token_expires_at"])
    op.create_check_constraint("ck_meta_message_operations_status", "meta_message_operations", "status in ('PREPARED','SENDING','PROVIDER_SUCCEEDED','COMPLETED','RETRY_PENDING','RECONCILIATION_REQUIRED','FAILED_SAFE','CANCELLED')")
    op.create_check_constraint("ck_meta_webhook_events_status", "meta_webhook_events", "status in ('RECEIVED','VERIFIED','QUEUED','PROCESSING','PROCESSED','IGNORED','RETRY_PENDING','DEAD_LETTER','FAILED_SAFE')")
    for table in TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"DROP POLICY IF EXISTS {table}_workspace_isolation ON {table}")
    op.execute("CREATE POLICY instagram_connections_workspace_isolation ON instagram_connections USING (workspace_id::text = current_setting('app.current_workspace_id', true)) WITH CHECK (workspace_id::text = current_setting('app.current_workspace_id', true))")
    op.execute("CREATE POLICY meta_oauth_states_workspace_isolation ON meta_oauth_states USING (workspace_id::text = current_setting('app.current_workspace_id', true)) WITH CHECK (workspace_id::text = current_setting('app.current_workspace_id', true))")
    op.execute("CREATE POLICY meta_message_operations_workspace_isolation ON meta_message_operations USING (workspace_id::text = current_setting('app.current_workspace_id', true)) WITH CHECK (workspace_id::text = current_setting('app.current_workspace_id', true))")
    op.execute("CREATE POLICY meta_webhook_events_workspace_isolation ON meta_webhook_events USING (workspace_id IS NULL OR workspace_id::text = current_setting('app.current_workspace_id', true)) WITH CHECK (workspace_id IS NULL OR workspace_id::text = current_setting('app.current_workspace_id', true))")

def downgrade() -> None:
    for table in TABLES:
        op.execute(f"DROP POLICY IF EXISTS {table}_workspace_isolation ON {table}")
    op.drop_constraint("ck_meta_webhook_events_status", "meta_webhook_events", type_="check")
    op.drop_constraint("ck_meta_message_operations_status", "meta_message_operations", type_="check")
    op.drop_index("ix_instagram_connections_token_expiry", table_name="instagram_connections")
    op.drop_index("ix_instagram_connections_account_lookup", table_name="instagram_connections")
    op.drop_index("ix_meta_message_operations_provider_message", table_name="meta_message_operations")
    op.drop_index("ix_meta_message_operations_active", table_name="meta_message_operations")
    op.drop_index("ix_meta_webhook_events_connection_status", table_name="meta_webhook_events")
    op.drop_index("ix_meta_webhook_events_claim", table_name="meta_webhook_events")
    op.drop_index("uq_direct_conversations_instagram_participant", table_name="direct_conversations")
