from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy import case, delete, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models.auth_identity import AuthEmailChallenge, AuthIdentity


class AuthIdentityRepository:
    def __init__(self, db: Session):
        self.db = db

    def owner(self, provider: str, subject: str) -> UUID | None:
        return self.db.scalar(
            select(AuthIdentity.user_id).where(AuthIdentity.provider == provider, AuthIdentity.subject == subject)
        )

    def providers(self, user_id: UUID) -> list[str]:
        return list(self.db.scalars(select(AuthIdentity.provider).where(AuthIdentity.user_id == user_id)))

    def add(self, user_id: UUID, provider: str, subject: str) -> None:
        self.db.add(AuthIdentity(user_id=user_id, provider=provider, subject=subject))


class AuthEmailRepository:
    def __init__(self, db: Session):
        self.db = db

    def reserve(self, key: str, digest: str, now: datetime) -> bool:
        table = AuthEmailChallenge
        # Bound cleanup work and skip rows currently being verified.
        expired = (
            select(table.email_key).where(table.window_ends_at < now - timedelta(hours=1))
            .order_by(table.window_ends_at).limit(25).with_for_update(skip_locked=True)
        )
        self.db.execute(delete(table).where(table.email_key.in_(expired)))
        expiry = now + timedelta(minutes=10)
        window = now + timedelta(hours=1)
        resend = now + timedelta(minutes=1)
        reset = table.window_ends_at <= now
        statement = insert(table).values(
            email_key=key, digest=digest, expires_at=expiry, window_ends_at=window,
            resend_at=resend, sends=1, attempts=0,
        ).on_conflict_do_update(
            index_elements=[table.email_key],
            set_={
                "digest": digest, "expires_at": expiry, "resend_at": resend,
                "window_ends_at": case((reset, window), else_=table.window_ends_at),
                "sends": case((reset, 1), else_=table.sends + 1),
                "attempts": 0,
            },
            where=(table.resend_at <= now) & (reset | (table.sends < 5)),
        ).returning(table.email_key)
        reserved = self.db.scalar(statement) is not None
        self.db.commit()
        return reserved

    def clear_failed_delivery(self, key: str, digest: str, now: datetime) -> None:
        table = AuthEmailChallenge
        self.db.execute(update(table).where(table.email_key == key, table.digest == digest).values(
            digest=None, resend_at=now,
        ))
        self.db.commit()

    def lock(self, key: str) -> AuthEmailChallenge | None:
        return self.db.scalar(select(AuthEmailChallenge).where(AuthEmailChallenge.email_key == key).with_for_update())
