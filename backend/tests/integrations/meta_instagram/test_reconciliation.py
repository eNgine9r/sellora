from types import SimpleNamespace
from uuid import uuid4

from app.integrations.meta_instagram.services.reconciliation_service import InstagramReconciliationService
from app.models.meta_instagram import MetaMessageOperation

class FakeOps:
    def __init__(self, op): self.op = op
    def get(self, workspace_id, operation_id): return self.op
    def get_for_update(self, workspace_id, operation_id): return self.op

class FakeMessages:
    def get_by_provider_message(self, workspace_id, provider, provider_message_id): return None
    def create(self, message): message.id = uuid4(); return message

def test_reconciliation_never_blindly_sends_without_provider_message(monkeypatch):
    op = MetaMessageOperation(workspace_id=uuid4(), conversation_id=uuid4(), instagram_connection_id=uuid4(), recipient_scoped_id="cust", idempotency_key="k", request_fingerprint="f", provider_message_id=None)
    service = InstagramReconciliationService(SimpleNamespace()); service.ops = FakeOps(op)
    result = service.reconcile(op.workspace_id, uuid4())
    assert result.status == "RECONCILIATION_REQUIRED"
    assert result.blind_retry_blocked is True
    assert result.manual_reconciliation_required is True
