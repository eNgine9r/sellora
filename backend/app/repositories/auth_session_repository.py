from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session


class AuthSessionRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def lock_active_refresh_digest(self, user_id: UUID, session_id: UUID) -> str | None:
        return self.db.scalar(
            text(
                "SELECT refresh_hash FROM public.auth_sessions WHERE id=:sid AND user_id=:uid "
                "AND revoked_at IS NULL AND expires_at > now() FOR UPDATE"
            ),
            {"sid": session_id, "uid": user_id},
        )
