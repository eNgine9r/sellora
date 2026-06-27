from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from jose import JWTError, jwt

from app.core.config import get_settings

settings = get_settings()


def _create_token(subject: str, token_type: str, expires_delta: timedelta, extra_claims: dict[str, Any] | None = None) -> str:
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": subject,
        "type": token_type,
        "iat": now,
        "exp": now + expires_delta,
    }
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def create_access_token(user_id: UUID) -> str:
    return _create_token(str(user_id), "access", timedelta(minutes=settings.jwt_expire_minutes))


def create_refresh_token(user_id: UUID) -> str:
    return _create_token(str(user_id), "refresh", timedelta(days=settings.refresh_token_expire_days))


def decode_token(token: str, expected_type: str) -> dict[str, Any]:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError as exc:
        raise ValueError("Invalid token") from exc
    if payload.get("type") != expected_type:
        raise ValueError("Invalid token type")
    return payload
