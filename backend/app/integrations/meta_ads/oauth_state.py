from __future__ import annotations

import base64
import hmac
import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from uuid import UUID, uuid4

MOCK_OAUTH_STATE_PURPOSE = "meta_ads_mock_oauth"
_STATE_SIGNING_KEY = b"sellora-meta-ads-mock-oauth-state-v1"


class MetaOAuthStateError(ValueError):
    """Raised when mock OAuth state is invalid, expired, or mismatched."""


@dataclass(frozen=True)
class MetaOAuthMockStatePayload:
    workspace_id: UUID
    user_id: UUID
    nonce: str
    issued_at: datetime
    expires_at: datetime
    purpose: str = MOCK_OAUTH_STATE_PURPOSE

    def to_safe_dict(self) -> dict[str, str]:
        return {
            "workspace_id": str(self.workspace_id),
            "user_id": str(self.user_id),
            "nonce": self.nonce,
            "issued_at": self.issued_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
            "purpose": self.purpose,
        }


def _b64encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _b64decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode((value + padding).encode("ascii"))


def _sign(payload: str) -> str:
    return _b64encode(hmac.new(_STATE_SIGNING_KEY, payload.encode("ascii"), sha256).digest())


def generate_mock_oauth_state(workspace_id: UUID, user_id: UUID, now: datetime | None = None, ttl_minutes: int = 10) -> tuple[str, MetaOAuthMockStatePayload]:
    issued_at = now or datetime.now(UTC)
    if issued_at.tzinfo is None:
        issued_at = issued_at.replace(tzinfo=UTC)
    payload = MetaOAuthMockStatePayload(
        workspace_id=workspace_id,
        user_id=user_id,
        nonce=uuid4().hex,
        issued_at=issued_at,
        expires_at=issued_at + timedelta(minutes=ttl_minutes),
    )
    encoded_payload = _b64encode(json.dumps(payload.to_safe_dict(), sort_keys=True, separators=(",", ":")).encode("utf-8"))
    return f"{encoded_payload}.{_sign(encoded_payload)}", payload


def decode_mock_oauth_state(state: str) -> MetaOAuthMockStatePayload:
    try:
        encoded_payload, signature = state.split(".", 1)
    except ValueError as exc:
        raise MetaOAuthStateError("Invalid mock OAuth state format.") from exc
    if not hmac.compare_digest(_sign(encoded_payload), signature):
        raise MetaOAuthStateError("Invalid mock OAuth state signature.")
    try:
        data = json.loads(_b64decode(encoded_payload).decode("utf-8"))
        return MetaOAuthMockStatePayload(
            workspace_id=UUID(data["workspace_id"]),
            user_id=UUID(data["user_id"]),
            nonce=str(data["nonce"]),
            issued_at=datetime.fromisoformat(data["issued_at"]),
            expires_at=datetime.fromisoformat(data["expires_at"]),
            purpose=str(data["purpose"]),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise MetaOAuthStateError("Invalid mock OAuth state payload.") from exc


def validate_mock_oauth_state(state: str, workspace_id: UUID, user_id: UUID, now: datetime | None = None) -> MetaOAuthMockStatePayload:
    payload = decode_mock_oauth_state(state)
    checked_at = now or datetime.now(UTC)
    if checked_at.tzinfo is None:
        checked_at = checked_at.replace(tzinfo=UTC)
    if payload.purpose != MOCK_OAUTH_STATE_PURPOSE:
        raise MetaOAuthStateError("Invalid mock OAuth state purpose.")
    if payload.expires_at <= checked_at:
        raise MetaOAuthStateError("Mock OAuth state has expired.")
    if payload.workspace_id != workspace_id:
        raise MetaOAuthStateError("Mock OAuth state workspace mismatch.")
    if payload.user_id != user_id:
        raise MetaOAuthStateError("Mock OAuth state user mismatch.")
    return payload
