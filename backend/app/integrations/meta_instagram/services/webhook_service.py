from datetime import UTC, date, datetime
from typing import Any
import hashlib
import hmac
import json

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.integrations.meta_instagram.exceptions import MetaInstagramError
from app.integrations.meta_instagram.repositories.connection_repository import InstagramConnectionRepository
from app.integrations.meta_instagram.repositories.webhook_event_repository import MetaWebhookEventRepository
from app.models.meta_instagram import MetaWebhookEvent, MetaWebhookEventStatus


class InstagramWebhookService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = MetaWebhookEventRepository(db)

    def verify_challenge(self, mode: str | None, verify_token: str | None, challenge: str | None) -> str:
        expected = get_settings().meta_webhook_verify_token
        if mode != "subscribe" or not expected or not verify_token or not hmac.compare_digest(expected, verify_token):
            raise MetaInstagramError("META_WEBHOOK_VERIFY_FAILED", "Webhook verification failed.", 403)
        return challenge or ""

    def validate_signature(self, body: bytes, signature: str | None) -> None:
        secret = get_settings().meta_app_secret
        if not secret or not signature or not signature.startswith("sha256="):
            raise MetaInstagramError("META_WEBHOOK_SIGNATURE_INVALID", "Webhook signature invalid.", 403)
        digest = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(f"sha256={digest}", signature):
            raise MetaInstagramError("META_WEBHOOK_SIGNATURE_INVALID", "Webhook signature invalid.", 403)

    def persist_verified_events(self, body: bytes, payload: dict[str, Any]) -> list[MetaWebhookEvent]:
        """Route each signed Meta messaging item to its own workspace.

        The signature is validated over the original HTTP body before this method.
        Keeping one provider event per item means a batch containing several
        messages or different IG accounts cannot be silently deduplicated by
        the first message ID or written into the first account's workspace.
        """
        entries = payload.get("entry") or []
        if not isinstance(entries, list):
            raise MetaInstagramError("META_WEBHOOK_PAYLOAD_INVALID", "Webhook payload invalid.", 400)
        parts: list[dict[str, Any]] = []
        for entry in entries:
            if not isinstance(entry, dict):
                raise MetaInstagramError("META_WEBHOOK_PAYLOAD_INVALID", "Webhook payload invalid.", 400)
            items = entry.get("messaging") or []
            if not isinstance(items, list):
                raise MetaInstagramError("META_WEBHOOK_PAYLOAD_INVALID", "Webhook payload invalid.", 400)
            for item in items:
                if not isinstance(item, dict):
                    raise MetaInstagramError("META_WEBHOOK_PAYLOAD_INVALID", "Webhook payload invalid.", 400)
                parts.append({
                    "object": payload.get("object"),
                    "entry": [{ "id": entry.get("id"), "time": entry.get("time"), "messaging": [item]}],
                })
        if not parts or (len(parts) == 1 and len(entries) == 1):
            # Preserve the legacy exact-body digest and event identity for
            # singleton events. Even one message in a multi-entry envelope
            # must be split: an earlier empty entry can belong to another shop.
            return [self.persist_verified_event(body, payload)]
        if len(parts) > 100:
            raise MetaInstagramError("META_WEBHOOK_PAYLOAD_INVALID", "Webhook batch too large.", 413)
        events: list[MetaWebhookEvent] = []
        for part in parts:
            canonical = json.dumps(part, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()
            events.append(self.persist_verified_event(canonical, part))
        return events

    def persist_verified_event(self, body: bytes, payload: dict[str, Any]) -> MetaWebhookEvent:
        payload_hash = hashlib.sha256(body).hexdigest()
        legacy_event_id = self._event_id(payload)
        account_id = self._account_id(payload)
        # A message ID alone must not deduplicate another business account's
        # event. Hash the target account, never store its raw ID in the key.
        event_external_id = (
            f"{legacy_event_id[:160]}:{hashlib.sha256(account_id.encode()).hexdigest()[:16]}"
            if legacy_event_id and account_id else legacy_event_id
        )
        bucket = date.today()
        duplicate = self.repo.get_duplicate("INSTAGRAM", event_external_id, payload_hash, bucket)
        if duplicate:
            return duplicate
        if event_external_id != legacy_event_id and legacy_event_id:
            # Preserve replay idempotency for pre-migration events, but do not
            # deduplicate an ignored event that becomes valid after linking IG.
            old = self.repo.get_duplicate("INSTAGRAM", legacy_event_id, payload_hash, bucket)
            if (
                old is not None
                and old.status not in (MetaWebhookEventStatus.IGNORED.value, MetaWebhookEventStatus.FAILED_SAFE.value)
                and self._account_id(old.payload) == account_id
            ):
                return old

        now = datetime.now(UTC)
        connection = InstagramConnectionRepository(self.db).get_by_account(account_id) if account_id else None
        status = MetaWebhookEventStatus.VERIFIED.value if connection else MetaWebhookEventStatus.IGNORED.value
        error_code = None if connection else "META_CONNECTION_NOT_READY"
        error_message = None if connection else "No unique connected Sellora workspace matches the Instagram account."
        processed_at = None if connection else now

        if connection:
            connection.last_webhook_at = now
            connection.updated_at = now

        event = MetaWebhookEvent(
            provider="INSTAGRAM",
            workspace_id=getattr(connection, "workspace_id", None),
            instagram_connection_id=getattr(connection, "id", None),
            event_external_id=event_external_id,
            object_type=str(payload.get("object", "instagram")),
            event_type=self._event_type(payload),
            event_date_bucket=bucket,
            payload_hash=payload_hash,
            payload=payload,
            signature_verified=True,
            status=status,
            received_at=now,
            processed_at=processed_at,
            safe_error_code=error_code,
            safe_error_message=error_message,
            created_at=now,
            updated_at=now,
        )
        return self.repo.create(event)

    def parse_body(self, body: bytes) -> dict[str, Any]:
        if len(body) > get_settings().meta_webhook_max_body_bytes:
            raise MetaInstagramError("META_WEBHOOK_PAYLOAD_INVALID", "Webhook payload too large.", 413)
        try:
            payload = json.loads(body.decode("utf-8"))
        except Exception as exc:
            raise MetaInstagramError("META_WEBHOOK_PAYLOAD_INVALID", "Webhook payload invalid.", 400) from exc
        if not isinstance(payload, dict):
            raise MetaInstagramError("META_WEBHOOK_PAYLOAD_INVALID", "Webhook payload invalid.", 400)
        return payload

    def _event_id(self, payload: dict[str, Any]) -> str | None:
        for entry in payload.get("entry", []) or []:
            for item in entry.get("messaging", []) or []:
                timestamp = str(item.get("timestamp") or entry.get("time") or "")
                message = item.get("message") or {}
                postback = item.get("postback") or {}
                read = item.get("read") or {}
                reaction = item.get("reaction") or {}
                message_edit = item.get("message_edit") or {}
                if message.get("mid"):
                    return f"messages:{message.get('mid')}"
                if postback.get("mid"):
                    return f"messaging_postbacks:{postback.get('mid')}"
                if read.get("mid"):
                    return f"messaging_seen:{read.get('mid')}:{timestamp}"[:180]
                if reaction.get("mid"):
                    return f"message_reactions:{reaction.get('mid')}:{reaction.get('action')}:{timestamp}"[:180]
                if message_edit.get("mid"):
                    return f"message_edit:{message_edit.get('mid')}:{message_edit.get('num_edit')}:{timestamp}"[:180]
        return None

    def _account_id(self, payload: dict[str, Any]) -> str | None:
        for entry in payload.get("entry", []) or []:
            if entry.get("id"):
                return str(entry.get("id"))
        return None

    def _event_type(self, payload: dict[str, Any]) -> str:
        items = [
            item
            for entry in payload.get("entry", []) or []
            for item in entry.get("messaging", []) or []
            if isinstance(item, dict)
        ]
        if any(item.get("read") for item in items):
            return "messaging_seen"
        if any(item.get("reaction") for item in items):
            return "message_reactions"
        if any(item.get("message_edit") for item in items):
            return "message_edit"
        if any(item.get("postback") for item in items):
            return "messaging_postbacks"
        if any(item.get("message") for item in items):
            return "messages"
        return "unsupported"