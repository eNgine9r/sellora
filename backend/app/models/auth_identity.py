from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, SmallInteger, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class AuthIdentity(Base):
    __tablename__ = "auth_identities"
    __table_args__ = (UniqueConstraint("user_id", "provider"),)

    provider: Mapped[str] = mapped_column(String(16), primary_key=True)
    subject: Mapped[str] = mapped_column(String(255), primary_key=True)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)


class AuthEmailChallenge(Base):
    __tablename__ = "auth_email_challenges"

    email_key: Mapped[str] = mapped_column(String(64), primary_key=True)
    digest: Mapped[str | None] = mapped_column(String(64))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    window_ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    resend_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    sends: Mapped[int] = mapped_column(SmallInteger)
    attempts: Mapped[int] = mapped_column(SmallInteger)
