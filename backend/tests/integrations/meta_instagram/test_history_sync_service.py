from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.integrations.meta_instagram.exceptions import MetaInstagramError
from app.integrations.meta_instagram.history_client import (
    MetaConversationPage,
    MetaConversationSummary,
    MetaMessageDetails,
    MetaMessagePage,
    MetaMessageSummary,
)
from app.integrations.meta_instagram.services.history_sync_service import InstagramHistorySyncService


class FakeDB:
    pass


class FakeConnectionRepo:
    def __init__(self, connection):
        self.connection = connection

    def get_active(self, workspace_id):
        return self.connection if self.connection.workspace_id == workspace_id else None


class FakeSyncRepo:
    def __init__(self, sync):
        self.sync = sync

    def next_pending_for_update(self):
        return self.sync

    def get(self, workspace_id):
        return self.sync if self.sync.workspace_id == workspace_id else None


class FakeConversationRepo:
    def __init__(self):
        self.rows = []

    def get_by_external_thread(self, workspace_id, connection_id, thread_id):
        return next((row for row in self.rows if row.workspace_id == workspace_id and row.instagram_connection_id == connection_id and row.external_thread_id == thread_id), None)

    def get_by_instagram_participant(self, workspace_id, connection_id, participant_id):
        return next((row for row in self.rows if row.workspace_id == workspace_id and row.instagram_connection_id == connection_id and row.participant_scoped_id == participant_id), None)

    def get(self, workspace_id, conversation_id):
        return next((row for row in self.rows if row.workspace_id == workspace_id and row.id == conversation_id), None)

    def create(self, conversation):
        conversation.id = uuid4()
        self.rows.append(conversation)
        return conversation


class FakeMessageRepo:
    def __init__(self):
        self.rows = []

    def get_by_provider_message(self, workspace_id, provider, provider_message_id):
        return next((row for row in self.rows if row.workspace_id == workspace_id and row.provider == provider and row.provider_message_id == provider_message_id), None)

    def create(self, message):
        message.id = uuid4()
        self.rows.append(message)
        return message


class FakeProfileService:
    def enrich_if_due(self, workspace_id, conversation_id):
        return None


class FakeHistoryClient:
    def __init__(self, error=None):
        self.error = error

    async def list_conversations(self, account_id, after=None, limit=10):
        if self.error:
            raise self.error
        return MetaConversationPage(
            conversations=[MetaConversationSummary(id="thread-1", updated_time="2026-07-20T10:00:00+00:00")],
            after_cursor=None,
        )

    async def list_messages(self, conversation_id, after=None, limit=20):
        return MetaMessagePage(
            messages=[MetaMessageSummary(id="mid-1", created_time="2026-07-20T10:00:00+00:00")],
            after_cursor=None,
        )

    async def get_message(self, message_id):
        return MetaMessageDetails(
            id=message_id,
            created_time="2026-07-20T10:00:00+00:00",
            from_id="customer-1",
            from_username="customer.name",
            to=[{"id": "business-1", "username": "shop"}],
            message="Скільки коштує?",
            is_unsupported=False,
        )


def make_sync(workspace_id, connection_id):
    return SimpleNamespace(
        workspace_id=workspace_id,
        instagram_connection_id=connection_id,
        status="PENDING",
        conversation_cursor=None,
        conversation_limit=100,
        messages_per_conversation=20,
        conversation_pages_processed=0,
        conversations_discovered=0,
        conversations_synced=0,
        messages_discovered=0,
        messages_imported=0,
        messages_existing=0,
        messages_unavailable=0,
        error_count=0,
        rate_limit_count=0,
        attempt_count=0,
        last_error_code=None,
        last_error_message=None,
        next_retry_at=None,
        started_at=None,
        completed_at=None,
        last_synced_at=None,
    )


def make_service(monkeypatch, client):
    workspace_id = uuid4()
    connection_id = uuid4()
    connection = SimpleNamespace(
        id=connection_id,
        workspace_id=workspace_id,
        status="CONNECTED",
        instagram_account_id="business-1",
        access_token_ciphertext="encrypted",
    )
    sync = make_sync(workspace_id, connection_id)
    conversations = FakeConversationRepo()
    messages = FakeMessageRepo()
    monkeypatch.setattr(
        "app.integrations.meta_instagram.services.history_sync_service.decrypt_instagram_token",
        lambda value: "plain-token",
    )
    service = InstagramHistorySyncService(FakeDB(), client_factory=lambda token: client)
    service.connections = FakeConnectionRepo(connection)
    service.syncs = FakeSyncRepo(sync)
    service.conversations = conversations
    service.messages = messages
    service.profile_service = FakeProfileService()
    return workspace_id, sync, conversations, messages, service


@pytest.mark.asyncio
async def test_history_sync_imports_messages_without_creating_unread_backlog(monkeypatch):
    workspace_id, sync, conversations, messages, service = make_service(monkeypatch, FakeHistoryClient())

    result = await service.process_next()

    assert result is sync
    assert sync.status == "COMPLETED"
    assert sync.conversations_discovered == 1
    assert sync.conversations_synced == 1
    assert sync.messages_imported == 1
    assert sync.messages_existing == 0
    assert sync.last_synced_at is not None
    assert len(conversations.rows) == 1
    assert conversations.rows[0].workspace_id == workspace_id
    assert conversations.rows[0].external_thread_id == "thread-1"
    assert conversations.rows[0].participant_scoped_id == "customer-1"
    assert conversations.rows[0].unread_count == 0
    assert len(messages.rows) == 1
    assert messages.rows[0].provider_message_id == "mid-1"
    assert messages.rows[0].delivery_status == "RECEIVED"


@pytest.mark.asyncio
async def test_history_sync_is_idempotent_by_provider_message_id(monkeypatch):
    _, sync, _, messages, service = make_service(monkeypatch, FakeHistoryClient())
    await service.process_next()
    sync.status = "PENDING"
    sync.conversation_cursor = None
    sync.completed_at = None
    sync.last_synced_at = None

    await service.process_next()

    assert len(messages.rows) == 1
    assert sync.messages_existing == 1


@pytest.mark.asyncio
async def test_history_sync_rate_limit_uses_bounded_retry(monkeypatch):
    error = MetaInstagramError("META_HISTORY_RATE_LIMITED", "rate limited", 429)
    _, sync, _, _, service = make_service(monkeypatch, FakeHistoryClient(error=error))

    await service.process_next()

    assert sync.status == "RETRY_PENDING"
    assert sync.rate_limit_count == 1
    assert sync.last_error_code == "META_HISTORY_RATE_LIMITED"
    assert sync.next_retry_at > datetime.now(UTC)
