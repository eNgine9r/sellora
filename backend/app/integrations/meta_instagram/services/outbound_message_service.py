from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID
import hashlib
from sqlalchemy.orm import Session
from app.core.config import get_settings
from app.integrations.meta_instagram.client import MetaInstagramClient, MetaSendResult
from app.integrations.meta_instagram.crypto import decrypt_instagram_token
from app.integrations.meta_instagram.exceptions import MetaInstagramError
from app.integrations.meta_instagram.repositories.connection_repository import InstagramConnectionRepository
from app.integrations.meta_instagram.repositories.message_operation_repository import MetaMessageOperationRepository
from app.models.ai_direct import DirectMessage, DirectMessageDirection, DirectMessageSenderType, DirectMessageType
from app.models.meta_instagram import MetaMessageOperation, MetaMessageOperationStatus
from app.repositories.ai_direct_repository import DirectConversationRepository, DirectMessageRepository

@dataclass(frozen=True)
class PreparedOperationResult:
    operation: MetaMessageOperation
    should_call_provider: bool
    reused_existing: bool
    status: str

class InstagramOutboundMessageService:
    def __init__(self, db: Session, client_factory=None) -> None:
        self.db = db; self.ops = MetaMessageOperationRepository(db); self.client_factory = client_factory
    def prepare(self, workspace_id: UUID, conversation_id: UUID, message_text: str, human_agent_requested: bool = False) -> tuple[bool, list[str], list[str]]:
        blockers=[]; warnings=[]; settings=get_settings()
        if not settings.meta_instagram_send_enabled: blockers.append("META_SEND_DISABLED")
        conversation = DirectConversationRepository(self.db).get(workspace_id, conversation_id)
        if not conversation: blockers.append("DIRECT_CONVERSATION_NOT_FOUND")
        else:
            if conversation.channel == "SYNTHETIC": blockers.append("META_RECIPIENT_NOT_ELIGIBLE")
            if not conversation.participant_scoped_id or not conversation.instagram_connection_id: blockers.append("META_RECIPIENT_NOT_ELIGIBLE")
            now = datetime.now(UTC)
            if not conversation.messaging_window_expires_at: blockers.append("META_MESSAGING_WINDOW_CLOSED")
            elif conversation.messaging_window_expires_at < now and not human_agent_requested: blockers.append("META_MESSAGING_WINDOW_CLOSED")
            if human_agent_requested:
                if not settings.meta_human_agent_enabled: blockers.append("META_HUMAN_AGENT_NOT_ALLOWED")
                if not conversation.human_agent_window_expires_at or conversation.human_agent_window_expires_at < now: blockers.append("META_HUMAN_AGENT_NOT_ALLOWED")
        if len(message_text) > 1000: blockers.append("META_WEBHOOK_PAYLOAD_INVALID")
        return not blockers, blockers, warnings
    def prepare_operation(self, workspace_id: UUID, conversation_id: UUID, user_id: UUID, message_text: str, idempotency_key: str, human_agent_requested: bool = False) -> PreparedOperationResult:
        fingerprint = self._fingerprint(conversation_id, message_text, human_agent_requested)
        existing = self.ops.get_by_idempotency_for_update(workspace_id, idempotency_key)
        if existing:
            return self._prepared_from_existing(existing, fingerprint)
        self._rate_limit(workspace_id, conversation_id)
        ready, blockers, _ = self.prepare(workspace_id, conversation_id, message_text, human_agent_requested)
        if not ready: raise MetaInstagramError(blockers[0], blockers[0])
        conversation = DirectConversationRepository(self.db).get(workspace_id, conversation_id)
        connection = InstagramConnectionRepository(self.db).get(workspace_id, conversation.instagram_connection_id)
        if not connection or connection.status != "CONNECTED" or not connection.access_token_ciphertext: raise MetaInstagramError("META_CONNECTION_NOT_READY", "Instagram connection is not ready.")
        if connection.token_expires_at and connection.token_expires_at < datetime.now(UTC): raise MetaInstagramError("META_TOKEN_EXPIRED", "Instagram token expired.")
        op = MetaMessageOperation(workspace_id=workspace_id, instagram_connection_id=connection.id, conversation_id=conversation_id, recipient_scoped_id=conversation.participant_scoped_id, idempotency_key=idempotency_key, request_fingerprint=fingerprint, status=MetaMessageOperationStatus.SENDING.value, started_at=datetime.now(UTC), created_by=user_id, messaging_window_expires_at=conversation.messaging_window_expires_at, human_agent_allowed=human_agent_requested, safe_request_metadata={"message_length": len(message_text), "human_agent_requested": human_agent_requested, "message_hash": hashlib.sha256(message_text.encode()).hexdigest()})
        created = self.ops.create_with_savepoint(op)
        if created:
            return PreparedOperationResult(operation=created, should_call_provider=True, reused_existing=False, status=MetaMessageOperationStatus.SENDING.value)
        existing_after_conflict = self.ops.get_by_idempotency_for_update(workspace_id, idempotency_key)
        if existing_after_conflict:
            return self._prepared_from_existing(existing_after_conflict, fingerprint)
        raise MetaInstagramError("META_MESSAGE_OPERATION_ACTIVE", "Message operation could not be prepared safely.", 409)
    async def call_provider(self, workspace_id: UUID, operation_id: UUID, message_text: str) -> MetaSendResult:
        op = self.ops.get(workspace_id, operation_id)
        if not op: raise MetaInstagramError("META_MESSAGE_OPERATION_ACTIVE", "Message operation not found.", 404)
        connection = InstagramConnectionRepository(self.db).get(workspace_id, op.instagram_connection_id)
        if not connection or not connection.access_token_ciphertext: raise MetaInstagramError("META_CONNECTION_NOT_READY", "Instagram connection is not ready.")
        token = decrypt_instagram_token(connection.access_token_ciphertext)
        instagram_account_id = connection.instagram_account_id or "me"
        recipient_scoped_id = op.recipient_scoped_id
        human_agent_allowed = op.human_agent_allowed
        self.db.commit()
        client = self.client_factory(token) if self.client_factory else MetaInstagramClient(get_settings().meta_graph_api_base_url, get_settings().meta_graph_api_version, token)
        return await client.send_text_message(instagram_account_id, recipient_scoped_id, message_text, human_agent_allowed)
    def finalize_success(self, workspace_id: UUID, operation_id: UUID, message_text: str, result: MetaSendResult) -> MetaMessageOperation:
        op = self.ops.get_for_update(workspace_id, operation_id)
        if not op: raise MetaInstagramError("META_MESSAGE_OPERATION_ACTIVE", "Message operation not found.", 404)
        existing = DirectMessageRepository(self.db).get_by_provider_message(workspace_id, "INSTAGRAM", result.provider_message_id or "") if result.provider_message_id else None
        if existing:
            msg = existing
        else:
            msg = DirectMessageRepository(self.db).create(DirectMessage(workspace_id=workspace_id, conversation_id=op.conversation_id, direction=DirectMessageDirection.OUTBOUND.value, sender_type=DirectMessageSenderType.MANAGER.value, message_type=DirectMessageType.TEXT.value, text=message_text, received_at=datetime.now(UTC), sent_at=datetime.now(UTC), processing_status="SENT", is_synthetic=False, provider="INSTAGRAM", provider_message_id=result.provider_message_id, delivery_status="SENT", sent_by_user_id=op.created_by))
        op.status=MetaMessageOperationStatus.COMPLETED.value; op.provider_request_id=result.provider_request_id; op.provider_message_id=result.provider_message_id; op.direct_message_id=msg.id; op.completed_at=datetime.now(UTC); op.provider_succeeded_at=datetime.now(UTC); op.safe_result_metadata={"provider_status": result.raw_status}
        conversation = DirectConversationRepository(self.db).get(workspace_id, op.conversation_id)
        if conversation: conversation.last_outbound_message_at = datetime.now(UTC); conversation.last_message_at = datetime.now(UTC)
        connection = InstagramConnectionRepository(self.db).get(workspace_id, op.instagram_connection_id)
        if connection: connection.last_message_sent_at = datetime.now(UTC)
        return op
    def finalize_failure(self, workspace_id: UUID, operation_id: UUID, exc: MetaInstagramError) -> MetaMessageOperation:
        op = self.ops.get_for_update(workspace_id, operation_id)
        if not op: raise exc
        if exc.code == "META_RECONCILIATION_REQUIRED":
            op.status = MetaMessageOperationStatus.RECONCILIATION_REQUIRED.value; op.blind_retry_blocked = True; op.manual_reconciliation_required = True
        elif exc.status_code in {429, 503, 504}:
            op.status = MetaMessageOperationStatus.RETRY_PENDING.value
        else:
            op.status = MetaMessageOperationStatus.FAILED_SAFE.value
        op.last_error_code = exc.code; op.last_error_message = exc.message[:300]
        return op
    async def send(self, workspace_id: UUID, conversation_id: UUID, user_id: UUID, message_text: str, idempotency_key: str, human_agent_requested: bool = False):
        return self.prepare_operation(workspace_id, conversation_id, user_id, message_text, idempotency_key, human_agent_requested).operation
    def _prepared_from_existing(self, existing: MetaMessageOperation, fingerprint: str) -> PreparedOperationResult:
        if existing.request_fingerprint != fingerprint:
            raise MetaInstagramError("META_IDEMPOTENCY_KEY_REUSED", "Idempotency key reused with different payload.", 409)
        return PreparedOperationResult(operation=existing, should_call_provider=False, reused_existing=True, status=existing.status)
    def _fingerprint(self, conversation_id: UUID, message_text: str, human_agent_requested: bool) -> str:
        return hashlib.sha256(f"{conversation_id}:{message_text}:{human_agent_requested}".encode()).hexdigest()
    def _rate_limit(self, workspace_id: UUID, conversation_id: UUID) -> None:
        since = datetime.now(UTC) - timedelta(minutes=1)
        settings = get_settings()
        if self.ops.count_recent(workspace_id, None, since) >= settings.meta_outbound_workspace_rate_limit:
            raise MetaInstagramError("META_WORKSPACE_RATE_LIMITED", "Workspace Instagram send rate limit exceeded.", 429)
        if self.ops.count_recent(workspace_id, conversation_id, since) >= settings.meta_outbound_conversation_rate_limit:
            raise MetaInstagramError("META_CONVERSATION_RATE_LIMITED", "Conversation Instagram send rate limit exceeded.", 429)
