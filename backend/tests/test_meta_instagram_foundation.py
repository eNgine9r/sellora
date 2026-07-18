from __future__ import annotations

from uuid import uuid4
import hashlib, hmac, json
from types import SimpleNamespace

import pytest

from app.integrations.meta_instagram.config import REQUIRED_MESSAGING_PERMISSION, WEBHOOK_SUBSCRIPTIONS, get_meta_instagram_config
from app.integrations.meta_instagram.exceptions import MetaInstagramError
from app.integrations.meta_instagram.services.webhook_service import InstagramWebhookService
from app.integrations.meta_instagram.services.outbound_message_service import InstagramOutboundMessageService


class FakeWebhookRepo:
    def __init__(self): self.events = []
    def get_duplicate(self, provider, event_external_id, payload_hash, bucket):
        return next((e for e in self.events if e.provider == provider and (e.event_external_id == event_external_id if event_external_id else e.payload_hash == payload_hash and e.event_date_bucket == bucket)), None)
    def create(self, event):
        event.id = uuid4(); self.events.append(event); return event


class FakeWebhookService(InstagramWebhookService):
    def __init__(self): self.repo = FakeWebhookRepo(); self.db = None


def test_meta_config_defaults_disable_send_and_auto_send():
    config = get_meta_instagram_config()
    assert config.send_enabled is False
    assert config.auto_send_enabled is False
    assert config.webhook_processing_enabled is True
    assert REQUIRED_MESSAGING_PERMISSION == "instagram_business_manage_messages"
    assert WEBHOOK_SUBSCRIPTIONS == ["messages", "messaging_postbacks"]


def test_webhook_verify_uses_constant_secret(monkeypatch):
    monkeypatch.setenv("META_WEBHOOK_VERIFY_TOKEN", "verify-token")
    from app.core.config import get_settings
    get_settings.cache_clear()
    service = FakeWebhookService()
    assert service.verify_challenge("subscribe", "verify-token", "123") == "123"
    with pytest.raises(MetaInstagramError) as exc:
        service.verify_challenge("subscribe", "wrong", "123")
    assert exc.value.code == "META_WEBHOOK_VERIFY_FAILED"
    get_settings.cache_clear()


def test_webhook_signature_validation(monkeypatch):
    monkeypatch.setenv("META_APP_SECRET", "secret")
    from app.core.config import get_settings
    get_settings.cache_clear()
    body = b'{"object":"instagram","entry":[]}'
    signature = "sha256=" + hmac.new(b"secret", body, hashlib.sha256).hexdigest()
    service = FakeWebhookService()
    service.validate_signature(body, signature)
    with pytest.raises(MetaInstagramError) as exc:
        service.validate_signature(body, "sha256=bad")
    assert exc.value.code == "META_WEBHOOK_SIGNATURE_INVALID"
    get_settings.cache_clear()


def test_webhook_persistence_deduplicates_by_event_id(monkeypatch):
    import app.integrations.meta_instagram.services.webhook_service as module
    monkeypatch.setattr(module, "InstagramConnectionRepository", lambda db: SimpleNamespace(get_by_account=lambda account_id: None))
    payload = {"object": "instagram", "entry": [{"id": "ig-1", "messaging": [{"sender": {"id": "cust-1"}, "message": {"mid": "mid-1", "text": "Привіт"}}]}]}
    body = json.dumps(payload).encode()
    service = FakeWebhookService()
    first = service.persist_verified_event(body, payload)
    second = service.persist_verified_event(body, payload)
    assert first.id == second.id
    assert first.signature_verified is True
    assert first.status == "VERIFIED"


def test_outbound_prepare_blocks_when_send_disabled(monkeypatch):
    class FakeConversationRepo:
        def get(self, workspace_id, conversation_id): return None
    import app.integrations.meta_instagram.services.outbound_message_service as module
    monkeypatch.setattr(module, "DirectConversationRepository", lambda db: FakeConversationRepo())
    service = InstagramOutboundMessageService(SimpleNamespace())
    ready, blockers, warnings = service.prepare(uuid4(), uuid4(), "Доброго дня")
    assert ready is False
    assert "META_SEND_DISABLED" in blockers
    assert warnings == []
