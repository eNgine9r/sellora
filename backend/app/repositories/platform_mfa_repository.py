from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.engine import Row
from sqlalchemy.orm import Session


class PlatformMfaRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def lock_factor(self, user_id: UUID) -> Row[tuple[bytes, int, int, datetime | None]] | None:
        return self.db.execute(text("""
            SELECT encrypted_seed, last_step, failure_count, window_started_at
            FROM public.platform_operator_mfa WHERE user_id = :user_id FOR UPDATE
        """), {"user_id": user_id}).one_or_none()

    def record_failure(self, user_id: UUID, count: int, window_start: datetime) -> None:
        self.db.execute(text("""
            UPDATE public.platform_operator_mfa
            SET failure_count = :count, window_started_at = :window_start
            WHERE user_id = :user_id
        """), {"user_id": user_id, "count": count, "window_start": window_start})

    def record_success(self, user_id: UUID, step: int) -> None:
        self.db.execute(text("""
            UPDATE public.platform_operator_mfa
            SET last_step = :step, failure_count = 0, window_started_at = NULL
            WHERE user_id = :user_id
        """), {"user_id": user_id, "step": step})

    def store_proof(
        self, user_id: UUID, session_id: UUID, digest: bytes, expires_at: datetime, granted_at: datetime,
    ) -> bool:
        return self.db.execute(text("""
            UPDATE public.auth_sessions
            SET platform_mfa_digest = :digest, platform_mfa_expires_at = :expires_at
            WHERE id = :sid AND user_id = :uid AND authenticated_via = 'PASSWORD'
                AND revoked_at IS NULL AND expires_at > clock_timestamp()
                AND EXISTS (
                    SELECT 1 FROM public.platform_operator_grants
                    WHERE user_id = :uid AND granted_at = :granted_at AND revoked_at IS NULL
                )
            RETURNING id
        """), {
            "sid": session_id, "uid": user_id, "digest": digest,
            "expires_at": expires_at, "granted_at": granted_at,
        }).scalar() is not None

    def has_proof(self, user_id: UUID, session_id: UUID, digest: bytes, lifetime: timedelta) -> bool:
        return self.db.execute(text("""
            SELECT 1 FROM public.auth_sessions AS session
            JOIN public.platform_operator_grants AS operator_grant ON operator_grant.user_id = session.user_id
            WHERE session.id = :sid AND session.user_id = :uid AND session.authenticated_via = 'PASSWORD'
                AND session.revoked_at IS NULL AND session.expires_at > clock_timestamp()
                AND operator_grant.revoked_at IS NULL
                AND session.platform_mfa_digest = :digest AND session.platform_mfa_expires_at > clock_timestamp()
                AND session.platform_mfa_expires_at - :lifetime >= operator_grant.granted_at
        """), {"sid": session_id, "uid": user_id, "digest": digest, "lifetime": lifetime}).scalar() is not None

    def replace_factor(self, user_id: UUID, encrypted_seed: bytes, step: int) -> None:
        self.db.execute(text("""
            INSERT INTO public.platform_operator_mfa (user_id, encrypted_seed, last_step)
            VALUES (:uid, :seed, :step)
            ON CONFLICT (user_id) DO UPDATE
            SET encrypted_seed = EXCLUDED.encrypted_seed, last_step = EXCLUDED.last_step,
                failure_count = 0, window_started_at = NULL
        """), {"uid": user_id, "seed": encrypted_seed, "step": step})
        self.clear_proofs(user_id)

    def delete_factor(self, user_id: UUID) -> None:
        self.db.execute(text("DELETE FROM public.platform_operator_mfa WHERE user_id = :uid"), {"uid": user_id})
        self.clear_proofs(user_id)

    def clear_proofs(self, user_id: UUID) -> None:
        self.db.execute(text("""
            UPDATE public.auth_sessions
            SET platform_mfa_digest = NULL, platform_mfa_expires_at = NULL
            WHERE user_id = :uid AND platform_mfa_digest IS NOT NULL
        """), {"uid": user_id})
