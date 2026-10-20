"""Isolated PostgreSQL + FastAPI session security integration tests.

Run ONLY with COOKIE_SESSION_TEST_DB_URL pointing to disposable synthetic DB.
No production users, secrets, Meta accounts, or Direct messages are accessed.
"""

import os
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

from app.auth.password import hash_password
from app.auth.jwt import create_access_token
from app.auth.session_service import SessionAuthenticationService
from app.main import app
from app.repositories.user_repository import UserRepository

TEST_URL = os.environ.get("COOKIE_SESSION_TEST_DB_URL")
pytestmark = pytest.mark.skipif(not TEST_URL, reason="Requires isolated disposable PostgreSQL")


@pytest.fixture
def app_client(monkeypatch):
    assert TEST_URL and "sellora-cookie-pg-qa" in TEST_URL, "Refuse real DB"
    uid = uuid4()
    fake = SimpleNamespace(
        id=uid,
        email="synthetic-owner@example.com",
        password_hash=hash_password("synthetic-password-not-real"),
        first_name="Synthetic",
        last_name="Owner",
        is_active=True,
        last_login_at=None,
        workspaces=[],
    )
    engine = create_engine(TEST_URL, connect_args={"prepare_threshold": None})
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO users(id,email,password_hash,first_name,last_name,is_active) "
                "VALUES (:id,:email,:hash,'Synthetic','Owner',true)"
            ),
            {"id": uid, "email": fake.email, "hash": fake.password_hash},
        )
    monkeypatch.setattr(UserRepository, "get_by_email", lambda self, email: fake if email == fake.email else None)
    monkeypatch.setattr(UserRepository, "get_by_id", lambda self, user_id: fake if user_id == uid else None)
    with TestClient(app, base_url="https://sellora-web-staging.vercel.app") as client:
        yield client, fake, engine
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM auth_sessions WHERE user_id=:uid"), {"uid": uid})
        conn.execute(text("DELETE FROM users WHERE id=:uid"), {"uid": uid})
    engine.dispose()


def login(client):
    return client.post(
        "/api/v1/auth/session/login",
        headers={"Origin": "https://sellora-web-staging.vercel.app"},
        json={"email": "synthetic-owner@example.com", "password": "synthetic-password-not-real"},
    )


def post(client, path, **kwargs):
    headers = kwargs.pop("headers", {})
    return client.post(
        "/api/v1/auth/session/" + path,
        headers={"Origin": "https://sellora-web-staging.vercel.app", **headers},
        **kwargs,
    )


def test_cookie_login_refresh_rotation_csrf_and_revoke(app_client):
    client, fake, engine = app_client
    assert client.post(
        "/api/v1/auth/session/login",
        json={"email": fake.email, "password": "synthetic-password-not-real"},
    ).status_code == 403
    assert client.post(
        "/api/v1/auth/session/login",
        headers={"Origin": "https://attacker.example"},
        json={"email": fake.email, "password": "synthetic-password-not-real"},
    ).status_code == 403

    first = login(client)
    assert first.status_code == 200, first.text[:300]
    assert "refresh_token" not in first.json()
    assert first.json()["access_token"]
    from app.auth.jwt import decode_token
    assert decode_token(first.json()["access_token"], "access").get("sid")
    cookie_header = first.headers["set-cookie"]
    for flag in ("httponly", "secure", "samesite=lax", "path=/api/v1/auth/session"):
        assert flag in cookie_header.lower()
    old_cookie = first.cookies.get("sellora_session_refresh")
    assert old_cookie and len(old_cookie) > 70

    with engine.connect() as conn:
        saved = conn.execute(
            text("SELECT refresh_hash,rotation_count FROM auth_sessions WHERE user_id=:uid"),
            {"uid": fake.id},
        ).one()
    assert len(saved.refresh_hash) == 64 and old_cookie not in saved.refresh_hash
    assert saved.rotation_count == 0

    refresh = post(client, "refresh")
    assert refresh.status_code == 200
    current_cookie = refresh.cookies.get("sellora_session_refresh")
    assert current_cookie and current_cookie != old_cookie
    assert "refresh_token" not in refresh.json()

    # Replaying an older cookie during short concurrent-tab grace returns 409,
    # not another token and not global logout.
    race = post(client, "refresh", headers={"Cookie": "sellora_session_refresh=" + old_cookie})
    assert race.status_code == 409, race.text[:250]
    assert post(client, "refresh").status_code == 200

    # Delayed replay of an old refresh token revokes that one session.
    with engine.begin() as conn:
        conn.execute(
            text("UPDATE auth_sessions SET rotated_at=:ago WHERE user_id=:uid"),
            {"uid": fake.id, "ago": datetime.now(UTC) - timedelta(seconds=20)},
        )
    replay = post(client, "refresh", headers={"Cookie": "sellora_session_refresh=" + old_cookie})
    assert replay.status_code == 401
    assert post(client, "refresh").status_code == 401
    protected = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer " + first.json()["access_token"]},
    )
    assert protected.status_code == 401


def test_seamless_upgrade_and_logout_all(app_client):
    client, fake, engine = app_client
    legacy_access = create_access_token(fake.id)
    no_csrf = client.post(
        "/api/v1/auth/session/upgrade", headers={"Authorization": "Bearer " + legacy_access}
    )
    assert no_csrf.status_code == 403
    upgrade = post(client, "upgrade", headers={"Authorization": "Bearer " + legacy_access})
    assert upgrade.status_code == 200
    assert "refresh_token" not in upgrade.json()
    assert upgrade.cookies.get("sellora_session_refresh")

    second = login(client)
    assert second.status_code == 200

    revoked = post(client, "logout-all", headers={"Authorization": "Bearer " + legacy_access})
    assert revoked.status_code == 204
    assert post(client, "refresh").status_code == 401
    with engine.connect() as conn:
        remaining = conn.execute(
            text("SELECT count(*) FROM auth_sessions WHERE user_id=:uid AND revoked_at IS NULL"),
            {"uid": fake.id},
        ).scalar_one()
    assert remaining == 0
    assert client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer " + upgrade.json()["access_token"]},
    ).status_code == 401


def test_feature_off_returns_404(monkeypatch, app_client):
    import app.api.v1.session_auth as session_api
    from app.core.config import get_settings

    original = get_settings()
    monkeypatch.setattr(
        session_api, "get_settings",
        lambda: SimpleNamespace(cookie_sessions_enabled=False, environment="production"),
    )
    client, fake, _ = app_client
    assert login(client).status_code == 404
    assert post(client, "refresh").status_code == 404
