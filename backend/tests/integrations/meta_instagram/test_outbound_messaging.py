from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.integrations.meta_instagram.exceptions import MetaInstagramError
from app.integrations.meta_instagram.services.outbound_message_service import InstagramOutboundMessageService
from app.models.meta_instagram import MetaMessageOperation

class FakeOps:
    def __init__(self): self.existing = None; self.created = []
    def get_by_idempotency_for_update(self, workspace_id, key): return self.existing
    def create(self, op): self.created.append(op); self.existing = op; return op
    def count_recent(self, workspace_id, conversation_id, since): return 0

class FakeConversationRepo:
    def __init__(self, conversation): self.conversation = conversation
    def get(self, workspace_id, conversation_id): return self.conversation

class FakeConnectionRepo:
    def __init__(self, connection): self.connection = connection
    def get(self, workspace_id, connection_id): return self.connection

def test_outbound_requires_messaging_window(monkeypatch):
    monkeypatch.setenv("META_INSTAGRAM_SEND_ENABLED", "true")
    from app.core.config import get_settings
    get_settings.cache_clear()
    conversation = SimpleNamespace(id=uuid4(), channel="INSTAGRAM", participant_scoped_id="cust", instagram_connection_id=uuid4(), messaging_window_expires_at=None, human_agent_window_expires_at=None)
    import app.integrations.meta_instagram.services.outbound_message_service as module
    monkeypatch.setattr(module, "DirectConversationRepository", lambda db: FakeConversationRepo(conversation))
    ready, blockers, _ = InstagramOutboundMessageService(SimpleNamespace()).prepare(uuid4(), conversation.id, "hello")
    assert ready is False
    assert "META_MESSAGING_WINDOW_CLOSED" in blockers
    get_settings.cache_clear()

def test_outbound_idempotency_rejects_different_fingerprint(monkeypatch):
    monkeypatch.setenv("META_INSTAGRAM_SEND_ENABLED", "true")
    from app.core.config import get_settings
    get_settings.cache_clear()
    workspace_id = uuid4(); conversation_id = uuid4()
    ops = FakeOps(); ops.existing = MetaMessageOperation(workspace_id=workspace_id, conversation_id=conversation_id, instagram_connection_id=uuid4(), recipient_scoped_id="cust", idempotency_key="k", request_fingerprint="different")
    import app.integrations.meta_instagram.services.outbound_message_service as module
    service = InstagramOutboundMessageService(SimpleNamespace()); service.ops = ops
    with pytest.raises(MetaInstagramError) as exc:
        service.prepare_operation(workspace_id, conversation_id, uuid4(), "hello", "k")
    assert exc.value.code == "META_IDEMPOTENCY_KEY_REUSED"
    get_settings.cache_clear()

def test_completed_idempotency_result_does_not_call_provider(monkeypatch):
    workspace_id = uuid4(); conversation_id = uuid4()
    fingerprint = InstagramOutboundMessageService(SimpleNamespace())._fingerprint(conversation_id, "hello", False)
    completed = MetaMessageOperation(workspace_id=workspace_id, conversation_id=conversation_id, instagram_connection_id=uuid4(), recipient_scoped_id="cust", idempotency_key="k", request_fingerprint=fingerprint, status="COMPLETED", provider_message_id="mid-1", direct_message_id=uuid4())
    ops = FakeOps(); ops.existing = completed
    service = InstagramOutboundMessageService(SimpleNamespace()); service.ops = ops
    result = service.prepare_operation(workspace_id, conversation_id, uuid4(), "hello", "k")
    assert result.operation is completed
    assert result.should_call_provider is False
    assert result.reused_existing is True


def test_reconciliation_required_idempotency_result_does_not_call_provider():
    workspace_id = uuid4(); conversation_id = uuid4()
    fingerprint = InstagramOutboundMessageService(SimpleNamespace())._fingerprint(conversation_id, "hello", False)
    op = MetaMessageOperation(workspace_id=workspace_id, conversation_id=conversation_id, instagram_connection_id=uuid4(), recipient_scoped_id="cust", idempotency_key="k", request_fingerprint=fingerprint, status="RECONCILIATION_REQUIRED", blind_retry_blocked=True)
    ops = FakeOps(); ops.existing = op
    service = InstagramOutboundMessageService(SimpleNamespace()); service.ops = ops
    result = service.prepare_operation(workspace_id, conversation_id, uuid4(), "hello", "k")
    assert result.should_call_provider is False
    assert result.status == "RECONCILIATION_REQUIRED"

