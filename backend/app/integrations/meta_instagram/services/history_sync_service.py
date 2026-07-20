from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID
import hashlib

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.integrations.meta_instagram.crypto import decrypt_instagram_token
from app.integrations.meta_instagram.exceptions import MetaInstagramError
from app.integrations.meta_instagram.history_client import (
    MetaConversationSummary,
    MetaInstagramHistoryClient,
    MetaMessageDetails,
)
from app.integrations.meta_instagram.repositories.connection_repository import InstagramConnectionRepository
from app.integrations.meta_instagram.repositories.inbox_sync_repository import InstagramHistorySyncRepository
from app.integrations.meta_instagram.services.participant_profile_service import InstagramParticipantProfileService
from app.models.ai_direct import (
    DirectChannel,
    DirectConversation,
    DirectMessage,
    DirectMessageDirection,
    DirectMessageSenderType,
    DirectMessageType,
)
from app.models.instagram_inbox_sync import InstagramHistorySync, InstagramHistorySyncStatus
from app.models.meta_instagram import InstagramConnectionStatus
from app.repositories.ai_direct_repository import DirectConversationRepository, DirectMessageRepository


ACTIVE_SYNC_STATUSES = {
    InstagramHistorySyncStatus.PENDING.value,
    InstagramHistorySyncStatus.RUNNING.value,
    InstagramHistorySyncStatus.RETRY_PENDING.value,
}


