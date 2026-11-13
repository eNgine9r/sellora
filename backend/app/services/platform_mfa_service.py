import hmac
import re
import secrets
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from uuid import UUID

from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.platform_admin import PlatformAuditEvent, PlatformRole
from app.repositories.platform_admin_repository import PlatformAuditRepository
from app.repositories.platform_mfa_repository import PlatformMfaRepository

MFA_HEADER = "X-Sellora-Platform-MFA"
PROOF_LIFETIME = timedelta(minutes=30)
ATTEMPT_WINDOW = timedelta(minutes=5)
MAX_FAILURES = 5
_CODE_PATTERN = re.compile(r"[0-9]{6}")
_PROOF_PATTERN = re.compile(r"[A-Za-z0-9_-]{43}")


class PlatformMfaError(Exception):
    def __init__(self, code: str, status_code: int) -> None:
        self.code = code
        self.status_code = status_code


def platform_mfa_cipher() -> Fernet:
    key = get_settings().platform_admin_mfa_key
    try:
        return Fernet(key.get_secret_value() if key else "")
    except (ValueError, TypeError):
        raise PlatformMfaError("PLATFORM_MFA_UNAVAILABLE", 503) from None


def totp_code(seed: bytes, step: int) -> str:
    digest = hmac.digest(seed, step.to_bytes(8, "big"), "sha1")
    offset = digest[-1] & 0x0F
    number = int.from_bytes(digest[offset:offset + 4], "big") & 0x7FFFFFFF
    return f"{number % 1_000_000:06d}"


def matching_step(seed: bytes, code: str, now: datetime, *, after: int = -1) -> int | None:
    if not _CODE_PATTERN.fullmatch(code):
        return None
    step = int(now.timestamp()) // 30
    for candidate in (step, step - 1, step + 1):
        if candidate > after and hmac.compare_digest(totp_code(seed, candidate), code):
            return candidate
    return None


class PlatformMfaService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = PlatformMfaRepository(db)

    def check(self, user_id: UUID, session_id: UUID, proof: str | None) -> None:
        platform_mfa_cipher()
        if not proof or not _PROOF_PATTERN.fullmatch(proof):
            raise PlatformMfaError("PLATFORM_MFA_REQUIRED", 403)
        if not self.repository.has_proof(user_id, session_id, sha256(proof.encode()).digest(), PROOF_LIFETIME):
            raise PlatformMfaError("PLATFORM_MFA_REQUIRED", 403)

    def verify(
        self, user_id: UUID, role: PlatformRole, session_id: UUID, granted_at: datetime, code: str,
    ) -> str:
        cipher = platform_mfa_cipher()
        factor = self.repository.lock_factor(user_id)
        if factor is None:
            raise PlatformMfaError("PLATFORM_MFA_NOT_ENROLLED", 403)

        now = datetime.now(UTC)
        window_start = factor.window_started_at
        count = factor.failure_count
        if window_start is None or now >= window_start + ATTEMPT_WINDOW:
            window_start = now
            count = 0
        if count >= MAX_FAILURES:
            raise PlatformMfaError("PLATFORM_MFA_RATE_LIMITED", 429)

        try:
            seed = cipher.decrypt(factor.encrypted_seed)
        except InvalidToken:
            raise PlatformMfaError("PLATFORM_MFA_UNAVAILABLE", 503) from None

        step = matching_step(seed, code, now, after=factor.last_step)
        if step is None:
            self.repository.record_failure(user_id, count + 1, window_start)
            self.db.commit()
            raise PlatformMfaError("PLATFORM_MFA_INVALID_CODE", 403)

        proof = secrets.token_urlsafe(32)
        if not self.repository.store_proof(
            user_id, session_id, sha256(proof.encode()).digest(), now + PROOF_LIFETIME, granted_at,
        ):
            raise PlatformMfaError("PLATFORM_MFA_INVALID_SESSION", 401)
        self.repository.record_success(user_id, step)
        PlatformAuditRepository(self.db).add(PlatformAuditEvent(
            actor_user_id=user_id, actor_role=role, action="VERIFY_PLATFORM_MFA", outcome="ALLOWED",
        ))
        self.db.commit()
        return proof
