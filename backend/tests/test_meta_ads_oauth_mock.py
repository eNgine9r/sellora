from __future__ import annotations

from datetime import UTC, datetime, timedelta
from urllib.parse import parse_qs, urlparse
from uuid import uuid4

import pytest

from app.integrations.meta_ads.oauth_mock import MOCK_META_OAUTH_AUTHORIZE_URL, MetaAdsMockOAuthPermissionError, MetaAdsMockOAuthService
from app.integrations.meta_ads.oauth_state import MetaOAuthStateError, decode_mock_oauth_state, generate_mock_oauth_state, validate_mock_oauth_state
from app.integrations.meta_ads.schemas import MetaOAuthMockCallbackInputDTO
from app.models.role import RoleName


def test_owner_can_start_mock_oauth_flow_with_mock_domain_only() -> None:
    service = MetaAdsMockOAuthService()
    workspace_id = uuid4()
    user_id = uuid4()

    result = service.start_mock_connect(workspace_id=workspace_id, user_id=user_id, role=RoleName.OWNER)

    assert result.workspace_id == workspace_id
    assert result.connection_mode == "mock"
    assert result.connected is False
    assert result.token_stored is False
    assert result.live_api_enabled is False
    assert result.authorization_url.startswith(MOCK_META_OAUTH_AUTHORIZE_URL)
    assert "facebook.com" not in result.authorization_url
    assert "graph.facebook.com" not in result.authorization_url


def test_manager_and_analyst_cannot_start_or_disconnect_mock_oauth_flow() -> None:
    service = MetaAdsMockOAuthService()
    workspace_id = uuid4()
    user_id = uuid4()

    for role in (RoleName.MANAGER, RoleName.ANALYST):
        with pytest.raises(MetaAdsMockOAuthPermissionError):
            service.start_mock_connect(workspace_id=workspace_id, user_id=user_id, role=role)
        with pytest.raises(MetaAdsMockOAuthPermissionError):
            service.simulate_disconnect(workspace_id=workspace_id, role=role)


def test_state_contains_workspace_user_context_and_no_token() -> None:
    workspace_id = uuid4()
    user_id = uuid4()

    state, payload = generate_mock_oauth_state(workspace_id=workspace_id, user_id=user_id)
    decoded = decode_mock_oauth_state(state)

    assert decoded.workspace_id == workspace_id == payload.workspace_id
    assert decoded.user_id == user_id == payload.user_id
    assert decoded.purpose == "meta_ads_mock_oauth"
    assert decoded.nonce
    assert "token" not in state.lower()


def test_invalid_expired_and_mismatched_state_are_rejected() -> None:
    workspace_id = uuid4()
    user_id = uuid4()
    now = datetime(2026, 7, 2, 12, 0, tzinfo=UTC)
    state, _ = generate_mock_oauth_state(workspace_id=workspace_id, user_id=user_id, now=now, ttl_minutes=1)

    with pytest.raises(MetaOAuthStateError):
        validate_mock_oauth_state("not-a-valid-state", workspace_id=workspace_id, user_id=user_id, now=now)
    with pytest.raises(MetaOAuthStateError):
        validate_mock_oauth_state(state, workspace_id=workspace_id, user_id=user_id, now=now + timedelta(minutes=2))
    with pytest.raises(MetaOAuthStateError):
        validate_mock_oauth_state(state, workspace_id=uuid4(), user_id=user_id, now=now)
    with pytest.raises(MetaOAuthStateError):
        validate_mock_oauth_state(state, workspace_id=workspace_id, user_id=uuid4(), now=now)


def test_callback_result_masks_discards_token_and_performs_no_storage_or_live_call() -> None:
    service = MetaAdsMockOAuthService()
    workspace_id = uuid4()
    user_id = uuid4()
    start = service.start_mock_connect(workspace_id=workspace_id, user_id=user_id, role=RoleName.OWNER)

    result = service.simulate_callback(
        workspace_id=workspace_id,
        user_id=user_id,
        role=RoleName.OWNER,
        payload=MetaOAuthMockCallbackInputDTO(state=parse_qs(urlparse(start.authorization_url).query)["state"][0], code="mock_code_success"),
    )

    assert result.connected is False
    assert result.token_stored is False
    assert result.live_api_enabled is False
    assert result.token_safety is not None
    assert result.token_safety.masked_value.startswith("mock_token_************")
    assert result.token_safety.raw_token_returned is False
    assert result.token_safety.token_stored is False
    assert "successabcd" not in repr(result)


def test_status_is_not_active_and_read_only() -> None:
    workspace_id = uuid4()

    status = MetaAdsMockOAuthService().status(workspace_id)

    assert status.status == "NOT_ACTIVE"
    assert status.workspace_id == workspace_id
    assert status.connected is False
    assert status.token_stored is False
    assert status.live_api_enabled is False
