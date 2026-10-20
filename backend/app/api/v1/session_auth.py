"""Opt-in same-origin session-cookie API. Legacy login remains unchanged.

The frontend must use the Vercel same-origin /api/v1 rewrite, not a cross-site
direct cookie request to the Raspberry host.
"""

from datetime import UTC, datetime
import os
from urllib.parse import urlsplit

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth.login_throttle import LoginThrottle, LoginThrottled
from app.auth.session_service import SessionAuthenticationService, SessionTokens
from app.core.config import get_settings
from app.database.session import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.auth import LoginRequest
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth/session", tags=["Authentication"])
COOKIE_NAME = "sellora_session_refresh"
COOKIE_PATH = "/api/v1/auth/session"


class SessionAccessResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


def _enabled():
    if not get_settings().cookie_sessions_enabled:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Session login is not enabled")


def _origin(request: Request) -> None:
    settings = get_settings()
    origins = os.getenv("SELLORA_CORS_ALLOWED_ORIGINS", "").strip()
    allowed = {
        part.strip().rstrip("/") for part in origins.split(",") if part.strip()
    } if origins else {"https://sellora-web-staging.vercel.app"}
    if settings.environment != "production":
        allowed.update(("http://localhost:3000", "http://127.0.0.1:3000"))

    origin = request.headers.get("Origin")
    if origin is not None:
        candidate = origin
    else:
        referer = request.headers.get("Referer")
        try:
            parsed = urlsplit(referer or "")
            candidate = f"{parsed.scheme}://{parsed.netloc}"
        except ValueError:
            candidate = ""
    # Fail closed for absent, null, foreign or malformed Origin/Referer.
    if not candidate or candidate not in allowed:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Untrusted session request origin")


def _set_cookie(response: Response, tokens: SessionTokens) -> None:
    response.set_cookie(
        key=COOKIE_NAME,
        value=tokens.refresh_cookie,
        httponly=True,
        secure=get_settings().environment == "production",
        samesite="lax",
        path=COOKIE_PATH,
        max_age=tokens.max_age_seconds,
    )
    response.headers["Cache-Control"] = "no-store"


def _clear_cookie(response: Response) -> None:
    response.delete_cookie(
        key=COOKIE_NAME,
        path=COOKIE_PATH,
        secure=get_settings().environment == "production",
        httponly=True,
        samesite="lax",
    )
    response.headers["Cache-Control"] = "no-store"


@router.post("/login", response_model=SessionAccessResponse)
def session_login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> SessionAccessResponse:
    _enabled()
    _origin(request)
    guard = LoginThrottle(db)
    try:
        guard.check(payload.email)
    except LoginThrottled as exc:
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many sign-in attempts",
            headers={"Retry-After": str(exc.retry_after_seconds)},
        ) from exc
    authenticated = AuthService(db).authenticate(payload.email, payload.password)
    if authenticated is None:
        guard.failed(payload.email)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    guard.succeeded(payload.email)
    user = AuthService(db).users.get_by_email(payload.email)
    if user is None or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    issued = SessionAuthenticationService(db).create(user.id)
    _set_cookie(response, issued)
    return SessionAccessResponse(access_token=issued.access_token)


@router.post("/upgrade", response_model=SessionAccessResponse)
def session_upgrade(
    request: Request,
    response: Response,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SessionAccessResponse:
    """Transition a valid existing bearer login without asking for the password again.

    The legacy refresh token should be discarded by the browser immediately after
    upgrade. Legacy JWT deprecation must be scheduled independently.
    """
    _enabled()
    _origin(request)
    issued = SessionAuthenticationService(db).create(current_user.id)
    _set_cookie(response, issued)
    return SessionAccessResponse(access_token=issued.access_token)


@router.post("/refresh", response_model=SessionAccessResponse)
def session_refresh(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> SessionAccessResponse:
    _enabled()
    _origin(request)
    issued = SessionAuthenticationService(db).rotate(request.cookies.get(COOKIE_NAME))
    if issued is None:
        _clear_cookie(response)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Session expired or revoked")
    _set_cookie(response, issued)
    return SessionAccessResponse(access_token=issued.access_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def session_logout(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> None:
    _enabled()
    _origin(request)
    SessionAuthenticationService(db).revoke(request.cookies.get(COOKIE_NAME))
    _clear_cookie(response)


@router.post("/logout-all", status_code=status.HTTP_204_NO_CONTENT)
def session_logout_all(
    request: Request,
    response: Response,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    _enabled()
    _origin(request)
    SessionAuthenticationService(db).revoke_all(current_user.id)
    _clear_cookie(response)
