"""Regression guard: every Raspberry release must retain secure-session routes.

The regression was introduced when a feature release overlaid GitHub's old
api/v1/router.py, which did not register the already-deployed session_auth
router. This suite requires no real credentials or database writes.
"""
from types import SimpleNamespace

from fastapi.testclient import TestClient

import app.api.v1.session_auth as session_auth
from app.main import app


def test_staging_secure_login_endpoint_remains_registered(monkeypatch):
    monkeypatch.setattr(
        session_auth, "get_settings",
        lambda: SimpleNamespace(cookie_sessions_enabled=True, environment="production"),
    )
    with TestClient(app) as client:
        # Missing fields yield validation error if route exists, but 404 if
        # session_auth has been omitted from app/api/v1/router.py.
        response = client.post(
            "/api/v1/auth/session/login",
            json={},
            headers={"Origin": "https://sellora-web-staging.vercel.app"},
        )
        assert response.status_code == 422
        assert response.json()["detail"]


def test_session_refresh_is_registered_and_requires_cookie(monkeypatch):
    monkeypatch.setattr(
        session_auth, "get_settings",
        lambda: SimpleNamespace(cookie_sessions_enabled=True, environment="production"),
    )
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/auth/session/refresh",
            headers={"Origin": "https://sellora-web-staging.vercel.app"},
        )
        assert response.status_code == 401


def test_session_refresh_rejects_foreign_origin(monkeypatch):
    monkeypatch.setattr(
        session_auth, "get_settings",
        lambda: SimpleNamespace(cookie_sessions_enabled=True, environment="production"),
    )
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/auth/session/refresh",
            headers={"Origin": "https://example.invalid"},
        )
        assert response.status_code == 403


def test_legacy_login_endpoint_retained_without_signin_attempt():
    with TestClient(app) as client:
        response = client.post("/api/v1/auth/login", json={})
        assert response.status_code == 422