class InstagramHistorySyncService:
    def __init__(self, db: Session, client_factory=None) -> None:
        self.db = db
        self.connections = InstagramConnectionRepository(db)
        self.syncs = InstagramHistorySyncRepository(db)
        self.conversations = DirectConversationRepository(db)
        self.messages = DirectMessageRepository(db)
        self.profile_service = InstagramParticipantProfileService(db)
        self.client_factory = client_factory

    def request_sync(
        self,
        workspace_id: UUID,
        user_id: UUID,
        *,
        conversation_limit: int = 100,
        messages_per_conversation: int = 20,
    ) -> InstagramHistorySync:
        connection = self.connections.get_active(workspace_id)
        if (
            not connection
            or connection.status != InstagramConnectionStatus.CONNECTED.value
            or not connection.instagram_account_id
            or not connection.access_token_ciphertext
        ):
            raise MetaInstagramError(
                "META_CONNECTION_NOT_READY",
                "Connect Instagram before synchronizing message history.",
                409,
            )

        sync = self.syncs.get_for_update(workspace_id)
        if sync and sync.status in ACTIVE_SYNC_STATUSES:
            return sync
        if not sync:
            sync = self.syncs.create(
                InstagramHistorySync(
                    workspace_id=workspace_id,
                    instagram_connection_id=connection.id,
                )
            )
        sync.instagram_connection_id = connection.id
        sync.requested_by = user_id
        sync.status = InstagramHistorySyncStatus.PENDING.value
        sync.conversation_cursor = None
        sync.conversation_limit = max(1, min(conversation_limit, 500))
        sync.messages_per_conversation = max(1, min(messages_per_conversation, 20))
        sync.conversation_pages_processed = 0
        sync.conversations_discovered = 0
        sync.conversations_synced = 0
        sync.messages_discovered = 0
        sync.messages_imported = 0
        sync.messages_existing = 0
        sync.messages_unavailable = 0
        sync.error_count = 0
        sync.rate_limit_count = 0
        sync.attempt_count = 0
        sync.last_error_code = None
        sync.last_error_message = None
        sync.next_retry_at = None
        sync.started_at = None
        sync.completed_at = None
        return sync

    def status(self, workspace_id: UUID) -> InstagramHistorySync | None:
        return self.syncs.get(workspace_id)

    async def process_next(self) -> InstagramHistorySync | None:
        sync = self.syncs.next_pending_for_update()
        if not sync:
            return None
        connection = self.connections.get_active(sync.workspace_id)
        if (
            not connection
            or connection.id != sync.instagram_connection_id
            or connection.status != InstagramConnectionStatus.CONNECTED.value
            or not connection.instagram_account_id
            or not connection.access_token_ciphertext
        ):
            self._fail_safe(sync, "META_CONNECTION_NOT_READY", "Instagram connection is not ready for history sync.")
            return sync

        now = datetime.now(UTC)
        sync.status = InstagramHistorySyncStatus.RUNNING.value
        sync.started_at = sync.started_at or now
        sync.attempt_count = (sync.attempt_count or 0) + 1
        sync.next_retry_at = None
        sync.last_error_code = None
        sync.last_error_message = None

        remaining = sync.conversation_limit - sync.conversations_discovered
        if remaining <= 0:
            self._complete(sync)
            return sync

        client = self._client(decrypt_instagram_token(connection.access_token_ciphertext))
        try:
            page = await client.list_conversations(
                connection.instagram_account_id,
                after=sync.conversation_cursor,
                limit=min(10, remaining),
            )
            summaries = page.conversations[:remaining]
            sync.conversation_pages_processed += 1
            sync.conversations_discovered += len(summaries)
            for summary in summaries:
                try:
                    await self._sync_conversation(sync, connection, client, summary)
                    sync.conversations_synced += 1
                except MetaInstagramError as exc:
                    if exc.code in {"META_HISTORY_RATE_LIMITED", "META_HISTORY_PROVIDER_UNAVAILABLE"}:
                        self._schedule_retry(sync, exc)
                        return sync
                    sync.error_count += 1
                    sync.last_error_code = exc.code
                    sync.last_error_message = exc.message[:300]
                except Exception as exc:
                    sync.error_count += 1
                    sync.last_error_code = "META_HISTORY_CONVERSATION_FAILED"
                    sync.last_error_message = exc.__class__.__name__

            reached_limit = sync.conversations_discovered >= sync.conversation_limit
            sync.conversation_cursor = None if reached_limit else page.after_cursor
            if reached_limit or not page.after_cursor:
                self._complete(sync)
            else:
                sync.status = InstagramHistorySyncStatus.PENDING.value
            return sync
        except MetaInstagramError as exc:
            if exc.code in {"META_HISTORY_RATE_LIMITED", "META_HISTORY_PROVIDER_UNAVAILABLE"}:
                self._schedule_retry(sync, exc)
            else:
                self._fail_safe(sync, exc.code, exc.message)
            return sync

    async def _sync_conversation(
        self,
        sync: InstagramHistorySync,
        connection,
        client: MetaInstagramHistoryClient,
        summary: MetaConversationSummary,
    ) -> None:
        page = await client.list_messages(
            summary.id,
            limit=sync.messages_per_conversation,
        )
        sync.messages_discovered += len(page.messages)
        conversation: DirectConversation | None = self.conversations.get_by_external_thread(
            sync.workspace_id,
            connection.id,
            summary.id,
        )

        for message_summary in reversed(page.messages):
            existing = self.messages.get_by_provider_message(
                sync.workspace_id,
                "INSTAGRAM",
                message_summary.id,
            )
            if existing:
                sync.messages_existing += 1
                if conversation is None:
                    conversation = self.conversations.get(sync.workspace_id, existing.conversation_id)
                continue
            try:
                details = await client.get_message(message_summary.id)
            except MetaInstagramError as exc:
                if exc.code == "META_HISTORY_MESSAGE_UNAVAILABLE":
                    sync.messages_unavailable += 1
                    continue
                raise

            direction, participant_id, participant_username = self._identity(
                connection.instagram_account_id,
                details,
            )
            if not participant_id:
                sync.messages_unavailable += 1
                continue
            if conversation is None:
                conversation = self.conversations.get_by_instagram_participant(
                    sync.workspace_id,
                    connection.id,
                    participant_id,
                )
            if conversation is None:
                conversation = self.conversations.create(
                    DirectConversation(
                        workspace_id=sync.workspace_id,
                        channel=DirectChannel.INSTAGRAM.value,
                        instagram_connection_id=connection.id,
                        external_conversation_id=summary.id,
                        external_thread_id=summary.id,
                        participant_external_id=participant_id,
                        participant_scoped_id=participant_id,
                        participant_username=participant_username,
                        participant_display_name=participant_username or "Instagram customer",
                        unread_count=0,
                        provider_sync_status="HISTORY_SYNCING",
                    )
                )
            else:
                conversation.external_conversation_id = summary.id
                conversation.external_thread_id = summary.id
                conversation.participant_scoped_id = conversation.participant_scoped_id or participant_id
                conversation.participant_external_id = conversation.participant_external_id or participant_id
                if participant_username and not conversation.participant_username:
                    conversation.participant_username = participant_username
                    if conversation.participant_display_name in {None, "Instagram customer"}:
                        conversation.participant_display_name = participant_username

            created_at = self._parse_time(details.created_time or message_summary.created_time)
            text = details.message
            message_type = DirectMessageType.TEXT.value
            payload_type = "TEXT"
            if details.is_unsupported or text is None:
                payload_type = "UNSUPPORTED"
                message_type = DirectMessageType.SYSTEM_EVENT.value
                text = "[Unsupported historical Instagram message]"
            metadata = {
                "history_imported": True,
                "is_unsupported": details.is_unsupported,
            }
            if details.reply_to_mid:
                metadata["reply_to_mid"] = details.reply_to_mid
            self.messages.create(
                DirectMessage(
                    workspace_id=sync.workspace_id,
                    conversation_id=conversation.id,
                    external_message_id=details.id,
                    direction=direction,
                    sender_type=(
                        DirectMessageSenderType.MANAGER.value
                        if direction == DirectMessageDirection.OUTBOUND.value
                        else DirectMessageSenderType.CUSTOMER.value
                    ),
                    message_type=message_type,
                    text=text,
                    safe_text_hash=hashlib.sha256((text or details.id).encode()).hexdigest(),
                    received_at=created_at,
                    sent_at=created_at if direction == DirectMessageDirection.OUTBOUND.value else None,
                    processing_status="RECEIVED",
                    is_synthetic=False,
                    provider="INSTAGRAM",
                    provider_message_id=details.id,
                    delivery_status=(
                        "PROVIDER_ACCEPTED"
                        if direction == DirectMessageDirection.OUTBOUND.value
                        else "RECEIVED"
                    ),
                    message_payload_type=payload_type,
                    attachment_metadata=metadata,
                    provider_created_at=created_at,
                )
            )
            sync.messages_imported += 1
            self._advance_conversation(conversation, direction, created_at)

        if conversation:
            conversation.provider_sync_status = "HISTORY_SYNCED"
            self._enrich_profile_safe(sync.workspace_id, conversation)

    def _identity(
        self,
        account_id: str,
        details: MetaMessageDetails,
    ) -> tuple[str, str | None, str | None]:
        if details.from_id == account_id:
            participant = next(
                (item for item in details.to if str(item.get("id") or "") != account_id),
                details.to[0] if details.to else {},
            )
            return (
                DirectMessageDirection.OUTBOUND.value,
                str(participant.get("id")) if participant.get("id") else None,
                str(participant.get("username")) if participant.get("username") else None,
            )
        return (
            DirectMessageDirection.INBOUND.value,
            details.from_id,
            details.from_username,
        )

    def _advance_conversation(self, conversation, direction: str, created_at: datetime) -> None:
        if not conversation.last_message_at or created_at > conversation.last_message_at:
            conversation.last_message_at = created_at
        if direction == DirectMessageDirection.INBOUND.value:
            if not conversation.last_inbound_message_at or created_at > conversation.last_inbound_message_at:
                conversation.last_inbound_message_at = created_at
            if created_at + timedelta(hours=24) > datetime.now(UTC):
                conversation.messaging_window_expires_at = created_at + timedelta(hours=24)
                conversation.human_agent_window_expires_at = created_at + timedelta(days=7)
        elif not conversation.last_outbound_message_at or created_at > conversation.last_outbound_message_at:
            conversation.last_outbound_message_at = created_at

    def _enrich_profile_safe(self, workspace_id: UUID, conversation: DirectConversation) -> None:
        try:
            profile = self.profile_service.enrich_if_due(workspace_id, conversation.id)
            if profile:
                conversation.provider_sync_status = f"HISTORY_SYNCED_PROFILE_{profile.status}"
        except Exception:
            conversation.provider_sync_status = "HISTORY_SYNCED_PROFILE_FAILED_SAFE"

    def _client(self, access_token: str) -> MetaInstagramHistoryClient:
        if self.client_factory:
            return self.client_factory(access_token)
        settings = get_settings()
        return MetaInstagramHistoryClient(
            settings.meta_graph_api_base_url,
            settings.meta_graph_api_version,
            access_token,
        )

    def _schedule_retry(self, sync: InstagramHistorySync, exc: MetaInstagramError) -> None:
        sync.status = InstagramHistorySyncStatus.RETRY_PENDING.value
        sync.error_count += 1
        if exc.code == "META_HISTORY_RATE_LIMITED":
            sync.rate_limit_count += 1
        delay_minutes = min(60, 2 ** min(sync.attempt_count, 5))
        sync.next_retry_at = datetime.now(UTC) + timedelta(minutes=delay_minutes)
        sync.last_error_code = exc.code
        sync.last_error_message = exc.message[:300]

    def _fail_safe(self, sync: InstagramHistorySync, code: str, message: str) -> None:
        sync.status = InstagramHistorySyncStatus.FAILED_SAFE.value
        sync.error_count += 1
        sync.last_error_code = code
        sync.last_error_message = message[:300]
        sync.completed_at = datetime.now(UTC)

    def _complete(self, sync: InstagramHistorySync) -> None:
        now = datetime.now(UTC)
        sync.status = (
            InstagramHistorySyncStatus.PARTIAL.value
            if sync.error_count or sync.messages_unavailable
            else InstagramHistorySyncStatus.COMPLETED.value
        )
        sync.completed_at = now
        sync.last_synced_at = now
        sync.next_retry_at = None
        sync.conversation_cursor = None

    def _parse_time(self, value: str | None) -> datetime:
        if not value:
            return datetime.now(UTC)
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
        except ValueError:
            return datetime.now(UTC)
