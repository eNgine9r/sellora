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
from app.integrations.meta_instagram.runtime_worker import InstagramHistorySyncService as WorkerHistorySyncService


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
        self.cancel_requested = False
        self.worker_locked = False

    def next_pending_for_update(self):
        return self.sync if self.sync.status in {"PENDING", "RETRY_PENDING"} else None

    def get(self, workspace_id):
        return self.sync if self.sync.workspace_id == workspace_id else None

    def get_for_update_skip_locked(self, workspace_id):
        return None if self.worker_locked else self.get(workspace_id)

    def request_cancel(self, workspace_id, sync_id, user_id):
        assert self.sync.workspace_id == workspace_id and self.sync.id == sync_id
        self.cancel_requested = True

    def cancellation_requested(self, workspace_id, sync_id):
        return self.cancel_requested and self.sync.workspace_id == workspace_id and self.sync.id == sync_id

    def clear_cancellation(self, workspace_id):
        self.cancel_requested = False


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
        id=uuid4(),
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


def make_service(monkeypatch, client, service_type=InstagramHistorySyncService):
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
    service = service_type(FakeDB(), client_factory=lambda token: client)
    service._decrypt = lambda value: "plain-token"
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


class InlineHistoryClient(FakeHistoryClient):
    def __init__(self, *, attachment=False):
        super().__init__()
        self.detail_requests = 0
        self.attachment = attachment

    async def list_messages(self, conversation_id, after=None, limit=20):
        details = await super().get_message("mid-inline")
        if self.attachment:
            from dataclasses import replace
            details = replace(details, message=None, attachments=[{
                "type": "image", "url": "https://example.com/synthetic-history.jpg",
            }])
        return MetaMessagePage(messages=[MetaMessageSummary(
            id="mid-inline", created_time=details.created_time, details=details, details_complete=True,
        )])

    async def get_message(self, message_id):
        self.detail_requests += 1
        raise MetaInstagramError(
            "META_HISTORY_ACCESS_DENIED", "Standalone historical message is unavailable.", 400,
        )


@pytest.mark.asyncio
@pytest.mark.parametrize("attachment", [False, True])
@pytest.mark.parametrize("production", [False, True])
async def test_history_sync_uses_inline_details_when_standalone_lookup_is_denied(monkeypatch, attachment, production):
    client = InlineHistoryClient(attachment=attachment)
    workspace_id, sync, conversations, messages, service = make_service(monkeypatch, client, WorkerHistorySyncService if production else InstagramHistorySyncService)

    await service.process_next()

    assert sync.status == "COMPLETED"
    assert sync.error_count == 0
    assert sync.messages_imported == 1
    assert client.detail_requests == 0
    assert len(conversations.rows) == 1
    assert messages.rows[0].workspace_id == workspace_id
    assert messages.rows[0].provider_message_id == "mid-inline"
    assert not messages.rows[0].is_synthetic
    if attachment:
        assert messages.rows[0].attachment_metadata["attachments"][0]["type"] == "image"
    else:
        assert messages.rows[0].text == "Скільки коштує?"

    sync.status = "PENDING"
    sync.conversations_discovered = 0
    await service.process_next()
    assert len(messages.rows) == 1
    assert sync.messages_existing == 1
    assert client.detail_requests == 0


class ReducedInlineHistoryClient(InlineHistoryClient):
    def __init__(self, mode):
        super().__init__()
        self.mode = mode

    async def list_messages(self, conversation_id, after=None, limit=20):
        from dataclasses import replace
        page = await super().list_messages(conversation_id, after, limit)
        summary = page.messages[0]
        details = summary.details
        if self.mode in {"hydrate_media", "empty_denied"}:
            details = replace(details, message="")
        return MetaMessagePage(messages=[replace(summary, details=details, details_complete=False)])

    async def get_message(self, message_id):
        self.detail_requests += 1
        if self.mode == "hydrate_media":
            from dataclasses import replace
            details = await FakeHistoryClient.get_message(self, message_id)
            return replace(details, message="", attachments=[{
                "type": "image", "url": "https://example.com/synthetic-hydrated.jpg",
            }])
        code = "META_HISTORY_PROVIDER_UNAVAILABLE" if self.mode == "temporary_error" else "META_HISTORY_ACCESS_DENIED"
        raise MetaInstagramError(code, "Synthetic standalone lookup rejected.", 503 if self.mode == "temporary_error" else 400)


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", ["hydrate_media", "text_denied", "empty_denied", "temporary_error"])
@pytest.mark.parametrize("production", [False, True])
async def test_reduced_inline_details_preserve_media_hydration_and_safe_fallback(monkeypatch, mode, production):
    client = ReducedInlineHistoryClient(mode)
    _, sync, _, messages, service = make_service(monkeypatch, client, WorkerHistorySyncService if production else InstagramHistorySyncService)
    await service.process_next()
    assert client.detail_requests == 1
    if mode == "temporary_error":
        assert sync.status == "RETRY_PENDING"
        assert not messages.rows
    elif mode == "empty_denied":
        assert sync.status == "PARTIAL"
        assert sync.error_count == 1
        assert not messages.rows
    else:
        assert sync.status == "COMPLETED"
        assert len(messages.rows) == 1
        if mode == "hydrate_media":
            assert messages.rows[0].attachment_metadata["attachments"][0]["type"] == "image"
        else:
            assert messages.rows[0].text == "Скільки коштує?"


