import hmac
import secrets
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr, Field, StringConstraints
from sqlalchemy.orm import Session

from app.api.v1.session_auth import COOKIE_NAME, _origin, _set_cookie
from app.auth.social_oauth import PROVIDERS, Provider, ProviderError, SocialOAuth, normalize_email, provider_credentials, public_origin
from app.core.config import Settings, get_settings
from app.database.session import get_db
from app.dependencies.auth import authenticate_access_session, bearer_scheme, get_current_user
from app.models.user import User
from app.services.public_auth_service import EmailRegistrationService, PublicAuthError, PublicAuthService, email_enabled, seal, unseal

router = APIRouter(prefix="/auth/session/access", tags=["Authentication"])
STATE_COOKIE = "sellora_auth_oauth"
SIGNUP_COOKIE = "sellora_auth_signup"
EMAIL_COOKIE = "sellora_auth_email"
Locale = Literal["uk", "en"]


class StartRequest(BaseModel):
    intent: Literal["login", "register", "link"]
    locale: Locale = "uk"
    accepts_terms: bool = False


class EmailRequest(BaseModel):
    social: bool = False
    email: Annotated[EmailStr, Field(max_length=255)]
    locale: Locale = "uk"


class EmailConfirmRequest(EmailRequest):
    code: Annotated[str, StringConstraints(pattern=r"^[0-9]{6}$")]
    first_name: Annotated[str, StringConstraints(strip_whitespace=True, max_length=100)] = ""
    password: Annotated[str, StringConstraints(min_length=12, max_length=128)] | None = None
    accepts_terms: bool = False


def _headers(response: Response) -> None:
    response.headers["Cache-Control"] = "no-store"
    response.headers["Referrer-Policy"] = "no-referrer"


def _browser_cookie(response: Response, key: str, value: str, settings: Settings, minutes: int) -> None:
    response.set_cookie(key, value, max_age=minutes * 60, httponly=True, samesite="lax",
                        secure=(public_origin(settings) or "").startswith("https:"),
                        path=f"{settings.api_v1_prefix}/auth/session/access")


def _clear(response: Response, key: str, settings: Settings) -> None:
    response.delete_cookie(key, httponly=True, samesite="lax",
                           secure=(public_origin(settings) or "").startswith("https:"),
                           path=f"{settings.api_v1_prefix}/auth/session/access")


def _available() -> tuple[Settings, str]:
    settings = get_settings()
    origin = public_origin(settings)
    if not origin:
        raise HTTPException(404, detail="unavailable")
    return settings, origin


def _setup_status(settings: Settings) -> dict:
    origin = public_origin(settings)
    email_registration = bool(origin) and email_enabled(settings)
    enabled = [provider for provider in PROVIDERS if origin and provider_credentials(settings, provider)]
    signup_providers = (
        [provider for provider in enabled if provider == "google" or email_registration]
        if settings.auth_registration_enabled else []
    )
    return {"providers": enabled, "signup_providers": signup_providers,
            "email_registration": email_registration, "origin": origin}


@router.get("/options")
def options(response: Response):
    _headers(response)
    return _setup_status(get_settings())


@router.get("/identities")
def identities(response: Response, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    settings, _ = _available()
    _headers(response)
    return {"providers": _setup_status(settings)["providers"],
            "linked": PublicAuthService(db).identities.providers(user.id)}


@router.post("/{provider}/start")
def start(provider: Provider, payload: StartRequest, request: Request, response: Response,
          credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme), db: Session = Depends(get_db)):
    settings, origin = _available()
    _origin(request, expected=origin)
    setup = _setup_status(settings)
    if provider not in setup["providers"]:
        raise HTTPException(404, detail="unavailable")
    if payload.intent == "register" and (not payload.accepts_terms or provider not in setup["signup_providers"]):
        raise HTTPException(400, detail="registration_unavailable")
    state, verifier, nonce = (secrets.token_urlsafe(32) for _ in range(3))
    claims = {"provider": provider, "intent": payload.intent, "state": state,
              "verifier": verifier, "nonce": nonce, "locale": payload.locale}
    if payload.intent == "link":
        user, sid = authenticate_access_session(credentials, db)
        if sid is None:
            raise HTTPException(401, detail="session_required")
        claims.update(uid=str(user.id), sid=str(sid))
    _headers(response)
    _browser_cookie(response, STATE_COOKIE, seal(settings, "oauth", claims, 10), settings, 10)
    return {"authorization_url": SocialOAuth(settings, provider).authorization_url(
        state=state, verifier=verifier, nonce=nonce, locale=payload.locale,
    )}


def _redirect(origin: str, target: str) -> RedirectResponse:
    response = RedirectResponse(f"{origin}{target}", status_code=303)
    _headers(response)
    return response


