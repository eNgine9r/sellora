from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID
import hashlib

from app.integrations.meta_instagram.exceptions import MetaInstagramError
from app.integrations.meta_instagram.history_client import MetaConversationSummary, MetaInstagramHistoryClient, MetaMessageDetails
from app.integrations.meta_instagram.services.history_sync_service import InstagramHistorySyncService
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


class InstagramHistorySyncVisibilityService(InstagramHistorySyncService):
    """History sync with truthful provider-thread to CRM-dialog accounting.

    A Meta conversation is counted as synchronized only when it is durably linked
    to a Sellora DirectConversation. Provider threads whose message details are no
    longer available remain discovered but are not falsely reported as visible CRM
    dialogs.
    """

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
            self._fail_safe(
                sync,
                "META_CONNECTION_NOT_READY",
                "Instagram connection is not ready for history sync.",
            )
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

        client = self._client(self._decrypt(connection.access_token_ciphertext))
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
                    materialized = await self._sync_conversation(
                        sync,
                        connection,
                        client,
                        summary,
                    )
                    if materialized:
                        sync.conversations_synced += 1
                except MetaInstagramError as exc:
                    if exc.code in {
                        "META_HISTORY_RATE_LIMITED",
                        "META_HISTORY_PROVIDER_UNAVAILABLE",
                    }:
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
            if exc.code in {
                "META_HISTORY_RATE_LIMITED",
                "META_HISTORY_PROVIDER_UNAVAILABLE",
            }:
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
    ) -> bool:
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
        thread_linked = bool(conversation)

        for message_summary in reversed(page.messages):
            existing = self.messages.get_by_provider_message(
                sync.workspace_id,
                "INSTAGRAM",
                message_summary.id,
            )
            if existing:
                sync.messages_existing += 1
                if conversation is None:
                    candidate = self.conversations.get(
                        sync.workspace_id,
                        existing.conversation_id,
                    )
                    if candidate and self._link_thread(candidate, summary.id):
                        conversation = candidate
                        thread_linked = True
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
                candidate = self.conversations.get_by_instagram_participant(
                    sync.workspace_id,
                    connection.id,
                    participant_id,
                )
                if candidate and self._link_thread(candidate, summary.id):
                    conversation = candidate
                    thread_linked = True

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
                thread_linked = True
            else:
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
                "external_thread_id": summary.id,
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

        if conversation and thread_linked:
            conversation.provider_sync_status = "HISTORY_SYNCED"
            self._enrich_profile_safe(sync.workspace_id, conversation)
        return bool(conversation and thread_linked)

    def _link_thread(self, conversation: DirectConversation, thread_id: str) -> bool:
        current = conversation.external_thread_id or conversation.external_conversation_id
        if current and current != thread_id:
            return False
        conversation.external_thread_id = thread_id
        conversation.external_conversation_id = thread_id
        return True

    def _decrypt(self, ciphertext: str) -> str:
        # Kept as a seam for focused tests while production delegates to the
        # same encrypted-token implementation as the original service.
        from app.integrations.meta_instagram.crypto import decrypt_instagram_token

        return decrypt_instagram_token(ciphertext)
