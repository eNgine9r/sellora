from datetime import UTC, datetime, timedelta
from urllib.parse import parse_qs, urlsplit

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
import httpx
from jose import jwk, jwt
import pytest

from app.auth.social_oauth import Profile, ProviderError, SocialOAuth, public_origin
from app.core.config import Settings


@pytest.fixture
def settings():
    return Settings(
        cookie_sessions_enabled=True, auth_public_origin="https://sellora.example.com",
        jwt_secret="synthetic-key-for-public-auth-tests-32-bytes",
        auth_google_client_id="sellora-web", auth_google_client_secret="test-google-secret",
        auth_facebook_app_id="123", auth_facebook_app_secret="test-facebook-secret",
    )


def test_public_origin_requires_cookie_sessions_and_signing_key(settings):
    assert public_origin(settings) == "https://sellora.example.com"
    settings.auth_public_origin = "https://sellora.example.com/mismatch"
    assert public_origin(settings) is None
    settings.auth_public_origin = "https://sellora.example.com"
    settings.jwt_secret = "change-me"
    assert public_origin(settings) is None


def test_google_authorization_uses_nonce_and_pkce(settings):
    oauth = SocialOAuth(settings, "google")
    url = urlsplit(oauth.authorization_url(state="state", verifier="verifier", nonce="nonce", locale="uk"))
    params = parse_qs(url.query)
    assert url.hostname == "accounts.google.com"
    assert params["state"] == ["state"]
    assert params["nonce"] == ["nonce"]
    assert params["code_challenge_method"] == ["S256"]
    assert params["scope"] == ["openid email profile"]
    assert params["redirect_uri"] == ["https://sellora.example.com/api/v1/auth/session/access/google/callback"]
    assert "client_secret" not in params and "verifier" not in url.query


@pytest.fixture(scope="module")
def google_key():
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private = key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                                serialization.NoEncryption())
    public = key.public_key().public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
    return private, {**jwk.construct(public, "RS256").to_dict(), "kid": "test-key"}


@pytest.mark.parametrize(("changes", "expected"), [
    ({}, "owner@gmail.com"),
    ({"email": "owner@example.com"}, None),
    ({"email": "owner@example.com", "hd": "example.com"}, "owner@example.com"),
    ({"email_verified": False}, None),
    ({"nonce": "wrong"}, "reject"),
    ({"aud": "wrong"}, "reject"),
    ({"iss": "https://invalid.example.com"}, "reject"),
    ({"exp": 1}, "reject"),
    ({"azp": "wrong"}, "reject"),
])
def test_google_identity_claims(settings, google_key, monkeypatch, changes, expected):
    private, public = google_key
    now = datetime.now(UTC)
    claims = {"sub": "123", "aud": "sellora-web", "iss": "https://accounts.google.com",
              "iat": now, "exp": now + timedelta(minutes=3), "nonce": "nonce",
              "email": "Owner@gmail.com", "email_verified": True, "given_name": "Owner", **changes}
    token = jwt.encode(claims, private, algorithm="RS256", headers={"kid": "test-key"})

    def transport(request):
        if request.url.host == "oauth2.googleapis.com":
            assert request.method == "POST"
            assert parse_qs(request.content.decode())["code_verifier"] == ["verifier"]
            return httpx.Response(200, json={"id_token": token})
        assert request.url.host == "www.googleapis.com"
        return httpx.Response(200, json={"keys": [public]})

    client = httpx.Client(transport=httpx.MockTransport(transport))
    monkeypatch.setattr("app.auth.social_oauth.httpx.Client", lambda **_: client)
    oauth = SocialOAuth(settings, "google")
    if expected == "reject":
        with pytest.raises(ProviderError):
            oauth.exchange(code="code", verifier="verifier", nonce="nonce")
    else:
        assert oauth.exchange(code="code", verifier="verifier", nonce="nonce") == Profile("123", "Owner", "", expected)


def test_facebook_uses_app_scoped_id_and_verifies_email_separately(settings, monkeypatch):
    def transport(request):
        assert request.url.host == "graph.facebook.com"
        if request.method == "POST":
            assert parse_qs(request.content.decode())["client_secret"] == ["test-facebook-secret"]
            return httpx.Response(200, json={"access_token": "temporary"})
        assert request.headers["Authorization"] == "Bearer temporary"
        assert len(request.url.params["appsecret_proof"]) == 64
        return httpx.Response(200, json={"id": "456", "first_name": "Shop", "email": "ignored@example.com"})

    client = httpx.Client(transport=httpx.MockTransport(transport))
    monkeypatch.setattr("app.auth.social_oauth.httpx.Client", lambda **_: client)
    assert SocialOAuth(settings, "facebook").exchange(code="code", verifier="verifier", nonce="nonce") == Profile("456", "Shop", "")
