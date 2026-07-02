from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import parse_qs, urlparse
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1.meta_ads_mock import router
from app.core.config import get_settings
from app.dependencies.auth import get_current_user
from app.dependencies.rbac import get_workspace_id
from app.integrations.meta_ads.oauth_mock import MOCK_META_OAUTH_AUTHORIZE_URL
from app.integrations.meta_ads.oauth_state import generate_mock_oauth_state
from app.models.role import RoleName


class StubSettings:
    def __init__(self, enabled: bool) -> None:
        self.meta_ads_mock_oauth_api_enabled = enabled


class WriteTrap:
    commits = 0
    flushes = 0

    def commit(self) -> None:
        self.commits += 1
        raise AssertionError("Meta Ads mock routes must not commit")

    def flush(self) -> None:
        self.flushes += 1
        raise AssertionError("Meta Ads mock routes must not flush")


def _user(workspace_id, role: RoleName):
    return SimpleNamespace(
        id=uuid4(),
        workspaces=[SimpleNamespace(workspace_id=workspace_id, workspace=SimpleNamespace(is_active=True), role=SimpleNamespace(name=role.value))],
    )


def _client(*, enabled: bool, role: RoleName = RoleName.OWNER, workspace_id=None):
    workspace_id = workspace_id or uuid4()
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    user = _user(workspace_id, role)
    app.dependency_overrides[get_workspace_id] = lambda: workspace_id
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_settings] = lambda: StubSettings(enabled)
    return TestClient(app), workspace_id, user


def _extract_state(authorization_url: str) -> str:
    return parse_qs(urlparse(authorization_url).query)["state"][0]


def test_status_route_works_safely_when_feature_gate_disabled() -> None:
    client, workspace_id, _ = _client(enabled=False, role=RoleName.ANALYST)

    response = client.get("/api/v1/integrations/meta-ads/mock/status")

    assert response.status_code == 200
    payload = response.json()
    assert payload["provider"] == "meta_ads"
    assert payload["connection_mode"] == "mock"
    assert payload["workspace_id"] == str(workspace_id)
    assert payload["mock_api_enabled"] is False
    assert payload["connected"] is False
    assert payload["token_stored"] is False
    assert payload["live_api_enabled"] is False
    assert "authorization_url" not in payload
    assert payload["audit_event"]["event"] == "meta_ads_mock_status_viewed"
    assert payload["audit_event"]["persisted"] is False


def test_connect_like_routes_are_blocked_when_feature_gate_disabled() -> None:
    client, _, _ = _client(enabled=False, role=RoleName.OWNER)

    assert client.post("/api/v1/integrations/meta-ads/mock/oauth/start").status_code == 403
    assert client.post("/api/v1/integrations/meta-ads/mock/oauth/callback", json={"state": "invalid", "code": "mock_code_ok"}).status_code == 403
    assert client.post("/api/v1/integrations/meta-ads/mock/disconnect").status_code == 403


def test_owner_can_start_mock_flow_when_feature_gate_enabled() -> None:
    client, _, _ = _client(enabled=True, role=RoleName.OWNER)

    response = client.post("/api/v1/integrations/meta-ads/mock/oauth/start")

    assert response.status_code == 200
    payload = response.json()
    assert payload["authorization_url"].startswith(MOCK_META_OAUTH_AUTHORIZE_URL)
    assert "facebook.com" not in payload["authorization_url"]
    assert "graph.facebook.com" not in payload["authorization_url"]
    assert payload["connected"] is False
    assert payload["token_stored"] is False
    assert payload["live_api_enabled"] is False
    assert "access_token" not in str(payload)
    assert "mock_token_" not in str(payload)
    assert payload["audit_event"]["event"] == "meta_ads_mock_connect_started"
    assert payload["audit_event"]["payload"]["db_write"] is False


def test_manager_and_analyst_are_denied_by_route_level_owner_guard() -> None:
    manager_client, _, _ = _client(enabled=True, role=RoleName.MANAGER)
    analyst_client, _, _ = _client(enabled=True, role=RoleName.ANALYST)

    assert manager_client.post("/api/v1/integrations/meta-ads/mock/oauth/start").status_code == 403
    assert analyst_client.post("/api/v1/integrations/meta-ads/mock/oauth/start").status_code == 403


def test_callback_validates_state_and_returns_safe_token_metadata() -> None:
    client, _, _ = _client(enabled=True, role=RoleName.OWNER)
    start = client.post("/api/v1/integrations/meta-ads/mock/oauth/start")
    state = _extract_state(start.json()["authorization_url"])

    response = client.post("/api/v1/integrations/meta-ads/mock/oauth/callback", json={"state": state, "code": "mock_code_success"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["connected"] is False
    assert payload["requires_live_setup"] is True
    assert payload["token_stored"] is False
    assert payload["live_api_enabled"] is False
    assert payload["token_safety"]["raw_token_returned"] is False
    assert "********" in payload["token_safety"]["masked_value"]
    assert "mock_code_success" not in str(payload)
    assert payload["audit_event"]["event"] == "meta_ads_mock_connect_callback_validated"


def test_callback_rejects_invalid_expired_and_mismatched_state() -> None:
    client, workspace_id, user = _client(enabled=True, role=RoleName.OWNER)

    invalid = client.post("/api/v1/integrations/meta-ads/mock/oauth/callback", json={"state": "not-valid", "code": "mock_code_success"})
    assert invalid.status_code == 400

    expired_state, _ = generate_mock_oauth_state(workspace_id=workspace_id, user_id=user.id, now=datetime.now(UTC) - timedelta(minutes=20), ttl_minutes=1)
    expired = client.post("/api/v1/integrations/meta-ads/mock/oauth/callback", json={"state": expired_state, "code": "mock_code_success"})
    assert expired.status_code == 400

    mismatch_state, _ = generate_mock_oauth_state(workspace_id=uuid4(), user_id=user.id)
    mismatched = client.post("/api/v1/integrations/meta-ads/mock/oauth/callback", json={"state": mismatch_state, "code": "mock_code_success"})
    assert mismatched.status_code == 400


def test_disconnect_returns_safe_non_persistent_result() -> None:
    client, _, _ = _client(enabled=True, role=RoleName.OWNER)

    response = client.post("/api/v1/integrations/meta-ads/mock/disconnect")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "MOCK_DISCONNECTED"
    assert payload["connected"] is False
    assert payload["token_stored"] is False
    assert payload["live_api_enabled"] is False
    assert payload["audit_event"]["event"] == "meta_ads_mock_disconnected"
    assert payload["audit_event"]["persisted"] is False
    assert payload["audit_event"]["payload"]["connection_deleted"] is False


def test_route_source_has_no_db_writes_live_http_or_real_meta_domains() -> None:
    route_source = Path("app/api/v1/meta_ads_mock.py").read_text()
    package_source = "\n".join(path.read_text() for path in Path("app/integrations/meta_ads").glob("*.py"))

    assert ".commit(" not in route_source
    assert ".flush(" not in route_source
    assert "Session" not in route_source
    assert "httpx" not in route_source
    assert "requests" not in route_source
    assert "facebook.com" not in route_source
    assert "graph.facebook.com" not in route_source
    assert "facebook.com" not in package_source
    assert "graph.facebook.com" not in package_source
