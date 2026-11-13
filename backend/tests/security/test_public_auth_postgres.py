"""HTTP auth flows with real session persistence on disposable PostgreSQL."""

import os
from urllib.parse import parse_qs, urlsplit
from uuid import uuid4

from fastapi.testclient import TestClient
import pytest
from pydantic import SecretStr
from sqlalchemy import create_engine, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from app.auth.password import hash_password
from app.auth.social_oauth import Profile
from app.core.config import get_settings
from app.database.session import get_db
from app.main import app
from app.models.user import User

pytestmark = pytest.mark.skipif(
    os.getenv("SELLORA_PUBLIC_AUTH_DISPOSABLE_CANARY") != "YES",
    reason="explicit disposable public auth database required",
)
PREFIX = "/api/v1/auth/session/access"
ORIGIN = "http://localhost:3000"
HEADERS = {"Origin": ORIGIN}
PASSWORD = "Synthetic-account-passphrase-1"


@pytest.fixture
def auth(monkeypatch):
    settings = get_settings()
    for key, value in {
        "cookie_sessions_enabled": True, "auth_public_origin": ORIGIN, "auth_registration_enabled": True,
        "auth_google_client_id": "test-google", "auth_google_client_secret": SecretStr("secret"),
        "auth_facebook_app_id": "123", "auth_facebook_app_secret": SecretStr("secret"),
        "jwt_secret": "synthetic-signing-key-for-disposable-tests-only", "auth_smtp_host": "smtp.example.com",
        "auth_smtp_from": "mail@example.com", "auth_smtp_user": None, "auth_smtp_password": None,
    }.items():
        monkeypatch.setattr(settings, key, value)
    monkeypatch.setenv("SELLORA_CORS_ALLOWED_ORIGINS", ORIGIN)
    url = make_url(os.environ["DATABASE_URL"])
    assert url.database == "sellora_public_auth_canary_isolated"
    engine = create_engine(url)
    with engine.connect() as connection, connection.begin() as transaction:
        with Session(bind=connection, join_transaction_mode="create_savepoint") as db:
            app.dependency_overrides[get_db] = lambda: db
            try:
                yield TestClient(app, base_url=ORIGIN), db
            finally:
                app.dependency_overrides.pop(get_db, None)
        transaction.rollback()
    engine.dispose()


def start(client, provider, intent, bearer=None, *, accept=True):
    headers = {**HEADERS, **({"Authorization": f"Bearer {bearer}"} if bearer else {})}
    return client.post(f"{PREFIX}/{provider}/start", headers=headers, json={"intent": intent, "accepts_terms": accept})


def complete(client, provider, started, **overrides):
    query = parse_qs(urlsplit(started.json()["authorization_url"]).query)
    return client.get(f"{PREFIX}/{provider}/callback",
                      params={"state": query["state"][0], "code": "synthetic", **overrides},
                      follow_redirects=False)


def me(client):
    rotated = client.post("/api/v1/auth/session/refresh", headers=HEADERS)
    assert rotated.status_code == 200
    return client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {rotated.json()['access_token']}"})


def profile(monkeypatch, email=None):
    monkeypatch.setattr("app.auth.social_oauth.SocialOAuth.exchange",
                        lambda *_, **__: Profile("987654321", "Test", "Owner", email))


def test_google_registration_sign_in_and_no_automatic_workspace(auth, monkeypatch):
    client, db = auth
    email = f"owner{uuid4().hex}@gmail.com"
    profile(monkeypatch, email)
    assert start(client, "google", "register", accept=False).status_code == 400
    started = start(client, "google", "register")
    assert "HttpOnly" in started.headers["Set-Cookie"]
    assert complete(client, "google", started, state="wrong").headers["Location"].endswith("/login?auth=expired")
    response = complete(client, "google", started)
    assert response.headers["Location"].endswith("/dashboard")
    assert "HttpOnly" in response.headers["Set-Cookie"]
    original = me(client).json()
    assert original["email"] == email and original["memberships"] == []
    assert db.scalar(select(User).where(User.email == email)).password_hash is None
    assert db.scalar(text("SELECT authenticated_via FROM public.auth_sessions WHERE user_id = :id"),
                     {"id": original["id"]}) is None
    client.post("/api/v1/auth/session/logout", headers=HEADERS)
    response = complete(client, "google", start(client, "google", "login"))
    assert response.headers["Location"].endswith("/dashboard")
    assert me(client).json()["id"] == original["id"]


