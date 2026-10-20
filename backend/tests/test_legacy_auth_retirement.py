"""Legacy JWT retirement checks; synthetic data only; no real accounts required."""

from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException, Response

import app.api.v1.auth as legacy_api
import app.api.v1.session_auth as session_api
import app.dependencies.auth as auth_dep
from app.auth.jwt import create_access_token
from app.schemas.auth import LoginRequest, RefreshRequest


@pytest.fixture
def retired(monkeypatch):
    monkeypatch.setattr(legacy_api, "get_settings", lambda: SimpleNamespace(legacy_auth_enabled=False))
    monkeypatch.setattr(session_api, "get_settings", lambda: SimpleNamespace(
        legacy_auth_enabled=False, cookie_sessions_enabled=True, environment="production"
    ))
    monkeypatch.setattr(auth_dep, "get_settings", lambda: SimpleNamespace(legacy_auth_enabled=False))


def test_old_login_returns_404_before_password_verification(retired):
    with pytest.raises(HTTPException) as result:
        legacy_api.login(
            LoginRequest(email="synthetic@example.com", password="fake-only"),
            db=None,
        )
    assert result.value.status_code == 404


def test_old_refresh_returns_404_without_returning_tokens(retired):
    with pytest.raises(HTTPException) as result:
        legacy_api.refresh(RefreshRequest(refresh_token="fake-only"), db=None)
    assert result.value.status_code == 404


def test_old_access_token_without_session_id_is_rejected(retired):
    legacy_access = create_access_token(uuid4())
    with pytest.raises(HTTPException) as result:
        auth_dep.get_current_user(
            credentials=SimpleNamespace(credentials=legacy_access),
            db=None,
        )
    assert result.value.status_code == 401


def test_old_upgrade_endpoint_disabled(retired):
    with pytest.raises(HTTPException) as result:
        session_api.session_upgrade(
            request=None, response=Response(),
            current_user=SimpleNamespace(id=uuid4()),
            db=None,
        )
    assert result.value.status_code == 404


def test_legacy_compatibility_defaults_to_on(monkeypatch):
    from app.core.config import Settings
    monkeypatch.delenv("SELLORA_LEGACY_AUTH_ENABLED", raising=False)
    assert Settings().legacy_auth_enabled is True
