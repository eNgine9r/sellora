from datetime import UTC, datetime, timedelta
from typing import Any
import hashlib
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.integrations.meta_instagram.repositories.connection_repository import InstagramConnectionRepository
from app.models.ai_direct import DirectChannel, DirectMessage, DirectMessageDirection, DirectMessageSenderType, DirectMessageType
from app.models.meta_instagram import MetaMessageOperationStatus, MetaWebhookEvent, MetaWebhookEventStatus
from app.repositories.ai_direct_repository import DirectConversationRepository, DirectMessageRepository
from app.integrations.meta_instagram.repositories.message_operation_repository import MetaMessageOperationRepository

MEDIA_TYPES = {"image": "IMAGE", "video": "VIDEO", "audio": "AUDIO", "sticker": "STICKER", "share": "SHARE"}

class InstagramInboundMessageService:
    def __init__(self, db: Session) -> None:
        self.db = db; self.conversations = DirectConversationRepository(db); self.messages = DirectMessageRepository(db)
    def process_event(self, event: MetaWebhookEvent) -> int:
        connection = InstagramConnectionRepository(self.db).get_active(event.workspace_id) if event.workspace_id else None
        if not connection:
            event.status = MetaWebhookEventStatus.IGNORED.value; event.processed_at = datetime.now(UTC); return 0
        created = 0
        for entry in event.payload.get("entry", []) or []:
            for item in entry.get("messaging", []) or []:
                created += self._process_item(event, connection.id, item)
        event.status = MetaWebhookEventStatus.PROCESSED.value; event.processed_at = datetime.now(UTC)
        connection.last_webhook_at = datetime.now(UTC)
        return created
    def _process_item(self, event: MetaWebhookEvent, connection_id, item: dict[str, Any]) -> int:
        recipient_id = str((item.get("recipient") or {}).get("id") or "")
        sender_id = str((item.get("sender") or {}).get("id") or "")
        message = item.get("message") or {}
        postback = item.get("postback") or {}
        is_echo = bool(message.get("is_echo")) or bool(sender_id and recipient_id and sender_id == str(event.payload.get("entry", [{}])[0].get("id", "")))
        participant_id = recipient_id if is_echo else sender_id
        if not participant_id: return 0
        provider_message_id = str(message.get("mid") or postback.get("mid") or postback.get("payload") or event.event_external_id or self._hash_item(item))
        if self.messages.get_by_provider_message(event.workspace_id, "INSTAGRAM", provider_message_id): return 0
        conversation = self._conversation(event.workspace_id, connection_id, participant_id)
        provider_created_at = self._provider_time(item)
        payload_type, text, message_type = self._payload(message, postback)
        direction = DirectMessageDirection.OUTBOUND.value if is_echo else DirectMessageDirection.INBOUND.value
        sender_type = DirectMessageSenderType.MANAGER.value if is_echo else DirectMessageSenderType.CUSTOMER.value
        direct_message = DirectMessage(workspace_id=event.workspace_id, conversation_id=conversation.id, direction=direction, sender_type=sender_type, message_type=message_type, text=text, safe_text_hash=hashlib.sha256((text or provider_message_id).encode()).hexdigest(), received_at=provider_created_at, processing_status="RECEIVED", is_synthetic=False, provider="INSTAGRAM", provider_message_id=provider_message_id, provider_event_id=event.event_external_id, delivery_status="SENT" if is_echo else "UNKNOWN", message_payload_type=payload_type, provider_created_at=provider_created_at, attachment_metadata=self._metadata(message, postback))
        try:
            self.messages.create(direct_message)
        except IntegrityError:
            self.db.rollback(); return 0
        conversation.channel = DirectChannel.INSTAGRAM.value
        conversation.instagram_connection_id = connection_id
        conversation.participant_scoped_id = participant_id
        conversation.last_message_at = provider_created_at
        if is_echo:
            conversation.last_outbound_message_at = provider_created_at
            op = MetaMessageOperationRepository(self.db).get_by_provider_message(event.workspace_id, provider_message_id)
            if op and not op.direct_message_id:
                op.direct_message_id = direct_message.id; op.status = MetaMessageOperationStatus.COMPLETED.value; op.completed_at = datetime.now(UTC)
        else:
            conversation.unread_count = (conversation.unread_count or 0) + 1
            conversation.last_inbound_message_at = provider_created_at
            conversation.messaging_window_expires_at = provider_created_at + timedelta(hours=24)
            conversation.human_agent_window_expires_at = provider_created_at + timedelta(days=7)
        return 1
    def _conversation(self, workspace_id, connection_id, participant_id):
        existing = self.conversations.get_by_instagram_participant(workspace_id, connection_id, participant_id)
        if existing: return existing
        from app.models.ai_direct import DirectConversation
        return self.conversations.create(DirectConversation(workspace_id=workspace_id, channel=DirectChannel.INSTAGRAM.value, instagram_connection_id=connection_id, participant_scoped_id=participant_id, participant_display_name="Instagram customer", unread_count=0, last_message_at=datetime.now(UTC)))
    def _provider_time(self, item: dict[str, Any]) -> datetime:
        ts = item.get("timestamp")
        return datetime.fromtimestamp(ts / 1000, UTC) if ts else datetime.now(UTC)
    def _payload(self, message: dict[str, Any], postback: dict[str, Any]) -> tuple[str, str, str]:
        if postback: return "POSTBACK", str(postback.get("title") or postback.get("payload") or "Instagram postback"), DirectMessageType.SYSTEM_EVENT.value
        if message.get("text"): return "TEXT", str(message.get("text")), DirectMessageType.TEXT.value
        for key, label in MEDIA_TYPES.items():
            if message.get(key): return label, f"[{label.lower()} Instagram message]", DirectMessageType.SYSTEM_EVENT.value
        return "UNSUPPORTED", "[Unsupported Instagram message]", DirectMessageType.SYSTEM_EVENT.value
    def _metadata(self, message: dict[str, Any], postback: dict[str, Any]) -> dict[str, Any]:
        if postback: return {"postback_payload_present": bool(postback.get("payload"))}
        return {key: True for key in MEDIA_TYPES if message.get(key)}
    def _hash_item(self, item: dict[str, Any]) -> str:
        return hashlib.sha256(repr(sorted(item.items())).encode()).hexdigest()
