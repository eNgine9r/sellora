"""Manual recovery of an Instagram post link omitted from a historical Direct message.

No provider calls or message rewrites. A manager deliberately associates a
verified public Instagram permalink to one existing workspace-scoped blank
message. This does NOT identify the purchased SKU or create an order.
"""
from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.integrations.meta_instagram.media import normalize_instagram_post_url
from app.models.ai_direct import DirectConversation, DirectMessage
from app.repositories.audit_log_repository import AuditLogRepository


class InstagramPostLinkError(ValueError):
    def __init__(self, code: str, status_code: int = 400) -> None:
        self.code = code
        self.status_code = status_code
        super().__init__(code)


class InstagramPostLinkService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def link(self, workspace_id: UUID, message_id: UUID, actor_id: UUID, url: str) -> DirectMessage:
        link = normalize_instagram_post_url(url)
        if not link:
            raise InstagramPostLinkError("INVALID_INSTAGRAM_POST_URL")
        message = self.db.execute(
            select(DirectMessage)
            .join(DirectConversation, DirectMessage.conversation_id == DirectConversation.id)
            .where(
                DirectMessage.id == message_id,
                DirectMessage.workspace_id == workspace_id,
                DirectMessage.deleted_at.is_(None),
                DirectConversation.workspace_id == workspace_id,
                DirectConversation.deleted_at.is_(None),
                DirectConversation.channel == "INSTAGRAM",
            )
            .with_for_update(of=DirectMessage)
        ).scalar_one_or_none()
        if not message:
            raise InstagramPostLinkError("DIRECT_MESSAGE_NOT_FOUND", 404)
        if message.provider != "INSTAGRAM" or (message.text or "").strip():
            raise InstagramPostLinkError("DIRECT_POST_LINK_NOT_ALLOWED", 409)
        existing = (message.attachment_metadata or {}).get("attachments") or []
        if existing:
            if len(existing) == 1 and existing[0].get("post_url") == link:
                return message  # retry idempotency
            raise InstagramPostLinkError("DIRECT_MESSAGE_ALREADY_HAS_ATTACHMENT", 409)
        kind = "reel" if "/reel/" in link else "ig_post"
        metadata = dict(message.attachment_metadata or {})
        metadata["attachments"] = [{"type": kind, "post_url": link, "source": "MANUAL"}]
        metadata["instagram_post_manual_linked_at"] = datetime.now(UTC).isoformat()
        message.attachment_metadata = metadata
        AuditLogRepository(self.db).create(
            workspace_id=workspace_id,
            user_id=actor_id,
            entity_type="DirectMessage",
            entity_id=message.id,
            action="DIRECT_INSTAGRAM_POST_LINKED",
            new_value={"type": kind, "source": "MANUAL"},
        )
        return message
