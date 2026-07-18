from datetime import UTC, datetime, timedelta
from typing import Any
from sqlalchemy.orm import Session
from app.integrations.meta_instagram.repositories.connection_repository import InstagramConnectionRepository
from app.models.ai_direct import DirectChannel
from app.models.meta_instagram import MetaWebhookEvent, MetaWebhookEventStatus
from app.repositories.ai_direct_repository import DirectConversationRepository, DirectMessageRepository
from app.ai.services.direct_conversation_service import DirectConversationService

class InstagramInboundMessageService:
    def __init__(self, db: Session) -> None:
        self.db = db; self.conversations = DirectConversationRepository(db); self.messages = DirectMessageRepository(db)
    def process_event(self, event: MetaWebhookEvent) -> int:
        connection = InstagramConnectionRepository(self.db).get_active(event.workspace_id) if event.workspace_id else None
        if not connection:
            event.status = MetaWebhookEventStatus.IGNORED.value; return 0
        created = 0
        for entry in event.payload.get("entry", []) or []:
            for item in entry.get("messaging", []) or []:
                sender_id = str((item.get("sender") or {}).get("id") or "")
                if not sender_id: continue
                message = item.get("message") or {}
                provider_message_id = str(message.get("mid") or event.event_external_id or event.payload_hash)
                if any(m.provider_message_id == provider_message_id for m in self.messages.list_for_conversation(event.workspace_id, getattr(self._conversation(event.workspace_id, connection.id, sender_id), 'id'))):
                    continue
                text = message.get("text") or "[Медіа або unsupported Instagram message]"
                conversation = self._conversation(event.workspace_id, connection.id, sender_id)
                msg = DirectConversationService(self.conversations, self.messages).add_message(event.workspace_id, conversation.id, text, inbound=True)
                msg.provider = "INSTAGRAM"; msg.provider_message_id = provider_message_id; msg.provider_event_id = event.event_external_id; msg.message_payload_type = "TEXT" if message.get("text") else "UNSUPPORTED"; msg.provider_created_at = datetime.fromtimestamp(item.get("timestamp", 0) / 1000, UTC) if item.get("timestamp") else datetime.now(UTC)
                conversation.instagram_connection_id = connection.id; conversation.channel = DirectChannel.INSTAGRAM.value; conversation.participant_scoped_id = sender_id; conversation.messaging_window_expires_at = datetime.now(UTC) + timedelta(hours=24); conversation.human_agent_window_expires_at = datetime.now(UTC) + timedelta(days=7)
                created += 1
        event.status = MetaWebhookEventStatus.PROCESSED.value; event.processed_at = datetime.now(UTC)
        return created
    def _conversation(self, workspace_id, connection_id, sender_id):
        for conversation in self.conversations.list(workspace_id):
            if conversation.instagram_connection_id == connection_id and conversation.participant_scoped_id == sender_id:
                return conversation
        c = self.conversations.create(__import__('app.models.ai_direct', fromlist=['DirectConversation']).DirectConversation(workspace_id=workspace_id, channel=DirectChannel.INSTAGRAM.value, instagram_connection_id=connection_id, participant_scoped_id=sender_id, participant_display_name="Instagram customer", unread_count=0, last_message_at=datetime.now(UTC)))
        return c
