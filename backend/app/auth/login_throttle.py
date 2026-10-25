"""PostgreSQL-backed login throttle, keyed by HMAC instead of stored email.

The frontend currently uses stateless JWT refresh tokens. This throttle addresses
online password guessing without changing or revoking any existing session.
Rate-limiting behind a feature flag permits an isolated canary before rollout.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from hashlib import sha256
import hmac
import math

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import get_settings


class LoginThrottled(Exception):
    def __init__(self, retry_after_seconds: int):
        self.retry_after_seconds = max(1, retry_after_seconds)
        super().__init__("Login temporarily rate limited")


class LoginThrottle:
    """Count consecutive failed logins to a normalized account identifier.

    Identifiers are HMAC-hashed before any DB write. The shared Postgres table
    makes the counter survive container restarts and multiple API workers.
    This is NOT a substitute for a future trusted-client-IP limiter.
    """

    def __init__(self, db: Session) -> None:
        self.db = db
        self.settings = get_settings()

    def _key(self, email: str) -> str:
        normalized = email.strip().casefold()
        return hmac.new(
            self.settings.jwt_secret.encode("utf-8"),
            ("sellora-login:" + normalized).encode("utf-8"),
            sha256,
        ).hexdigest()

    def check(self, email: str) -> None:
        if not self.settings.login_rate_limit_enabled:
            return
        now = datetime.now(UTC)
        row = self.db.execute(
            text(
                "SELECT failure_count, reset_at FROM public.auth_login_attempts "
                "WHERE identity_hash=:key"
            ),
            {"key": self._key(email)},
        ).first()
        if row and row.reset_at > now and row.failure_count >= self.settings.login_rate_limit_max_failures:
            raise LoginThrottled(math.ceil((row.reset_at - now).total_seconds()))

    def failed(self, email: str) -> None:
        if not self.settings.login_rate_limit_enabled:
            return
        now = datetime.now(UTC)
        expiry = now + timedelta(seconds=self.settings.login_rate_limit_window_seconds)
        self.db.execute(
            text(
                """
                INSERT INTO public.auth_login_attempts (identity_hash, failure_count, reset_at)
                VALUES (:key, 1, :expiry)
                ON CONFLICT (identity_hash) DO UPDATE SET
                    failure_count = CASE
                        WHEN auth_login_attempts.reset_at <= :now THEN 1
                        ELSE auth_login_attempts.failure_count + 1
                    END,
                    reset_at = CASE
                        WHEN auth_login_attempts.reset_at <= :now THEN :expiry
                        ELSE auth_login_attempts.reset_at
                    END
                """
            ),
            {"key": self._key(email), "now": now, "expiry": expiry},
        )
        self.db.commit()

    def succeeded(self, email: str) -> None:
        if not self.settings.login_rate_limit_enabled:
            return
        self.db.execute(
            text("DELETE FROM public.auth_login_attempts WHERE identity_hash=:key"),
            {"key": self._key(email)},
        )
        self.db.commit()