def test_existing_email_requires_explicit_link_and_current_refresh_session(auth, monkeypatch):
    client, db = auth
    email = f"existing{uuid4().hex}@gmail.com"
    user = User(email=email, first_name="Existing", last_name="Owner", password_hash=hash_password(PASSWORD))
    db.add(user)
    db.commit()
    profile(monkeypatch, email)
    assert complete(client, "google", start(client, "google", "login")).headers["Location"].endswith("auth=account_required")
    assert complete(client, "google", start(client, "google", "register")).headers["Location"].endswith("auth=account_exists")
    assert start(client, "google", "link").status_code == 401
    logged_in = client.post("/api/v1/auth/session/login", headers=HEADERS, json={"email": email, "password": PASSWORD})
    bearer = logged_in.json()["access_token"]
    started = start(client, "google", "link", bearer)
    client.post("/api/v1/auth/session/logout", headers=HEADERS)
    assert complete(client, "google", started).headers["Location"].endswith("auth=session_required")
    logged_in = client.post("/api/v1/auth/session/login", headers=HEADERS, json={"email": email, "password": PASSWORD})
    bearer = logged_in.json()["access_token"]
    linked = complete(client, "google", start(client, "google", "link", bearer))
    assert linked.headers["Location"].endswith("/settings/sign-in?auth=linked")
    assert client.get(f"{PREFIX}/identities", headers={"Authorization": f"Bearer {bearer}"}).json()["linked"] == ["google"]
    client.post("/api/v1/auth/session/logout", headers=HEADERS)
    assert complete(client, "google", start(client, "google", "login")).headers["Location"].endswith("/dashboard")
    assert me(client).json()["id"] == str(user.id)


@pytest.mark.parametrize("social", [False, True])
def test_email_code_signup_and_facebook_verification(auth, monkeypatch, social):
    client, _ = auth
    email = f"new{uuid4().hex}@example.com"
    codes = []
    monkeypatch.setattr("app.services.public_auth_service.EmailRegistrationService._deliver",
                        lambda _, to, locale, code: codes.append(code))
    if social:
        profile(monkeypatch)
        response = complete(client, "facebook", start(client, "facebook", "register"))
        assert response.headers["Location"].endswith("/register?auth=verify_email")
    assert client.post(f"{PREFIX}/email/send", headers=HEADERS, json={"email": email, "social": social}).status_code == 202
    assert client.post(f"{PREFIX}/email/send", headers=HEADERS, json={"email": email, "social": social}).status_code == 202
    assert len(codes) == 1
    details = {"email": email, "first_name": "Shop", "password": PASSWORD, "accepts_terms": True, "social": social}
    bad = "000000" if codes[0] != "000000" else "111111"
    rejected = client.post(f"{PREFIX}/email/confirm", headers=HEADERS, json={**details, "code": bad})
    assert rejected.json()["detail"] == "invalid_code"
    accepted = client.post(f"{PREFIX}/email/confirm", headers=HEADERS, json={**details, "code": codes[0]})
    assert accepted.status_code == 204
    account = me(client).json()
    assert account["email"] == email
    assert client.post(f"{PREFIX}/email/confirm", headers=HEADERS, json={**details, "code": codes[0]}).status_code == 400
    client.post("/api/v1/auth/session/logout", headers=HEADERS)
    if social:
        assert complete(client, "facebook", start(client, "facebook", "login")).headers["Location"].endswith("/dashboard")
    else:
        mixed_case_email = "New" + email[3:]
        assert client.post("/api/v1/auth/session/login", headers=HEADERS,
                           json={"email": mixed_case_email, "password": PASSWORD}).status_code == 200
    assert me(client).json()["id"] == account["id"]


def test_untrusted_origin_and_validation_payloads_are_rejected(auth):
    client, _ = auth
    denied = client.post(f"{PREFIX}/google/start", headers={"Origin": "https://foreign.example"},
                         json={"intent": "login"})
    assert denied.status_code == 403
    invalid = client.post(f"{PREFIX}/email/confirm", headers=HEADERS,
                          json={"email": "invalid", "code": "must-not-be-echoed"})
    assert invalid.status_code == 422 and invalid.json() == {"detail": "invalid_request"}


def test_social_session_cannot_open_platform_admin_even_with_a_platform_grant(auth, monkeypatch):
    from app.models.platform_admin import PlatformGrant, PlatformRole

    client, db = auth
    settings = get_settings()
    monkeypatch.setattr(settings, "platform_admin_enabled", True)
    monkeypatch.setattr(settings, "platform_admin_mfa_required", True)
    email = f"admin{uuid4().hex}@gmail.com"
    profile(monkeypatch, email)
    assert complete(client, "google", start(client, "google", "register")).headers["Location"].endswith("/dashboard")
    user = db.scalar(select(User).where(User.email == email))
    db.add(PlatformGrant(user_id=user.id, role=PlatformRole.ADMIN))
    db.commit()
    session = client.post("/api/v1/auth/session/refresh", headers=HEADERS)
    headers = {"Authorization": f"Bearer {session.json()['access_token']}"}
    assert client.get("/api/v1/auth/me", headers=headers).status_code == 200
    assert client.get("/api/v1/platform-admin/me", headers=headers).status_code == 401
    assert client.post("/api/v1/platform-admin/mfa/verify", headers=headers, json={"code": "123456"}).status_code == 401