class MidPageLimitClient(FakeHistoryClient):
    def __init__(self):
        super().__init__()
        self.blocked = True
        self.requested_threads = []

    async def list_conversations(self, account_id, after=None, limit=10):
        return MetaConversationPage(conversations=[MetaConversationSummary(id="thread-1"), MetaConversationSummary(id="thread-2")])

    async def list_messages(self, conversation_id, after=None, limit=20):
        self.requested_threads.append(conversation_id)
        if conversation_id == "thread-2" and self.blocked:
            raise MetaInstagramError("META_HISTORY_RATE_LIMITED", "Application request limit reached.", 429)
        from dataclasses import replace
        details = await super().get_message("mid-" + conversation_id)
        details = replace(details, from_id="customer-" + conversation_id)
        return MetaMessagePage(messages=[MetaMessageSummary(id=details.id, details=details, details_complete=True)])


@pytest.mark.asyncio
@pytest.mark.parametrize("production", [False, True])
async def test_mid_page_throttle_resumes_without_skipping_conversations_or_duplicating_messages(monkeypatch, production):
    client = MidPageLimitClient()
    _, sync, _, messages, service = make_service(monkeypatch, client, WorkerHistorySyncService if production else InstagramHistorySyncService)
    sync.conversation_limit = 2
    sync.attempt_count = 9  # Successful pages must not make the first throttle wait 32 minutes.
    await service.process_next()
    assert sync.status == "RETRY_PENDING"
    assert sync.conversations_discovered == 0
    assert sync.conversations_synced == 0
    assert sync.conversation_pages_processed == 0
    assert sync.error_count == 0
    assert sync.rate_limit_count == 1
    assert sync.messages_imported == 1
    assert len(messages.rows) == 1
    delay = (sync.next_retry_at - datetime.now(UTC)).total_seconds()
    assert 110 < delay <= 120

    client.blocked = False
    await service.process_next()
    assert sync.status == "COMPLETED"
    assert sync.conversations_discovered == 2
    assert sync.conversations_synced == 2
    assert sync.conversation_pages_processed == 1
    assert sync.messages_imported == 2
    assert sync.messages_existing == 1
    assert sync.error_count == 0
    assert sync.rate_limit_count == 1
    assert len(messages.rows) == 2
    assert "thread-2" in client.requested_threads


@pytest.mark.asyncio
@pytest.mark.parametrize("production", [False, True])
async def test_replaying_a_throttled_page_keeps_permanent_errors_visible(monkeypatch, production):
    client = MidPageLimitClient()
    _, sync, _, messages, service = make_service(monkeypatch, client, WorkerHistorySyncService if production else InstagramHistorySyncService)
    sync.conversation_limit = 2
    def failed_lead(sync, *args):
        sync.error_count += 1
        sync.last_error_code = "DIRECT_LEAD_FAILED_SAFE"
    service._ensure_lead_safe = failed_lead
    await service.process_next()
    assert sync.status == "RETRY_PENDING"
    assert sync.error_count == 1
    assert len(messages.rows) == 1
    client.blocked = False
    await service.process_next()
    assert sync.status == "PARTIAL"
    assert sync.error_count == 2
    assert len(messages.rows) == 2


@pytest.mark.asyncio
async def test_history_cancel_stops_before_calling_meta(monkeypatch):
    client = FakeHistoryClient()
    _, sync, conversations, messages, service = make_service(monkeypatch, client)
    actor = uuid4()
    requested, status = service.cancel_sync(sync.workspace_id, actor)
    assert requested is True
    assert status == "CANCELLED"
    assert sync.status == "CANCELLED"
    assert sync.completed_at is not None
    assert len(conversations.rows) == 0 and len(messages.rows) == 0
    assert await service.process_next() is None


@pytest.mark.asyncio
async def test_history_cancel_while_locked_is_cooperative_and_preserves_records(monkeypatch):
    cancel_response = []

    class Client(FakeHistoryClient):
        async def list_conversations(self, account_id, after=None, limit=10):
            # Simulate a concurrent cancel API request *during* a provider call.
            # The history row is locked, but the independent cancellation record is not.
            service.syncs.worker_locked = True
            cancel_response.append(service.cancel_sync(sync.workspace_id, uuid4()))
            return await super().list_conversations(account_id, after, limit)

    client = Client()
    _, sync, conversations, messages, service = make_service(monkeypatch, client)
    result = await service.process_next()
    assert cancel_response == [(True, "STOPPING")]
    assert result is sync and sync.status == "CANCELLED"
    assert sync.next_retry_at is None
    assert not conversations.rows and not messages.rows


@pytest.mark.asyncio
async def test_history_cancel_does_not_affect_other_workspace(monkeypatch):
    client = FakeHistoryClient()
    _, sync, _, _, service = make_service(monkeypatch, client)
    foreign_workspace_id = uuid4()
    assert service.syncs.cancellation_requested(foreign_workspace_id, sync.id) is False
    assert service.status(foreign_workspace_id) is None


def test_history_cancel_signal_does_not_lock_active_sync_row_by_foreign_key():
    # A foreign key on sync_id would acquire KEY SHARE on the worker's
    # FOR UPDATE row and block the cancellation request itself.
    from app.models.instagram_inbox_sync import InstagramHistorySyncCancelRequest

    table = InstagramHistorySyncCancelRequest.__table__
    assert not table.c.sync_id.foreign_keys
    assert any(
        constraint.name == "uq_ig_history_cancel_workspace"
        for constraint in table.constraints
    )
