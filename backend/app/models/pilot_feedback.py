from enum import StrEnum
from uuid import UUID

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.database.mixins import SoftDeleteMixin, WorkspaceScopedMixin


class PilotFeedbackCategory(StrEnum):
    ISSUE = "ISSUE"
    IDEA = "IDEA"
    CONFUSION = "CONFUSION"
    PRAISE = "PRAISE"
    OTHER = "OTHER"


class PilotFeedbackStatus(StrEnum):
    NEW = "NEW"
    REVIEWED = "REVIEWED"
    PLANNED = "PLANNED"
    FIXED = "FIXED"
    WONT_FIX = "WONT_FIX"


class PilotFeedback(UUIDPrimaryKeyMixin, WorkspaceScopedMixin, SoftDeleteMixin, TimestampMixin, Base):
    __tablename__ = "pilot_feedback"

    user_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    rating: Mapped[int | None] = mapped_column(Integer, nullable=True)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    page_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default=PilotFeedbackStatus.NEW.value, nullable=False)
