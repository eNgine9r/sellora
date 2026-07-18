from datetime import UTC, datetime
from uuid import UUID
import hashlib
from sqlalchemy.orm import Session
from app.core.config import get_settings
from app.integrations.meta_instagram.client import MetaInstagramClient
from app.integrations.meta_instagram.crypto import decrypt_instagram_token
from app.integrations.meta_instagram.exceptions import MetaInstagramError
from app.integrations.meta_instagram.repositories.connection_repository import InstagramConnectionRepository
from app.integrations.meta_instagram.repositories.message_operation_repository import MetaMessageOperationRepository
from app.models.ai_direct import DirectMessageDirection, DirectMessageSenderType, DirectMessageType
from app.models.meta_instagram import MetaMessageOperation, MetaMessageOperationStatus
from app.repositories.ai_direct_repository import DirectConversationRepository, DirectMessageRepository

class InstagramOutboundMessageService:
    def __init__(self, db: Session) -> None: self.db = db; self.ops = MetaMessageOperationRepository(db)
    def prepare(self, workspace_id: UUID, conversation_id: UUID, message_text: str, human_agent_requested: bool = False) -> tuple[bool, list[str], list[str]]:
        blockers=[]; warnings=[]; settings=get_settings()
        if not settings.meta_instagram_send_enabled: blockers.append("META_SEND_DISABLED")
        conversation = DirectConversationRepository(self.db).get(workspace_id, conversation_id)
        if not conversation: blockers.append("DIRECT_CONVERSATION_NOT_FOUND")
        elif not conversation.participant_scoped_id or not conversation.instagram_connection_id: blockers.append("META_RECIPIENT_NOT_ELIGIBLE")
        elif conversation.messaging_window_expires_at and conversation.messaging_window_expires_at < datetime.now(UTC) and not human_agent_requested: blockers.append("META_MESSAGING_WINDOW_CLOSED")
        if human_agent_requested and not settings.meta_human_agent_enabled: blockers.append("META_HUMAN_AGENT_NOT_ALLOWED")
        if len(message_text) > 1000: blockers.append("META_WEBHOOK_PAYLOAD_INVALID")
        return not blockers, blockers, warnings
    async def send(self, workspace_id: UUID, conversation_id: UUID, user_id: UUID, message_text: str, idempotency_key: str, human_agent_requested: bool = False):
        fingerprint = hashlib.sha256(f"{conversation_id}:{message_text}:{human_agent_requested}".encode()).hexdigest()
        existing = self.ops.get_by_idempotency_for_update(workspace_id, idempotency_key)
        if existing:
            if existing.request_fingerprint != fingerprint: raise MetaInstagramError("META_IDEMPOTENCY_KEY_REUSED", "Idempotency key reused with different payload.", 409)
            return existing
        ready, blockers, _ = self.prepare(workspace_id, conversation_id, message_text, human_agent_requested)
        if not ready: raise MetaInstagramError(blockers[0], blockers[0])
        conversation = DirectConversationRepository(self.db).get(workspace_id, conversation_id)
        connection = InstagramConnectionRepository(self.db).get(workspace_id, conversation.instagram_connection_id)
        if not connection or connection.status != "CONNECTED" or not connection.access_token_ciphertext: raise MetaInstagramError("META_CONNECTION_NOT_READY", "Instagram connection is not ready.")
        op = self.ops.create(MetaMessageOperation(workspace_id=workspace_id, instagram_connection_id=connection.id, conversation_id=conversation_id, recipient_scoped_id=conversation.participant_scoped_id, idempotency_key=idempotency_key, request_fingerprint=fingerprint, status=MetaMessageOperationStatus.SENDING.value, started_at=datetime.now(UTC), created_by=user_id, safe_request_metadata={"message_length": len(message_text), "human_agent_requested": human_agent_requested}))
        client = MetaInstagramClient(get_settings().meta_graph_api_base_url, get_settings().meta_graph_api_version, decrypt_instagram_token(connection.access_token_ciphertext))
        result = await client.send_text_message(connection.instagram_account_id or "me", conversation.participant_scoped_id, message_text, human_agent_requested)
        msg = DirectMessageRepository(self.db).create(__import__('app.models.ai_direct', fromlist=['DirectMessage']).DirectMessage(workspace_id=workspace_id, conversation_id=conversation_id, direction=DirectMessageDirection.OUTBOUND.value, sender_type=DirectMessageSenderType.MANAGER.value, message_type=DirectMessageType.TEXT.value, text=message_text, received_at=datetime.now(UTC), processing_status="SENT", is_synthetic=False, provider="INSTAGRAM", provider_message_id=result.provider_message_id, delivery_status="SENT", sent_by_user_id=user_id))
        op.status=MetaMessageOperationStatus.COMPLETED.value; op.provider_request_id=result.provider_request_id; op.provider_message_id=result.provider_message_id; op.direct_message_id=msg.id; op.completed_at=datetime.now(UTC)
        return op
