from uuid import UUID
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models.meta_instagram import MetaMessageOperation

class MetaMessageOperationRepository:
    def __init__(self, db: Session) -> None: self.db = db
    def create(self, op: MetaMessageOperation) -> MetaMessageOperation:
        self.db.add(op); self.db.flush(); return op
    def get(self, workspace_id: UUID, operation_id: UUID) -> MetaMessageOperation | None:
        return self.db.execute(select(MetaMessageOperation).where(MetaMessageOperation.workspace_id == workspace_id, MetaMessageOperation.id == operation_id)).scalar_one_or_none()
    def get_for_update(self, workspace_id: UUID, operation_id: UUID) -> MetaMessageOperation | None:
        return self.db.execute(select(MetaMessageOperation).where(MetaMessageOperation.workspace_id == workspace_id, MetaMessageOperation.id == operation_id).with_for_update()).scalar_one_or_none()
    def get_by_idempotency_for_update(self, workspace_id: UUID, idempotency_key: str) -> MetaMessageOperation | None:
        return self.db.execute(select(MetaMessageOperation).where(MetaMessageOperation.workspace_id == workspace_id, MetaMessageOperation.idempotency_key == idempotency_key).with_for_update()).scalar_one_or_none()
    def get_by_provider_message(self, workspace_id: UUID, provider_message_id: str) -> MetaMessageOperation | None:
        return self.db.execute(select(MetaMessageOperation).where(MetaMessageOperation.workspace_id == workspace_id, MetaMessageOperation.provider_message_id == provider_message_id)).scalar_one_or_none()
    def count_recent(self, workspace_id: UUID, conversation_id: UUID | None, since) -> int:
        stmt = select(MetaMessageOperation).where(MetaMessageOperation.workspace_id == workspace_id, MetaMessageOperation.created_at >= since)
        if conversation_id is not None: stmt = stmt.where(MetaMessageOperation.conversation_id == conversation_id)
        return len(list(self.db.execute(stmt).scalars()))
