from uuid import uuid4

from app.models.ai_direct import DirectMessage
from app.repositories.ai_direct_repository import DirectMessageRepository

class FakeScalar:
    def __init__(self, result): self.result = result
    def scalar_one_or_none(self): return self.result

class RecordingSession:
    def __init__(self, result): self.statement = None; self.result = result
    def execute(self, statement): self.statement = statement; return FakeScalar(self.result)

def test_latest_analyzable_uses_limit_and_deterministic_ordering():
    message = DirectMessage(id=uuid4(), workspace_id=uuid4(), conversation_id=uuid4(), direction="INBOUND", sender_type="CUSTOMER", message_type="TEXT", text="hello", received_at="2026-07-18T00:00:00Z")
    session = RecordingSession(message)
    result = DirectMessageRepository(session).latest_analyzable(message.workspace_id, message.conversation_id)
    assert result is message
    statement = session.statement
    assert statement._limit_clause.value == 1
    order_by = [str(item) for item in statement._order_by_clauses]
    assert any("received_at" in item for item in order_by)
    assert any("created_at" in item for item in order_by)
    assert any("id" in item for item in order_by)
    where_text = str(statement.whereclause)
    assert "workspace_id" in where_text
    assert "conversation_id" in where_text
    assert "deleted_at" in where_text
    assert "message_type" in where_text


def test_latest_analyzable_zero_messages_returns_none():
    session = RecordingSession(None)
    assert DirectMessageRepository(session).latest_analyzable(uuid4(), uuid4()) is None
