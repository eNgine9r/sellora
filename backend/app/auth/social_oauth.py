"""Server-side identity exchange for Sellora sign-in."""

from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
import base64
import hmac
from typing import Literal
from urllib.parse import urlencode, urlsplit

from email_validator import EmailNotValidError, validate_email
import httpx
from jose import JOSEError, jwt

from app.core.config import Settings, _JWT_HMAC_MIN_BYTES, _JWT_PLACEHOLDERS

Provider = Literal["google", "facebook"]
PROVIDERS: tuple[Provider, ...] = ("google", "facebook")
GOOGLE_AUTHORIZE = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN = "https://oauth2.googleapis.com/token"
GOOGLE_KEYS = "https://www.googleapis.com/oauth2/v3/certs"
FACEBOOK_GRAPH = "https://graph.facebook.com/v26.0"
FACEBOOK_AUTHORIZE = "https://www.facebook.com/v26.0/dialog/oauth"


class ProviderError(Exception):
    pass


@dataclass(frozen=True)
class Profile:
    subject: str
    first_name: str
    last_name: str
    verified_email: str | None = None


def normalize_email(value: str) -> str:
    return validate_email(value.strip(), check_deliverability=False).normalized.lower()


def public_origin(settings: Settings) -> str | None:
    minimum = _JWT_HMAC_MIN_BYTES.get(settings.jwt_algorithm)
    secret = settings.jwt_secret.strip()
    if (not settings.cookie_sessions_enabled or minimum is None or secret.lower() in _JWT_PLACEHOLDERS
            or len(secret.encode()) < minimum):
        return None
    origin = (settings.auth_public_origin or "").strip().rstrip("/")
    try:
        parsed = urlsplit(origin)
        secure = parsed.scheme == "https" or (
            settings.environment != "production"
            and parsed.scheme == "http" and parsed.hostname in {"localhost", "127.0.0.1"}
        )
        if (not secure or not parsed.hostname or parsed.username is not None
                or parsed.password is not None or origin != f"{parsed.scheme}://{parsed.netloc}"
                or "*" in origin):
            return None
    except ValueError:
        return None
    return origin


def provider_credentials(settings: Settings, provider: Provider) -> tuple[str, str] | None:
    if provider == "google":
        client_id, secret = settings.auth_google_client_id, settings.auth_google_client_secret
    else:
        client_id, secret = settings.auth_facebook_app_id, settings.auth_facebook_app_secret
    if client_id and client_id.strip() and secret and secret.get_secret_value().strip():
        return client_id.strip(), secret.get_secret_value()


def _profile(subject: object, first: object, last: object, email: str | None = None) -> Profile:
    if not isinstance(subject, str) or not subject or len(subject) > 255:
        raise ProviderError()
    first_name = first.strip()[:100] if isinstance(first, str) else ""
    last_name = last.strip()[:100] if isinstance(last, str) else ""
    return Profile(subject, first_name, last_name, email)


def _json(response: httpx.Response) -> dict:
    if not response.is_success:
        raise ProviderError()
    payload = response.json()
    if not isinstance(payload, dict) or payload.get("error"):
        raise ProviderError()
    return payload


class SocialOAuth:
    def __init__(self, settings: Settings, provider: Provider):
        credentials = provider_credentials(settings, provider)
        origin = public_origin(settings)
        if not credentials or not origin:
            raise ProviderError()
        self.client_id, self.secret = credentials
        self.provider = provider
        self.callback = f"{origin}{settings.api_v1_prefix}/auth/session/access/{provider}/callback"

    def authorization_url(self, *, state: str, verifier: str, nonce: str, locale: str) -> str:
        params = {
            "client_id": self.client_id, "redirect_uri": self.callback,
            "response_type": "code", "state": state,
        }
        if self.provider == "google":
            challenge = base64.urlsafe_b64encode(sha256(verifier.encode()).digest()).decode().rstrip("=")
            params.update(scope="openid email profile", code_challenge=challenge,
                          code_challenge_method="S256", nonce=nonce, prompt="select_account", hl=locale)
            return f"{GOOGLE_AUTHORIZE}?{urlencode(params)}"
        params.update(scope="public_profile", locale="uk_UA" if locale == "uk" else "en_US")
        return f"{FACEBOOK_AUTHORIZE}?{urlencode(params)}"

    def exchange(self, *, code: str, verifier: str, nonce: str) -> Profile:
        form = {"client_id": self.client_id, "client_secret": self.secret,
                "code": code, "redirect_uri": self.callback}
        try:
            with httpx.Client(timeout=8, follow_redirects=False) as client:
                if self.provider == "google":
                    return self._google(client, form, verifier, nonce)
                return self._facebook(client, form)
        except (httpx.HTTPError, JOSEError, ValueError, TypeError, KeyError, AttributeError, OverflowError):
            raise ProviderError() from None

    def _google(self, client: httpx.Client, form: dict, verifier: str, nonce: str) -> Profile:
        form.update(grant_type="authorization_code", code_verifier=verifier)
        response = _json(client.post(GOOGLE_TOKEN, data=form))
        token = response["id_token"]
        access_token = response.get("access_token")
        if not isinstance(token, str) or len(token) > 8192:
            raise ProviderError()
        if access_token is not None and (not isinstance(access_token, str) or not access_token or len(access_token) > 8192):
            raise ProviderError()
        header = jwt.get_unverified_header(token)
        keys = _json(client.get(GOOGLE_KEYS))["keys"]
        if not isinstance(keys, list) or not isinstance(header.get("kid"), str):
            raise ProviderError()
        key = next((k for k in keys if isinstance(k, dict) and k.get("kid") == header["kid"]), None)
        if key is None:
            raise ProviderError()
        claims = jwt.decode(
            token, key, algorithms=["RS256"], audience=self.client_id,
            issuer=("accounts.google.com", "https://accounts.google.com"),
            access_token=access_token,
            options={"require_exp": True, "require_iat": True, "require_sub": True, "require_aud": True},
        )
        if (claims.get("nonce") != nonce or claims.get("azp", self.client_id) != self.client_id
                or claims["iat"] > datetime.now(UTC).timestamp() + 60):
            raise ProviderError()
        email = None
        if claims.get("email_verified") is True and isinstance(claims.get("email"), str):
            try:
                candidate = normalize_email(claims["email"])
                hosted_domain = claims.get("hd")
                if candidate.endswith("@gmail.com") or (isinstance(hosted_domain, str) and hosted_domain):
                    email = candidate if len(candidate) <= 255 else None
            except EmailNotValidError:
                pass
        return _profile(claims["sub"], claims.get("given_name"), claims.get("family_name"), email)

    def _facebook(self, client: httpx.Client, form: dict) -> Profile:
        # The code exchange authenticates this app and returns an app-scoped user token.
        token = _json(client.post(f"{FACEBOOK_GRAPH}/oauth/access_token", data=form))["access_token"]
        if not isinstance(token, str) or not token or len(token) > 8192:
            raise ProviderError()
        proof = hmac.new(self.secret.encode(), token.encode(), sha256).hexdigest()
        result = _json(client.get(f"{FACEBOOK_GRAPH}/me", headers={"Authorization": f"Bearer {token}"},
                                  params={"fields": "id,first_name,last_name", "appsecret_proof": proof}))
        subject = result["id"]
        if not isinstance(subject, str) or not subject.isascii() or not subject.isdecimal():
            raise ProviderError()
        return _profile(subject, result.get("first_name"), result.get("last_name"))
