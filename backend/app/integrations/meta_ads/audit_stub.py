from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID

from app.integrations.meta_ads.token_safety import assert_no_raw_token_in_response, redact_secret_fields

META_ADS_MOCK_AUDIT_EVENTS = {
    "meta_ads_mock_connect_started",
    "meta_ads_mock_connect_callback_validated",
    "meta_ads_mock_connect_denied",
    "meta_ads_mock_disconnected",
    "meta_ads_mock_status_viewed",
}


@dataclass(frozen=True)
class MetaAdsMockAuditEventDTO:
    """Non-persistent audit event preview for the mock Meta Ads API boundary."""

    event: str
    provider: str
    workspace_id: UUID
    user_id: UUID | None
    outcome: str
    connection_mode: str = "mock"
    persisted: bool = False
    payload: dict[str, object] = field(default_factory=dict)


def build_meta_ads_mock_audit_event(
    *,
    event: str,
    workspace_id: UUID,
    user_id: UUID | None,
    outcome: str,
    payload: dict[str, object] | None = None,
) -> MetaAdsMockAuditEventDTO:
    """Build a safe, redacted, non-persistent audit event stub.

    The Sprint 4.13 mock API boundary intentionally does not write audit rows to
    the database. This DTO documents the event that a future persistent audit
    implementation should record while preventing token-like or secret fields
    from being returned or logged.
    """

    if event not in META_ADS_MOCK_AUDIT_EVENTS:
        raise ValueError("Unsupported Meta Ads mock audit event.")
    event_stub = MetaAdsMockAuditEventDTO(
        event=event,
        provider="meta_ads",
        workspace_id=workspace_id,
        user_id=user_id,
        outcome=outcome,
        payload=redact_secret_fields(payload or {}),
    )
    assert_no_raw_token_in_response(event_stub)
    return event_stub
