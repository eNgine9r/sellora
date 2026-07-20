from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.integrations.meta_instagram.exceptions import MetaInstagramError
from app.integrations.meta_instagram.history_client import (
    MetaConversationPage,
    MetaConversationSummary,
    MetaMessagePage,
    MetaMessageSummary,
)
from app.integrations.meta_instagram.services.history_sync_visibility_service import (
    InstagramHistorySyncVisibilityService,
)


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


class FakeConversationRepo:
    def __init__(self, rows=None):
        self.rows = list(rows or [])

    def get_by_external_thread(self, workspace_id, connection_id, thread_id):
        return next(
            (
                row
                for row in self.rows
                if row.workspace_id == workspace_id
                and row.instagram_connection_id == connection_id
                and row.external_thread_id == thread_id
            ),
            None,
        )

    def get_by_instagram_participant(self, workspace_id, connection_id, participant_id):
        return next(
            (
                row
                for row in self.rows
                if row.workspace_id == workspace_id
                and row.instagram_connection_id == connection_id
                and row.participant_scoped_id == participant_id
            ),
            None,
        )

    def get(self, workspace_id, conversation_id):
        return next(
            (
                row
                for row in self.rows
                if row.workspace_id == workspace_id and row.id == conversation_id
            ),
            None,
        )

    def create(self, conversation):
        conversation.id = uuid4()
        self.rows.append(conversation)
        return conversation


class FakeMessageRepo:
    def __init__(self, rows=None):
        self.rows = list(rows or [])

    def get_by_provider_message(self, workspace_id, provider, provider_message_id):
        return next(
            (
                row
                for row in self.rows
                if row.workspace_id == workspace_id
                and row.provider == provider
                and row.provider_message_id == provider_message_id
            ),
            None,
        )

    def create(self, message):
        message.id = uuid4()
        self.rows.append(message)
        return message


class FakeProfileService:
    def enrich_if_due(self, workspace_id, conversation_id):
        return None


class FakeHistoryClient:
    def __init__(self, *, message_id="mid-1", unavailable=False):
        self.message_id = message_id
        self.unavailable = unavailable

    async def list_conversations(self, account_id, after=None, limit=10):
        return MetaConversationPage(
            conversations=[MetaConversationSummary(id="thread-1")],
            after_cursor=None,
        )

    async def list_messages(self, conversation_id, after=None, limit=20):
        return MetaMessagePage(
            messages=[MetaMessageSummary(id=self.message_id)],
            after_cursor=None,
        )

    async def get_message(self, message_id):
        if self.unavailable:
            raise MetaInstagramError(
                "META_HISTORY_MESSAGE_UNAVAILABLE",
                "Meta no longer exposes details for this historical message.",
                404,
            )
        raise AssertionError("Existing provider messages must not be fetched again")


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


def make_service(client, *, conversation=None, message=None):
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
    conversations = FakeConversationRepo([conversation] if conversation else [])
    messages = FakeMessageRepo([message] if message else [])
    service = InstagramHistorySyncVisibilityService(
        FakeDB(),
        client_factory=lambda token: client,
    )
    service.connections = FakeConnectionRepo(connection)
    service.syncs = FakeSyncRepo(sync)
    service.conversations = conversations
    service.messages = messages
    service.profile_service = FakeProfileService()
    service._decrypt = lambda value: "plain-token"
    return workspace_id, connection_id, sync, conversations, messages, service


@pytest.mark.asyncio
async def test_existing_messages_link_provider_thread_and_count_visible_dialog():
    conversation_id = uuid4()
    workspace_id = uuid4()
    connection_id = uuid4()
    conversation = SimpleNamespace(
        id=conversation_id,
        workspace_id=workspace_id,
        instagram_connection_id=connection_id,
        external_thread_id=None,
        external_conversation_id=None,
        participant_scoped_id="customer-1",
        provider_sync_status=None,
    )
    message = SimpleNamespace(
        workspace_id=workspace_id,
        conversation_id=conversation_id,
        provider="INSTAGRAM",
        provider_message_id="mid-existing",
    )
    client = FakeHistoryClient(message_id="mid-existing")
    _, _, sync, conversations, _, service = make_service(client)
    service.connections.connection.workspace_id = workspace_id
    service.connections.connection.id = connection_id
    sync.workspace_id = workspace_id
    sync.instagram_connection_id = connection_id
    service.conversations = FakeConversationRepo([conversation])
    service.messages = FakeMessageRepo([message])

    await service.process_next()

    assert sync.conversations_discovered == 1
    assert sync.conversations_synced == 1
    assert sync.messages_existing == 1
    assert conversation.external_thread_id == "thread-1"
    assert conversation.external_conversation_id == "thread-1"
    assert conversation.provider_sync_status == "HISTORY_SYNCED"
    assert len(conversations.rows) == 0


@pytest.mark.asyncio
async def test_unavailable_only_provider_thread_is_not_reported_as_visible_dialog():
    client = FakeHistoryClient(unavailable=True)
    _, _, sync, conversations, _, service = make_service(client)

    await service.process_next()

    assert sync.status == "PARTIAL"
    assert sync.conversations_discovered == 1
    assert sync.conversations_synced == 0
    assert sync.messages_unavailable == 1
    assert conversations.rows == []


@pytest.mark.asyncio
async def test_existing_conversation_thread_is_not_overwritten_by_another_provider_thread():
    workspace_id = uuid4()
    connection_id = uuid4()
    conversation_id = uuid4()
    conversation = SimpleNamespace(
        id=conversation_id,
        workspace_id=workspace_id,
        instagram_connection_id=connection_id,
        external_thread_id="thread-original",
        external_conversation_id="thread-original",
        participant_scoped_id="customer-1",
        provider_sync_status="HISTORY_SYNCED",
    )
    message = SimpleNamespace(
        workspace_id=workspace_id,
        conversation_id=conversation_id,
        provider="INSTAGRAM",
        provider_message_id="mid-existing",
    )
    client = FakeHistoryClient(message_id="mid-existing")
    _, _, sync, _, _, service = make_service(client)
    service.connections.connection.workspace_id = workspace_id
    service.connections.connection.id = connection_id
    sync.workspace_id = workspace_id
    sync.instagram_connection_id = connection_id
    service.conversations = FakeConversationRepo([conversation])
    service.messages = FakeMessageRepo([message])

    await service.process_next()

    assert sync.conversations_discovered == 1
    assert sync.conversations_synced == 0
    assert conversation.external_thread_id == "thread-original"
    assert conversation.external_conversation_id == "thread-original"
