from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.login_throttle import LoginThrottle, LoginThrottled
from app.core.config import get_settings
from app.database.session import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.auth import CurrentUserResponse, LoginRequest, RefreshRequest, TokenPair
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=TokenPair)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenPair:
    if not get_settings().legacy_auth_enabled:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Legacy sign-in is unavailable")
    throttle = LoginThrottle(db)
    try:
        throttle.check(payload.email)
    except LoginThrottled as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many sign-in attempts. Try again later.",
            headers={"Retry-After": str(exc.retry_after_seconds)},
        ) from exc
    tokens = AuthService(db).authenticate(payload.email, payload.password)
    if tokens is None:
        throttle.failed(payload.email)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    throttle.succeeded(payload.email)
    return tokens


@router.post("/refresh", response_model=TokenPair)
def refresh(payload: RefreshRequest, db: Session = Depends(get_db)) -> TokenPair:
    if not get_settings().legacy_auth_enabled:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Legacy refresh is unavailable")
    tokens = AuthService(db).refresh(payload.refresh_token)
    if tokens is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
    return tokens


@router.get("/me", response_model=CurrentUserResponse)
def me(current_user: User = Depends(get_current_user)) -> CurrentUserResponse:
    return AuthService.to_current_user_response(current_user)