@router.get("/{provider}/callback", include_in_schema=False)
def callback(provider: Provider, request: Request, db: Session = Depends(get_db)):
    settings, origin = _available()
    claims = unseal(settings, "oauth", request.cookies.get(STATE_COOKIE))
    state = request.query_params.get("state", "")
    if (claims is None or claims.get("provider") != provider or not state or not state.isascii()
            or not hmac.compare_digest(state, claims["state"])):
        return _redirect(origin, "/login?auth=expired")

    intent = claims["intent"]
    error_path = {"link": "/settings/sign-in?auth=", "register": "/register?auth=", "login": "/login?auth="}[intent]
    response: Response
    code = request.query_params.get("code")
    try:
        if request.query_params.get("error") == "access_denied":
            raise PublicAuthError("cancelled")
        if not code or len(code) > 4096 or request.query_params.get("error"):
            raise ProviderError()
        profile = SocialOAuth(settings, provider).exchange(code=code, verifier=claims["verifier"], nonce=claims["nonce"])
        service = PublicAuthService(db)
        if intent == "link":
            service.link(provider, profile, UUID(claims["uid"]), UUID(claims["sid"]), request.cookies.get(COOKIE_NAME))
            response = _redirect(origin, "/settings/sign-in?auth=linked")
        elif intent == "login":
            session = service.social_sign_in(provider, profile)
            response = _redirect(origin, "/dashboard")
            _set_cookie(response, session, secure=origin.startswith("https:"))
        elif provider not in _setup_status(settings)["signup_providers"]:
            raise PublicAuthError("unavailable")
        elif service.identities.owner(provider, profile.subject):
            session = service.social_sign_in(provider, profile)
            response = _redirect(origin, "/dashboard")
            _set_cookie(response, session, secure=origin.startswith("https:"))
        elif profile.verified_email:
            session = service.register(profile.verified_email, profile.first_name, profile.last_name,
                                       provider=provider, subject=profile.subject)
            response = _redirect(origin, "/dashboard")
            _set_cookie(response, session, secure=origin.startswith("https:"))
        elif email_enabled(settings):
            response = _redirect(origin, "/register?auth=verify_email")
            _browser_cookie(response, SIGNUP_COOKIE, seal(settings, "signup", {
                "provider": provider, "subject": profile.subject, "first": profile.first_name,
                "last": profile.last_name, "binding": secrets.token_urlsafe(32),
            }, 20), settings, 20)
            _clear(response, EMAIL_COOKIE, settings)
        else:
            raise PublicAuthError("verified_email_required")
    except (ProviderError, PublicAuthError) as exc:
        error = str(exc) if isinstance(exc, PublicAuthError) else "provider_error"
        response = _redirect(origin, f"{error_path}{error}")
    _clear(response, STATE_COOKIE, settings)
    return response


@router.post("/email/send", status_code=202)
def send_code(payload: EmailRequest, request: Request, response: Response, db: Session = Depends(get_db)):
    settings, origin = _available()
    _origin(request, expected=origin)
    if not email_enabled(settings):
        raise HTTPException(404, detail="unavailable")
    existing = unseal(settings, "email", request.cookies.get(EMAIL_COOKIE))
    signup = unseal(settings, "signup", request.cookies.get(SIGNUP_COOKIE)) if payload.social else None
    if payload.social and signup is None:
        raise HTTPException(400, detail="expired")
    binding = signup["binding"] if signup else existing["binding"] if existing else secrets.token_urlsafe(32)
    try:
        EmailRegistrationService(db, settings).send(normalize_email(payload.email), payload.locale, binding)
    except PublicAuthError as exc:
        raise HTTPException(503, detail=str(exc)) from None
    _headers(response)
    if not signup:
        _browser_cookie(response, EMAIL_COOKIE, seal(settings, "email", {"binding": binding}, 20), settings, 20)
    return {"accepted": True}


@router.post("/email/confirm", status_code=204)
def confirm_email(payload: EmailConfirmRequest, request: Request, response: Response, db: Session = Depends(get_db)):
    settings, origin = _available()
    _origin(request, expected=origin)
    if not email_enabled(settings):
        raise HTTPException(404, detail="unavailable")
    signup = unseal(settings, "signup", request.cookies.get(SIGNUP_COOKIE)) if payload.social else None
    if payload.social and signup is None:
        raise HTTPException(400, detail="expired")
    email = unseal(settings, "email", request.cookies.get(EMAIL_COOKIE))
    if signup is not None and signup["provider"] not in _setup_status(settings)["signup_providers"]:
        raise HTTPException(404, detail="unavailable")
    if signup is None and (email is None or not payload.accepts_terms or not payload.first_name or payload.password is None):
        raise HTTPException(400, detail="invalid_registration")
    try:
        session = EmailRegistrationService(db, settings).confirm(
            normalize_email(payload.email), payload.code, (signup or email)["binding"],
            first_name=signup["first"] if signup else payload.first_name,
            last_name=signup["last"] if signup else "", password=None if signup else payload.password,
            provider=signup["provider"] if signup else None, subject=signup["subject"] if signup else None,
        )
    except PublicAuthError as exc:
        raise HTTPException(400, detail=str(exc)) from None
    _set_cookie(response, session, secure=origin.startswith("https:"))
    _clear(response, EMAIL_COOKIE, settings)
    _clear(response, SIGNUP_COOKIE, settings)
    _headers(response)