class ConflictOps(FakeOps):
    def __init__(self, existing_after_conflict):
        super().__init__(); self.existing_after_conflict = existing_after_conflict; self.lookups = 0; self.create_attempts = 0
    def get_by_idempotency_for_update(self, workspace_id, key):
        self.lookups += 1
        return None if self.lookups == 1 else self.existing_after_conflict
    def create_with_savepoint(self, op):
        self.create_attempts += 1
        return None

def _ready_conversation(conversation_id, connection_id):
    return SimpleNamespace(id=conversation_id, channel="INSTAGRAM", participant_scoped_id="cust", instagram_connection_id=connection_id, messaging_window_expires_at=datetime.now(UTC) + timedelta(hours=1), human_agent_window_expires_at=None)

def _ready_connection(connection_id):
    return SimpleNamespace(id=connection_id, status="CONNECTED", access_token_ciphertext="encrypted", token_expires_at=datetime.now(UTC) + timedelta(days=1))

def test_concurrent_insert_conflict_reuses_same_fingerprint_without_provider_call(monkeypatch):
    monkeypatch.setenv("META_INSTAGRAM_SEND_ENABLED", "true")
    from app.core.config import get_settings
    get_settings.cache_clear()
    workspace_id = uuid4(); conversation_id = uuid4(); connection_id = uuid4()
    fingerprint = InstagramOutboundMessageService(SimpleNamespace())._fingerprint(conversation_id, "hello", False)
    existing = MetaMessageOperation(workspace_id=workspace_id, conversation_id=conversation_id, instagram_connection_id=connection_id, recipient_scoped_id="cust", idempotency_key="k", request_fingerprint=fingerprint, status="SENDING")
    import app.integrations.meta_instagram.services.outbound_message_service as module
    monkeypatch.setattr(module, "DirectConversationRepository", lambda db: FakeConversationRepo(_ready_conversation(conversation_id, connection_id)))
    monkeypatch.setattr(module, "InstagramConnectionRepository", lambda db: FakeConnectionRepo(_ready_connection(connection_id)))
    service = InstagramOutboundMessageService(SimpleNamespace()); service.ops = ConflictOps(existing)
    result = service.prepare_operation(workspace_id, conversation_id, uuid4(), "hello", "k")
    assert result.operation is existing
    assert result.should_call_provider is False
    assert result.reused_existing is True
    assert service.ops.create_attempts == 1
    get_settings.cache_clear()

def test_concurrent_insert_conflict_rejects_different_fingerprint(monkeypatch):
    monkeypatch.setenv("META_INSTAGRAM_SEND_ENABLED", "true")
    from app.core.config import get_settings
    get_settings.cache_clear()
    workspace_id = uuid4(); conversation_id = uuid4(); connection_id = uuid4()
    existing = MetaMessageOperation(workspace_id=workspace_id, conversation_id=conversation_id, instagram_connection_id=connection_id, recipient_scoped_id="cust", idempotency_key="k", request_fingerprint="different", status="SENDING")
    import app.integrations.meta_instagram.services.outbound_message_service as module
    monkeypatch.setattr(module, "DirectConversationRepository", lambda db: FakeConversationRepo(_ready_conversation(conversation_id, connection_id)))
    monkeypatch.setattr(module, "InstagramConnectionRepository", lambda db: FakeConnectionRepo(_ready_connection(connection_id)))
    service = InstagramOutboundMessageService(SimpleNamespace()); service.ops = ConflictOps(existing)
    with pytest.raises(MetaInstagramError) as exc:
        service.prepare_operation(workspace_id, conversation_id, uuid4(), "hello", "k")
    assert exc.value.code == "META_IDEMPOTENCY_KEY_REUSED"
    assert service.ops.create_attempts == 1
    get_settings.cache_clear()

def test_restart_boundary_reuses_completed_operation_without_provider_call():
    workspace_id = uuid4(); conversation_id = uuid4()
    fingerprint = InstagramOutboundMessageService(SimpleNamespace())._fingerprint(conversation_id, "hello", False)
    completed = MetaMessageOperation(workspace_id=workspace_id, conversation_id=conversation_id, instagram_connection_id=uuid4(), recipient_scoped_id="cust", idempotency_key="k", request_fingerprint=fingerprint, status="COMPLETED", provider_message_id="mid-1", direct_message_id=uuid4())
    first_session_ops = FakeOps(); first_session_ops.existing = completed
    second_session_service = InstagramOutboundMessageService(SimpleNamespace()); second_session_service.ops = first_session_ops
    provider_call_count = 0
    result = second_session_service.prepare_operation(workspace_id, conversation_id, uuid4(), "hello", "k")
    assert result.operation is completed
    assert result.should_call_provider is False
    assert result.status == "COMPLETED"
    assert provider_call_count == 0
