from types import SimpleNamespace

from app.integrations.meta_instagram.services.webhook_processor_service import InstagramWebhookProcessorService


def test_webhook_worker_respects_processing_disabled(monkeypatch):
    monkeypatch.setenv("META_INSTAGRAM_WEBHOOK_PROCESSING_ENABLED", "false")
    from app.core.config import get_settings
    get_settings.cache_clear()
    service = InstagramWebhookProcessorService(SimpleNamespace())
    assert service.process_batch() == 0
    get_settings.cache_clear()
