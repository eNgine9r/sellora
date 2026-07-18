from datetime import UTC, datetime
from sqlalchemy import or_, select
from sqlalchemy.orm import Session
from app.models.meta_instagram import MetaWebhookEvent

class MetaWebhookEventRepository:
    def __init__(self, db: Session) -> None: self.db = db
    def create(self, event: MetaWebhookEvent) -> MetaWebhookEvent:
        self.db.add(event); self.db.flush(); return event
    def get_duplicate(self, provider: str, event_external_id: str | None, payload_hash: str, bucket) -> MetaWebhookEvent | None:
        stmt = select(MetaWebhookEvent).where(MetaWebhookEvent.provider == provider)
        if event_external_id:
            stmt = stmt.where(MetaWebhookEvent.event_external_id == event_external_id)
        else:
            stmt = stmt.where(MetaWebhookEvent.payload_hash == payload_hash, MetaWebhookEvent.event_date_bucket == bucket)
        return self.db.execute(stmt).scalar_one_or_none()
    def next_batch_for_update(self, limit: int = 25) -> list[MetaWebhookEvent]:
        now = datetime.now(UTC)
        return list(self.db.execute(select(MetaWebhookEvent).where(MetaWebhookEvent.status.in_(["VERIFIED", "QUEUED", "RETRY_PENDING"]), or_(MetaWebhookEvent.next_retry_at.is_(None), MetaWebhookEvent.next_retry_at <= now)).order_by(MetaWebhookEvent.received_at).limit(limit).with_for_update(skip_locked=True)).scalars())
