from types import SimpleNamespace
from uuid import uuid4

from app.integrations.meta_instagram.services.inbound_message_service import InstagramInboundMessageService
from app.models.meta_instagram import MetaWebhookEvent

class FakeConnectionRepo:
    def __init__(self, db): pass
    def get_active(self, workspace_id): return SimpleNamespace(id=uuid4(), workspace_id=workspace_id, status="DISCONNECTED")

def test_disconnected_connection_ignores_inbound_event(monkeypatch):
    import app.integrations.meta_instagram.services.inbound_message_service as module
    monkeypatch.setattr(module, "InstagramConnectionRepository", FakeConnectionRepo)
    event = MetaWebhookEvent(workspace_id=uuid4(), provider="INSTAGRAM", object_type="instagram", event_type="messages", payload_hash="hash", payload={"entry": [{"id": "ig", "messaging": [{"sender": {"id": "cust"}, "message": {"mid": "mid", "text": "hello"}}]}]}, signature_verified=True, status="VERIFIED")
    created = InstagramInboundMessageService(SimpleNamespace()).process_event(event)
    assert created == 0
    assert event.status == "IGNORED"
    assert event.safe_error_code == "META_CONNECTION_NOT_READY"
