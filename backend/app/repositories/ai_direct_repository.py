from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.models.ai_direct import (
    AIActionDraft,
    AIAnalysis,
    AISuggestion,
    AIUsageEvent,
    AIWorkspaceSettings,
    DirectConversation,
    DirectMessage,
)


class DirectConversationRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list(self, workspace_id: UUID) -> list[DirectConversation]:
        return list(
            self.db.execute(
                select(DirectConversation)
                .where(
                    DirectConversation.workspace_id == workspace_id,
                    DirectConversation.deleted_at.is_(None),
                )
                .order_by(DirectConversation.last_message_at.desc().nullslast())
            ).scalars()
        )

    def get(self, workspace_id: UUID, conversation_id: UUID) -> DirectConversation | None:
        return self.db.execute(
            select(DirectConversation).where(
                DirectConversation.workspace_id == workspace_id,
                DirectConversation.id == conversation_id,
                DirectConversation.deleted_at.is_(None),
            )
        ).scalar_one_or_none()

    def get_by_instagram_participant(
        self,
        workspace_id: UUID,
        instagram_connection_id: UUID,
        participant_scoped_id: str,
    ) -> DirectConversation | None:
        return self.db.execute(
            select(DirectConversation).where(
                DirectConversation.workspace_id == workspace_id,
                DirectConversation.instagram_connection_id == instagram_connection_id,
                DirectConversation.participant_scoped_id == participant_scoped_id,
                DirectConversation.deleted_at.is_(None),
            )
        ).scalar_one_or_none()

    def get_by_external_thread(
        self,
        workspace_id: UUID,
        instagram_connection_id: UUID,
        external_thread_id: str,
    ) -> DirectConversation | None:
        return self.db.execute(
            select(DirectConversation).where(
                DirectConversation.workspace_id == workspace_id,
                DirectConversation.instagram_connection_id == instagram_connection_id,
                DirectConversation.external_thread_id == external_thread_id,
                DirectConversation.deleted_at.is_(None),
            )
        ).scalar_one_or_none()

    def unread_total(self, workspace_id: UUID) -> int:
        value = self.db.execute(
            select(func.coalesce(func.sum(DirectConversation.unread_count), 0)).where(
                DirectConversation.workspace_id == workspace_id,
                DirectConversation.deleted_at.is_(None),
            )
        ).scalar_one()
        return int(value or 0)

    def mark_read(self, workspace_id: UUID, conversation_id: UUID) -> DirectConversation | None:
        statement = (
            update(DirectConversation)
            .where(
                DirectConversation.workspace_id == workspace_id,
                DirectConversation.id == conversation_id,
                DirectConversation.deleted_at.is_(None),
            )
            .values(unread_count=0, updated_at=datetime.now(UTC))
            .returning(DirectConversation)
        )
        return self.db.execute(statement).scalar_one_or_none()

    def create(self, conversation: DirectConversation) -> DirectConversation:
        self.db.add(conversation)
        self.db.flush()
        return conversation


class DirectMessageRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_for_conversation(self, workspace_id: UUID, conversation_id: UUID) -> list[DirectMessage]:
        return list(
            self.db.execute(
                select(DirectMessage)
                .where(
                    DirectMessage.workspace_id == workspace_id,
                    DirectMessage.conversation_id == conversation_id,
                    DirectMessage.deleted_at.is_(None),
                )
                .order_by(DirectMessage.received_at.asc(), DirectMessage.created_at.asc())
            ).scalars()
        )

    def recent_unread_inbound(
        self,
        workspace_id: UUID,
        *,
        limit: int = 20,
    ) -> list[tuple[DirectMessage, DirectConversation]]:
        ranked = (
            select(
                DirectMessage.id.label("message_id"),
                DirectMessage.conversation_id.label("conversation_id"),
                func.row_number()
                .over(
                    partition_by=DirectMessage.conversation_id,
                    order_by=(
                        DirectMessage.received_at.desc(),
                        DirectMessage.created_at.desc(),
                        DirectMessage.id.desc(),
                    ),
                )
                .label("inbound_rank"),
            )
            .where(
                DirectMessage.workspace_id == workspace_id,
                DirectMessage.direction == "INBOUND",
                DirectMessage.deleted_at.is_(None),
            )
            .subquery()
        )
        statement = (
            select(DirectMessage, DirectConversation)
            .join(ranked, ranked.c.message_id == DirectMessage.id)
            .join(DirectConversation, DirectConversation.id == DirectMessage.conversation_id)
            .where(
                DirectConversation.workspace_id == workspace_id,
                DirectConversation.deleted_at.is_(None),
                DirectConversation.unread_count > 0,
                ranked.c.inbound_rank <= DirectConversation.unread_count,
            )
            .order_by(DirectMessage.received_at.desc(), DirectMessage.created_at.desc())
            .limit(max(1, min(limit, 50)))
        )
        return [(message, conversation) for message, conversation in self.db.execute(statement).all()]

    def latest_analyzable(self, workspace_id: UUID, conversation_id: UUID) -> DirectMessage | None:
        return self.db.execute(
            select(DirectMessage)
            .where(
                DirectMessage.workspace_id == workspace_id,
                DirectMessage.conversation_id == conversation_id,
                DirectMessage.deleted_at.is_(None),
                DirectMessage.message_type == "TEXT",
            )
            .order_by(
                DirectMessage.received_at.desc(),
                DirectMessage.created_at.desc(),
                DirectMessage.id.desc(),
            )
            .limit(1)
        ).scalar_one_or_none()

    def get_by_provider_message(
        self,
        workspace_id: UUID,
        provider: str,
        provider_message_id: str,
    ) -> DirectMessage | None:
        return self.db.execute(
            select(DirectMessage).where(
                DirectMessage.workspace_id == workspace_id,
                DirectMessage.provider == provider,
                DirectMessage.provider_message_id == provider_message_id,
                DirectMessage.deleted_at.is_(None),
            )
        ).scalar_one_or_none()

    def create(self, message: DirectMessage) -> DirectMessage:
        self.db.add(message)
        self.db.flush()
        return message


class AIRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def settings_for_update(self, workspace_id: UUID) -> AIWorkspaceSettings | None:
        return self.db.execute(
            select(AIWorkspaceSettings)
            .where(AIWorkspaceSettings.workspace_id == workspace_id)
            .with_for_update()
        ).scalar_one_or_none()

    def get_or_create_settings(self, workspace_id: UUID) -> AIWorkspaceSettings:
        settings = self.db.execute(
            select(AIWorkspaceSettings).where(AIWorkspaceSettings.workspace_id == workspace_id)
        ).scalar_one_or_none()
        if settings:
            return settings
        settings = AIWorkspaceSettings(workspace_id=workspace_id)
        self.db.add(settings)
        self.db.flush()
        return settings

    def create_analysis(self, analysis: AIAnalysis) -> AIAnalysis:
        self.db.add(analysis)
        self.db.flush()
        return analysis

    def list_analyses(self, workspace_id: UUID, conversation_id: UUID) -> list[AIAnalysis]:
        return list(
            self.db.execute(
                select(AIAnalysis)
                .where(
                    AIAnalysis.workspace_id == workspace_id,
                    AIAnalysis.conversation_id == conversation_id,
                )
                .order_by(AIAnalysis.created_at.desc())
            ).scalars()
        )

    def get_analysis(self, workspace_id: UUID, analysis_id: UUID) -> AIAnalysis | None:
        return self.db.execute(
            select(AIAnalysis).where(
                AIAnalysis.workspace_id == workspace_id,
                AIAnalysis.id == analysis_id,
            )
        ).scalar_one_or_none()

    def create_suggestion(self, suggestion: AISuggestion) -> AISuggestion:
        self.db.add(suggestion)
        self.db.flush()
        return suggestion

    def list_suggestions(self, workspace_id: UUID, conversation_id: UUID) -> list[AISuggestion]:
        return list(
            self.db.execute(
                select(AISuggestion)
                .where(
                    AISuggestion.workspace_id == workspace_id,
                    AISuggestion.conversation_id == conversation_id,
                )
                .order_by(AISuggestion.created_at.desc())
            ).scalars()
        )

    def get_suggestion(self, workspace_id: UUID, suggestion_id: UUID) -> AISuggestion | None:
        return self.db.execute(
            select(AISuggestion).where(
                AISuggestion.workspace_id == workspace_id,
                AISuggestion.id == suggestion_id,
            )
        ).scalar_one_or_none()

    def create_action_draft(self, draft: AIActionDraft) -> AIActionDraft:
        self.db.add(draft)
        self.db.flush()
        return draft

    def get_action_draft(self, workspace_id: UUID, draft_id: UUID) -> AIActionDraft | None:
        return self.db.execute(
            select(AIActionDraft).where(
                AIActionDraft.workspace_id == workspace_id,
                AIActionDraft.id == draft_id,
            )
        ).scalar_one_or_none()

    def record_usage(self, event: AIUsageEvent) -> AIUsageEvent:
        self.db.add(event)
        self.db.flush()
        return event

    def usage_events(self, workspace_id: UUID) -> list[AIUsageEvent]:
        return list(
            self.db.execute(
                select(AIUsageEvent)
                .where(AIUsageEvent.workspace_id == workspace_id)
                .order_by(AIUsageEvent.created_at.desc())
                .limit(100)
            ).scalars()
        )
