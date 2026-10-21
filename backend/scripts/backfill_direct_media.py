"""Recover missing Direct attachment metadata from saved verified Meta events.

Dry-run by default. Does not create messages, change customers/orders, or
download media. Apply requires explicit workspace ID and --apply.
"""
from __future__ import annotations

import argparse
from collections import Counter
from uuid import UUID

from sqlalchemy import select, text

from app.database.session import SessionLocal
from app.integrations.meta_instagram.media import normalize_attachments
from app.models.ai_direct import DirectMessage
from app.models.meta_instagram import MetaWebhookEvent


def recover(workspace_id: UUID, *, apply: bool, limit: int = 3000) -> dict[str, int]:
    counters: Counter[str] = Counter()
    with SessionLocal() as db:
        if not apply:
            db.execute(text("SET TRANSACTION READ ONLY"))
        events = db.scalars(
            select(MetaWebhookEvent).where(
                MetaWebhookEvent.workspace_id == workspace_id,
                MetaWebhookEvent.status == "PROCESSED",
            ).order_by(MetaWebhookEvent.created_at.asc()).limit(limit)
        ).all()
        by_mid: dict[str, list[dict[str, str]]] = {}
        for event in events:
            payload = event.payload if isinstance(event.payload, dict) else {}
            for entry in payload.get("entry", []) or []:
                for item in entry.get("messaging", []) or []:
                    msg = item.get("message") or {}
                    mid = msg.get("mid")
                    attachments = normalize_attachments(msg)
                    if mid and attachments:
                        by_mid[str(mid)] = attachments
        counters["webhook_events"] = len(events)
        counters["messages_with_attachments"] = len(by_mid)
        if by_mid:
            rows = db.scalars(
                select(DirectMessage).where(
                    DirectMessage.workspace_id == workspace_id,
                    DirectMessage.provider == "INSTAGRAM",
                    DirectMessage.provider_message_id.in_(tuple(by_mid)),
                    DirectMessage.deleted_at.is_(None),
                )
            ).all()
            for message in rows:
                attachments = by_mid.get(message.provider_message_id)
                if not attachments:
                    continue
                metadata = dict(message.attachment_metadata or {})
                if metadata.get("attachments"):
                    counters["already_recovered"] += 1
                    continue
                counters["recoverable"] += 1
                counters["attachments_recoverable"] += len(attachments)
                if apply:
                    metadata["attachments"] = attachments
                    metadata["recovered_from_webhook"] = True
                    message.attachment_metadata = metadata
                    if message.message_payload_type == "UNSUPPORTED":
                        message.message_payload_type = attachments[0]["type"].upper()
                    counters["updated"] += 1
        if apply:
            db.commit()
        else:
            db.rollback()
    return dict(counters)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace-id", type=UUID, required=True)
    parser.add_argument("--limit", type=int, default=3000)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    if args.limit < 1 or args.limit > 20000:
        parser.error("limit must be between 1 and 20000")
    # Summary only. Never emit a Meta URL, message body, or provider ID.
    print({"mode": "apply" if args.apply else "dry-run",
           "counts": recover(args.workspace_id, apply=args.apply, limit=args.limit)})


if __name__ == "__main__":
    main()
