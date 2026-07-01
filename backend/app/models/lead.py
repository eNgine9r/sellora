from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.database.mixins import SoftDeleteMixin, WorkspaceScopedMixin


class LeadStatus(StrEnum):
    NEW = "NEW"
    IN_PROGRESS = "IN_PROGRESS"
    QUALIFIED = "QUALIFIED"
    CONVERTED = "CONVERTED"
    LOST = "LOST"


class Lead(UUIDPrimaryKeyMixin, WorkspaceScopedMixin, SoftDeleteMixin, TimestampMixin, Base):
    __tablename__ = "leads"

    instagram_username: Mapped[str | None] = mapped_column(String(120), nullable=True)
    instagram_profile_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    lead_source_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("lead_sources.id", ondelete="SET NULL"), nullable=True)
    campaign_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("ad_campaigns.id", ondelete="SET NULL"), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(30), default=LeadStatus.NEW.value, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    assigned_user_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    expected_revenue: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    loss_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    first_contact_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_contact_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    lead_source = relationship("LeadSource", back_populates="leads")
    campaign = relationship("AdCampaign")

    @property
    def campaign_name(self) -> str | None:
        return self.campaign.name if self.campaign else None
    assigned_user = relationship("User", foreign_keys=[assigned_user_id])
