"""Increase bounded Instagram inbox history scan limits.

Revision ID: 202610210040
Revises: 202610200039

Only the two check constraints are changed. No customer or message data is touched.
"""
from alembic import op

revision = "202610210040"
down_revision = "202610200039"
branch_labels = None
depends_on = None

TABLE = "instagram_history_syncs"
OLD_CONV = "ck_instagram_history_syncs_ck_instagram_history_syncs_c_7dce"
OLD_MSG = "ck_instagram_history_syncs_ck_instagram_history_syncs_m_965d"
NEW_CONV = "ck_ig_history_max_conversations"
NEW_MSG = "ck_ig_history_max_messages"


def upgrade():
    op.drop_constraint(op.f(OLD_CONV), TABLE, type_="check")
    op.drop_constraint(op.f(OLD_MSG), TABLE, type_="check")
    op.execute(
        f"ALTER TABLE {TABLE} ADD CONSTRAINT {NEW_CONV} "
        "CHECK (conversation_limit BETWEEN 1 AND 2000)"
    )
    op.execute(
        f"ALTER TABLE {TABLE} ADD CONSTRAINT {NEW_MSG} "
        "CHECK (messages_per_conversation BETWEEN 1 AND 200)"
    )


def downgrade():
    # Refuse a destructive/invalid downgrade once larger scans have been queued.
    op.execute(
        f"ALTER TABLE {TABLE} ADD CONSTRAINT ck_ig_history_old_conversation_guard "
        "CHECK (conversation_limit BETWEEN 1 AND 500)"
    )
    op.execute(
        f"ALTER TABLE {TABLE} ADD CONSTRAINT ck_ig_history_old_message_guard "
        "CHECK (messages_per_conversation BETWEEN 1 AND 20)"
    )
    op.drop_constraint(op.f(NEW_CONV), TABLE, type_="check")
    op.drop_constraint(op.f(NEW_MSG), TABLE, type_="check")
    op.execute(
        f"ALTER TABLE {TABLE} RENAME CONSTRAINT ck_ig_history_old_conversation_guard TO {OLD_CONV}"
    )
    op.execute(
        f"ALTER TABLE {TABLE} RENAME CONSTRAINT ck_ig_history_old_message_guard TO {OLD_MSG}"
    )
