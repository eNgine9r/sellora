from datetime import date
from decimal import Decimal
from enum import StrEnum

from sqlalchemy import Date, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.database.mixins import SoftDeleteMixin, WorkspaceScopedMixin


class AdCampaignPlatform(StrEnum):
    META = "META"
    INSTAGRAM = "INSTAGRAM"
    FACEBOOK = "FACEBOOK"
    TIKTOK = "TIKTOK"
    GOOGLE = "GOOGLE"
    TELEGRAM = "TELEGRAM"
    OTHER = "OTHER"


class AdCampaignStatus(StrEnum):
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"
    ARCHIVED = "ARCHIVED"


class AdCampaignObjective(StrEnum):
    MESSAGES = "MESSAGES"
    SALES = "SALES"
    TRAFFIC = "TRAFFIC"
    AWARENESS = "AWARENESS"
    FOLLOWERS = "FOLLOWERS"
    OTHER = "OTHER"


class AdCampaignBudgetType(StrEnum):
    DAILY = "DAILY"
    LIFETIME = "LIFETIME"
    MANUAL = "MANUAL"


class AdCampaign(UUIDPrimaryKeyMixin, WorkspaceScopedMixin, SoftDeleteMixin, TimestampMixin, Base):
    __tablename__ = "ad_campaigns"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    platform: Mapped[str] = mapped_column(String(30), default=AdCampaignPlatform.INSTAGRAM.value, nullable=False)
    status: Mapped[str] = mapped_column(String(30), default=AdCampaignStatus.ACTIVE.value, nullable=False)
    objective: Mapped[str] = mapped_column(String(30), default=AdCampaignObjective.MESSAGES.value, nullable=False)
    budget_type: Mapped[str] = mapped_column(String(30), default=AdCampaignBudgetType.MANUAL.value, nullable=False)
    daily_budget: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    total_budget: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    metrics = relationship("AdMetric", back_populates="campaign", cascade="all, delete-orphan")
