from datetime import UTC, datetime, timedelta
from sqlalchemy.orm import Session
from app.core.config import get_settings
from app.integrations.meta_instagram.repositories.webhook_event_repository import MetaWebhookEventRepository
from app.integrations.meta_instagram.services.inbound_message_service import InstagramInboundMessageService
from app.models.meta_instagram import MetaWebhookEventStatus

class InstagramWebhookProcessorService:
    def __init__(self, db: Session) -> None:
        self.db = db; self.repo = MetaWebhookEventRepository(db)
    def process_batch(self, limit: int = 25) -> int:
        if not get_settings().meta_instagram_webhook_processing_enabled:
            return 0
        events = self.repo.next_batch_for_update(limit)
        for event in events:
            event.status = MetaWebhookEventStatus.PROCESSING.value
            event.processing_started_at = datetime.now(UTC)
        self.db.flush()
        processed = 0
        for event in events:
            try:
                InstagramInboundMessageService(self.db).process_event(event)
                processed += 1
            except ValueError as exc:
                event.status = MetaWebhookEventStatus.FAILED_SAFE.value
                event.safe_error_code = "META_WEBHOOK_EVENT_UNSUPPORTED"
                event.safe_error_message = str(exc)[:300]
            except Exception as exc:
                event.attempt_count = (event.attempt_count or 0) + 1
                if event.attempt_count >= 3:
                    event.status = MetaWebhookEventStatus.DEAD_LETTER.value
                    event.safe_error_code = "META_WEBHOOK_PROCESSING_FAILED"
                else:
                    event.status = MetaWebhookEventStatus.RETRY_PENDING.value
                    event.safe_error_code = "META_WEBHOOK_PROCESSING_FAILED"
                    event.next_retry_at = datetime.now(UTC) + timedelta(minutes=2 ** event.attempt_count)
                event.safe_error_message = exc.__class__.__name__
        return processed
