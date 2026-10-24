"""Bounded private media caching, executed separately from webhook transactions."""
from __future__ import annotations

from sqlalchemy import select

from app.database.session import SessionLocal
from app.integrations.meta_instagram.media import cache_media
from app.models.ai_direct import DirectMessage


def cache_pending_media_batch(limit: int = 5) -> dict[str, int]:
    counts = {"messages": 0, "cached": 0, "unavailable": 0}
    with SessionLocal() as db:
        messages = db.scalars(
            select(DirectMessage).where(
                DirectMessage.provider == "INSTAGRAM",
                DirectMessage.deleted_at.is_(None),
                DirectMessage.attachment_metadata.op("?")("attachments"),
                ~DirectMessage.attachment_metadata.op("?")("media_cache_processed"),
            ).order_by(DirectMessage.received_at.desc()).limit(max(1, min(limit, 10)))
        ).all()
        for message in messages:
            metadata = dict(message.attachment_metadata or {})
            records = metadata.get("attachments")
            if not isinstance(records, list):
                continue
            records = [dict(entry) if isinstance(entry, dict) else {} for entry in records[:30]]
            counts["messages"] += 1
            for index, attachment in enumerate(records):
                if attachment.get("cached") or not attachment.get("source_url"):
                    continue
                try:
                    mime = cache_media(message.workspace_id, message.id, index, attachment["source_url"])
                    attachment["cached"] = True
                    if mime != "cached":
                        attachment["mime_type"] = mime
                    counts["cached"] += 1
                except (ValueError, OSError, RuntimeError):
                    # Never log a URL, attachment, or screenshot. View-on-demand can retry.
                    counts["unavailable"] += 1
            metadata["attachments"] = records
            metadata["media_cache_processed"] = True
            message.attachment_metadata = metadata
        db.commit()
    return counts
