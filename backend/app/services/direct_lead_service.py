from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.ai.services.direct_order_intent_service import detect_direct_order_intent
from app.models.ai_direct import DirectChannel
from app.models.lead import Lead, LeadStatus
from app.repositories.ai_direct_repository import DirectConversationRepository, DirectMessageRepository
from app.repositories.audit_log_repository import AuditLogRepository
from app.repositories.lead_repository import LeadRepository


class DirectLeadError(ValueError):
    """Safe, stable API codes for the Direct-to-Lead workflow."""


class DirectLeadService:
    """Idempotent, workspace-scoped lead association for genuine IG Direct inquiries.

    Lead is a sales opportunity, not a second Customer profile. Existing
    customer-prospect behavior remains separate; a lead never creates an order.
    """

    def __init__(self, db: Session) -> None:
        self.db = db
        self.conversations = DirectConversationRepository(db)
        self.messages = DirectMessageRepository(db)
        self.leads = LeadRepository(db)
        self.audit = AuditLogRepository(db)

    def ensure_from_inbound_order_intent(
        self, workspace_id: UUID, conversation_id: UUID, message_text: str | None,
        received_at: datetime | None = None,
    ) -> Lead | None:
        if not detect_direct_order_intent(message_text).detected:
            return None
        return self._ensure(workspace_id, conversation_id, actor_user_id=None, received_at=received_at)

    def ensure_manually(self, workspace_id: UUID, conversation_id: UUID, actor_user_id: UUID) -> Lead:
        conversation = self._conversation(workspace_id, conversation_id)
        inbound = self.messages.latest_instagram_inbound(workspace_id, conversation_id)
        if not inbound:
            raise DirectLeadError("DIRECT_LEAD_INBOUND_REQUIRED")
        return self._ensure(
            workspace_id, conversation.id, actor_user_id=actor_user_id,
            received_at=inbound.received_at,
        )

    def _conversation(self, workspace_id: UUID, conversation_id: UUID):
        conversation = self.conversations.get(workspace_id, conversation_id)
        if not conversation:
            raise DirectLeadError("DIRECT_CONVERSATION_NOT_FOUND")
        if (
            conversation.channel != DirectChannel.INSTAGRAM.value
            or not conversation.instagram_connection_id
            or not conversation.participant_scoped_id
        ):
            raise DirectLeadError("DIRECT_LEAD_INSTAGRAM_REQUIRED")
        return conversation

    def _ensure(
        self, workspace_id: UUID, conversation_id: UUID,
        actor_user_id: UUID | None, received_at: datetime | None,
    ) -> Lead:
        conversation = self._conversation(workspace_id, conversation_id)
        # Serialize competing messages and history-sync replays for one
        # Instagram participant, across all of their Direct conversations.
        self.conversations.lock_instagram_participant(
            workspace_id, conversation.instagram_connection_id, conversation.participant_scoped_id,
        )
        conversation = self.conversations.get_for_update(workspace_id, conversation_id)
        if not conversation:
            raise DirectLeadError("DIRECT_CONVERSATION_NOT_FOUND")
        if conversation.linked_lead_id:
            linked = self.leads.get(workspace_id, conversation.linked_lead_id)
            if linked and linked.status in {LeadStatus.NEW.value, LeadStatus.IN_PROGRESS.value, LeadStatus.QUALIFIED.value}:
                return linked

        previous = self.conversations.find_lead_for_instagram_participant(
            workspace_id, conversation.instagram_connection_id,
            conversation.participant_scoped_id,
        )
        if previous:
            linked = self.leads.get(workspace_id, previous.linked_lead_id)
            if linked and linked.status in {LeadStatus.NEW.value, LeadStatus.IN_PROGRESS.value, LeadStatus.QUALIFIED.value}:
                conversation.linked_lead_id = linked.id
                return linked

        username = (conversation.participant_username or "").strip().lstrip("@")[:120] or None
        display = (conversation.participant_display_name or "").strip()
        if display == "Instagram customer" or not display:
            display = username or "Instagram customer"
        lead = self.leads.create(Lead(
            workspace_id=workspace_id,
            instagram_username=username,
            name=display[:255],
            status=LeadStatus.NEW.value,
            first_contact_at=received_at or conversation.last_inbound_message_at or datetime.now(UTC),
            last_contact_at=received_at or conversation.last_inbound_message_at or datetime.now(UTC),
        ))
        conversation.linked_lead_id = lead.id
        self.audit.create(
            workspace_id=workspace_id,
            user_id=actor_user_id,
            entity_type="Lead",
            entity_id=lead.id,
            action="DIRECT_LEAD_CREATE",
            new_value={"source": "INSTAGRAM_DIRECT", "conversation_id": str(conversation.id), "status": "NEW"},
        )
        return lead
