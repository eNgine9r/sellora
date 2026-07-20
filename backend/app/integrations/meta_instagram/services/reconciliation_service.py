from datetime import UTC, datetime
from uuid import UUID
from sqlalchemy.orm import Session
from app.integrations.meta_instagram.exceptions import MetaInstagramError
from app.integrations.meta_instagram.repositories.message_operation_repository import MetaMessageOperationRepository
from app.models.ai_direct import DirectMessage, DirectMessageDirection, DirectMessageSenderType, DirectMessageType
from app.models.meta_instagram import MetaMessageOperation, MetaMessageOperationStatus
from app.repositories.ai_direct_repository import DirectMessageRepository

class InstagramReconciliationService:
    def __init__(self, db: Session) -> None: self.db = db; self.ops = MetaMessageOperationRepository(db)
    def status(self, workspace_id: UUID, operation_id: UUID) -> MetaMessageOperation:
        op = self.ops.get(workspace_id, operation_id)
        if not op: raise MetaInstagramError("META_MESSAGE_OPERATION_ACTIVE", "Message operation not found.", 404)
        return op
    def reconcile(self, workspace_id: UUID, operation_id: UUID) -> MetaMessageOperation:
        op = self.ops.get_for_update(workspace_id, operation_id)
        if not op: raise MetaInstagramError("META_MESSAGE_OPERATION_ACTIVE", "Message operation not found.", 404)
        if not op.provider_message_id:
            op.status = MetaMessageOperationStatus.RECONCILIATION_REQUIRED.value
            op.manual_reconciliation_required = True
            op.blind_retry_blocked = True
            return op
        existing = DirectMessageRepository(self.db).get_by_provider_message(workspace_id, "INSTAGRAM", op.provider_message_id)
        if existing:
            op.direct_message_id = existing.id
        else:
            msg = DirectMessageRepository(self.db).create(DirectMessage(workspace_id=workspace_id, conversation_id=op.conversation_id, direction=DirectMessageDirection.OUTBOUND.value, sender_type=DirectMessageSenderType.MANAGER.value, message_type=DirectMessageType.TEXT.value, text="[Reconciled Instagram outbound message]", received_at=datetime.now(UTC), processing_status="SENT", is_synthetic=False, provider="INSTAGRAM", provider_message_id=op.provider_message_id, delivery_status="PROVIDER_ACCEPTED", sent_by_user_id=op.created_by))
            op.direct_message_id = msg.id
        op.status = MetaMessageOperationStatus.COMPLETED.value
        op.completed_at = datetime.now(UTC)
        op.manual_reconciliation_required = False
        op.blind_retry_blocked = False
        return op