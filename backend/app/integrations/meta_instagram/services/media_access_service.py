"""Private attachment access in the integration service layer."""
from __future__ import annotations

from pathlib import Path
from uuid import UUID

from sqlalchemy.orm import Session

from app.integrations.meta_instagram.exceptions import MetaInstagramError
from app.integrations.meta_instagram.media import cache_media, cached_mime, private_media_path
from app.repositories.ai_direct_repository import DirectMessageRepository

ALLOWED_MEDIA_TYPES = {
    "image/jpeg", "image/png", "image/webp", "image/gif",
    "video/mp4", "video/webm", "audio/mpeg", "audio/mp4",
    "audio/ogg", "audio/webm", "application/pdf",
}


class InstagramMediaAccessService:
    def __init__(self, db: Session) -> None:
        self.messages = DirectMessageRepository(db)

    def resolve(self, workspace_id: UUID, message_id: UUID, index: int) -> tuple[Path, str]:
        message = self.messages.get_for_attachment(workspace_id, message_id)
        if not message:
            raise MetaInstagramError("DIRECT_MEDIA_NOT_FOUND", "Attachment not found.", 404)
        entries = (message.attachment_metadata or {}).get("attachments")
        if not isinstance(entries, list) or not (0 <= index < min(len(entries), 30)):
            raise MetaInstagramError("DIRECT_MEDIA_NOT_FOUND", "Attachment not found.", 404)
        attachment = entries[index]
        if not isinstance(attachment, dict):
            raise MetaInstagramError("DIRECT_MEDIA_NOT_FOUND", "Attachment not found.", 404)
        path = private_media_path(workspace_id, message_id, index)
        mime = cached_mime(message.attachment_metadata, index)
        if not path.is_file():
            url = attachment.get("source_url")
            if not url:
                raise MetaInstagramError("DIRECT_MEDIA_UNAVAILABLE", "Media no longer available.", 404)
            try:
                mime = cache_media(workspace_id, message_id, index, url)
            except (ValueError, OSError, RuntimeError):
                raise MetaInstagramError("DIRECT_MEDIA_UNAVAILABLE", "Media no longer available.", 404) from None
        if mime not in ALLOWED_MEDIA_TYPES:
            mime = "application/octet-stream"
        return path, mime
