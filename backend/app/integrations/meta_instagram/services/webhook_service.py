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

    def persist_verified_event(self, body: bytes, payload: dict[str, Any]) -> MetaWebhookEvent:
        payload_hash = hashlib.sha256(body).hexdigest()
        event_external_id = self._event_id(payload)
        bucket = date.today()
        duplicate = self.repo.get_duplicate("INSTAGRAM", event_external_id, payload_hash, bucket)
        if duplicate:
            return duplicate

        now = datetime.now(UTC)
        account_id = self._account_id(payload)
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