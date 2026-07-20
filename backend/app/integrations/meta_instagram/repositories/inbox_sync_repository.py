from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.instagram_inbox_sync import (
    InstagramHistorySync,
    InstagramHistorySyncStatus,
    InstagramMessageState,
)


class InstagramHistorySyncRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get(self, workspace_id: UUID) -> InstagramHistorySync | None:
        return self.db.execute(
            select(InstagramHistorySync).where(
                InstagramHistorySync.workspace_id == workspace_id,
            )
        ).scalar_one_or_none()

    def get_for_update(self, workspace_id: UUID) -> InstagramHistorySync | None:
        return self.db.execute(
            select(InstagramHistorySync)
            .where(InstagramHistorySync.workspace_id == workspace_id)
            .with_for_update()
        ).scalar_one_or_none()

    def create(self, sync: InstagramHistorySync) -> InstagramHistorySync:
        self.db.add(sync)
        self.db.flush()
        return sync

    def next_pending_for_update(self) -> InstagramHistorySync | None:
        now = datetime.now(UTC)
        return self.db.execute(
            select(InstagramHistorySync)
            .where(
                InstagramHistorySync.status.in_(
                    [
                        InstagramHistorySyncStatus.PENDING.value,
                        InstagramHistorySyncStatus.RETRY_PENDING.value,
                    ]
                ),
                or_(
                    InstagramHistorySync.next_retry_at.is_(None),
                    InstagramHistorySync.next_retry_at <= now,
                ),
            )
            .order_by(InstagramHistorySync.updated_at.asc())
            .limit(1)
            .with_for_update(skip_locked=True)
        ).scalar_one_or_none()


class InstagramMessageStateRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_message(self, workspace_id: UUID, direct_message_id: UUID) -> InstagramMessageState | None:
        return self.db.execute(
            select(InstagramMessageState).where(
                InstagramMessageState.workspace_id == workspace_id,
                InstagramMessageState.direct_message_id == direct_message_id,
            )
        ).scalar_one_or_none()

    def get_by_provider_message(self, workspace_id: UUID, provider_message_id: str) -> InstagramMessageState | None:
        return self.db.execute(
            select(InstagramMessageState).where(
                InstagramMessageState.workspace_id == workspace_id,
                InstagramMessageState.provider_message_id == provider_message_id,
            )
        ).scalar_one_or_none()

    def get_or_create(
        self,
        workspace_id: UUID,
        direct_message_id: UUID,
        provider_message_id: str,
    ) -> InstagramMessageState:
        existing = self.get_by_message(workspace_id, direct_message_id)
        if existing:
            return existing
        state = InstagramMessageState(
            workspace_id=workspace_id,
            direct_message_id=direct_message_id,
            provider_message_id=provider_message_id,
        )
        self.db.add(state)
        self.db.flush()
        return state

    def list_for_messages(
        self,
        workspace_id: UUID,
        message_ids: list[UUID],
    ) -> dict[UUID, InstagramMessageState]:
        if not message_ids:
            return {}
        rows = self.db.execute(
            select(InstagramMessageState).where(
                InstagramMessageState.workspace_id == workspace_id,
                InstagramMessageState.direct_message_id.in_(message_ids),
            )
        ).scalars()
        return {row.direct_message_id: row for row in rows}
