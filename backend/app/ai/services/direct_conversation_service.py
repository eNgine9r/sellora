from datetime import UTC, datetime
from uuid import UUID
import hashlib
from app.models.ai_direct import DirectConversation, DirectMessage, DirectChannel, DirectMessageDirection, DirectMessageSenderType, DirectMessageType
from app.repositories.ai_direct_repository import DirectConversationRepository, DirectMessageRepository

class DirectConversationService:
    def __init__(self, conversations: DirectConversationRepository, messages: DirectMessageRepository) -> None:
        self.conversations=conversations; self.messages=messages
    def create_synthetic(self, workspace_id: UUID, user_id: UUID | None, participant_display_name: str, participant_username: str | None, initial_message: str) -> DirectConversation:
        now=datetime.now(UTC)
        c=self.conversations.create(DirectConversation(workspace_id=workspace_id, channel=DirectChannel.SYNTHETIC.value, participant_display_name=participant_display_name, participant_username=participant_username, created_by=user_id, updated_by=user_id, last_message_at=now, last_inbound_message_at=now, unread_count=1))
        self.add_message(workspace_id, c.id, initial_message, True)
        return c
    def add_message(self, workspace_id: UUID, conversation_id: UUID, text: str, inbound: bool=True) -> DirectMessage:
        conversation = self.conversations.get(workspace_id, conversation_id)
        if not conversation: raise ValueError('DIRECT_CONVERSATION_NOT_FOUND')
        now=datetime.now(UTC); digest=hashlib.sha256(text.encode()).hexdigest()
        msg=self.messages.create(DirectMessage(workspace_id=workspace_id, conversation_id=conversation_id, direction=DirectMessageDirection.INBOUND.value if inbound else DirectMessageDirection.INTERNAL.value, sender_type=DirectMessageSenderType.CUSTOMER.value if inbound else DirectMessageSenderType.MANAGER.value, message_type=DirectMessageType.TEXT.value, text=text, safe_text_hash=digest, received_at=now, is_synthetic=conversation.channel==DirectChannel.SYNTHETIC.value))
        conversation.last_message_at=now
        if inbound: conversation.last_inbound_message_at=now; conversation.unread_count += 1
        return msg
