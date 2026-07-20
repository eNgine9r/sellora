from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.instagram_participant_profile import InstagramParticipantProfile


class InstagramParticipantProfileRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_conversation(
        self,
        workspace_id: UUID,
        conversation_id: UUID,
    ) -> InstagramParticipantProfile | None:
        return self.db.execute(
            select(InstagramParticipantProfile).where(
                InstagramParticipantProfile.workspace_id == workspace_id,
                InstagramParticipantProfile.conversation_id == conversation_id,
            )
        ).scalar_one_or_none()

    def get_by_conversation_for_update(
        self,
        workspace_id: UUID,
        conversation_id: UUID,
    ) -> InstagramParticipantProfile | None:
        return self.db.execute(
            select(InstagramParticipantProfile)
            .where(
                InstagramParticipantProfile.workspace_id == workspace_id,
                InstagramParticipantProfile.conversation_id == conversation_id,
            )
            .with_for_update()
        ).scalar_one_or_none()

    def list_for_conversations(
        self,
        workspace_id: UUID,
        conversation_ids: list[UUID],
    ) -> dict[UUID, InstagramParticipantProfile]:
        if not conversation_ids:
            return {}
        rows = self.db.execute(
            select(InstagramParticipantProfile).where(
                InstagramParticipantProfile.workspace_id == workspace_id,
                InstagramParticipantProfile.conversation_id.in_(conversation_ids),
            )
        ).scalars()
        return {row.conversation_id: row for row in rows}

    def create(self, profile: InstagramParticipantProfile) -> InstagramParticipantProfile:
        self.db.add(profile)
        self.db.flush()
        return profile
