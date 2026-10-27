"""Opaque refresh cookies with Postgres-serialized rotation and server revocation.

Only a keyed digest of the random refresh credential is stored. A stolen old
credential cannot be refreshed after rotation. A replay revokes that session.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
import hashlib
import hmac
import re
import secrets
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.auth.jwt import create_access_token
from app.core.config import get_settings
from app.repositories.user_repository import UserRepository


@dataclass(frozen=True)
class SessionTokens:
    access_token: str
    refresh_cookie: str
    max_age_seconds: int


class ConcurrentSessionRefresh(Exception):
    """A different tab rotated the cookie very recently; retry once."""


class SessionAuthenticationService:
    def __init__(self, db: Session):
        self.db = db
        self.settings = get_settings()

    def _hash(self, credential: str) -> str:
        return hmac.new(
            self.settings.jwt_secret.encode("utf-8"),
            ("sellora-session-v1:" + credential).encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

    @staticmethod
    def _parts(cookie: str | None) -> tuple[UUID, str] | None:
        if not cookie or len(cookie) > 160:
            return None
        try:
            raw_id, secret = cookie.split(".", 1)
            session_id = UUID(hex=raw_id)
        except (ValueError, AttributeError):
            return None
        if len(raw_id) != 32 or not re.fullmatch(r"[A-Za-z0-9_-]{50,100}", secret):
            return None
        return session_id, secret

    def _mint(self, user_id: UUID, session_id: UUID, expires_at: datetime) -> SessionTokens:
        secret = secrets.token_urlsafe(48)
        cookie = f"{session_id.hex}.{secret}"
        remaining = max(1, int((expires_at - datetime.now(UTC)).total_seconds()))
        return SessionTokens(create_access_token(user_id, session_id=session_id), cookie, remaining)

    def create(self, user_id: UUID) -> SessionTokens:
        now = datetime.now(UTC)
        expires_at = now + timedelta(days=self.settings.refresh_token_expire_days)
        session_id = uuid4()
        issued = self._mint(user_id, session_id, expires_at)
        self.db.execute(
            text(
                "INSERT INTO public.auth_sessions "
                "(id,user_id,refresh_hash,created_at,last_used_at,expires_at,rotation_count) "
                "VALUES (:sid,:uid,:digest,:now,:now,:expires,0)"
            ),
            {
                "sid": session_id, "uid": user_id,
                "digest": self._hash(issued.refresh_cookie),
                "now": now, "expires": expires_at,
            },
        )
        self.db.commit()
        return issued

    def rotate(self, cookie: str | None) -> SessionTokens | None:
        parts = self._parts(cookie)
        if parts is None:
            return None
        session_id, _ = parts
        now = datetime.now(UTC)
        # FOR UPDATE makes token consumption atomic, even with multiple workers.
        row = self.db.execute(
            text(
                "SELECT user_id,refresh_hash,previous_refresh_hash,rotated_at,expires_at,revoked_at FROM public.auth_sessions "
                "WHERE id=:sid FOR UPDATE"
            ),
            {"sid": session_id},
        ).mappings().first()
        if row is None:
            self.db.rollback()
            return None
        if row["revoked_at"] is not None or row["expires_at"] <= now:
            self.db.rollback()
            return None
        if not hmac.compare_digest(row["refresh_hash"], self._hash(cookie)):
            # Concurrent requests from multiple tabs can use an old cookie
            # before the first response updates the browser cookie jar.
            # Allow a short, non-issuing retry window for the previous secret.
            previous = row["previous_refresh_hash"]
            rotated = row["rotated_at"]
            if (
                previous is not None
                and rotated is not None
                and hmac.compare_digest(previous, self._hash(cookie))
                and timedelta(0) <= now - rotated <= timedelta(seconds=10)
            ):
                self.db.rollback()
                raise ConcurrentSessionRefresh()
            # Replay outside the short concurrency window revokes only
            # this session, never other sessions or Instagram credentials.
            self.db.execute(
                text("UPDATE public.auth_sessions SET revoked_at=:now WHERE id=:sid"),
                {"sid": session_id, "now": now},
            )
            self.db.commit()
            return None
        user = UserRepository(self.db).get_by_id(row["user_id"])
        if user is None or not user.is_active:
            self.db.execute(
                text("UPDATE public.auth_sessions SET revoked_at=:now WHERE id=:sid"),
                {"sid": session_id, "now": now},
            )
            self.db.commit()
            return None
        issued = self._mint(row["user_id"], session_id, row["expires_at"])
        self.db.execute(
            text(
                "UPDATE public.auth_sessions SET previous_refresh_hash=refresh_hash,rotated_at=:now, "
                "refresh_hash=:digest,last_used_at=:now,rotation_count=rotation_count+1 "
                "WHERE id=:sid"
            ),
            {"digest": self._hash(issued.refresh_cookie), "now": now, "sid": session_id},
        )
        self.db.commit()
        return issued

    def revoke(self, cookie: str | None) -> None:
        parts = self._parts(cookie)
        if parts is None:
            return
        session_id, _ = parts
        now = datetime.now(UTC)
        self.db.execute(
            text(
                "UPDATE public.auth_sessions SET revoked_at=:now WHERE id=:sid "
                "AND revoked_at IS NULL AND refresh_hash=:digest"
            ),
            {"now": now, "sid": session_id, "digest": self._hash(cookie)},
        )
        self.db.commit()

    def revoke_all(self, user_id: UUID) -> None:
        self.db.execute(
            text("UPDATE public.auth_sessions SET revoked_at=:now WHERE user_id=:uid AND revoked_at IS NULL"),
            {"now": datetime.now(UTC), "uid": user_id},
        )
        self.db.commit()
