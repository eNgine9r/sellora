from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import Date, ForeignKey, Integer, Numeric, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.database.mixins import SoftDeleteMixin, WorkspaceScopedMixin


class AdMetric(UUIDPrimaryKeyMixin, WorkspaceScopedMixin, SoftDeleteMixin, TimestampMixin, Base):
    __tablename__ = "ad_metrics"
    __table_args__ = (UniqueConstraint("campaign_id", "metric_date", name="uq_ad_metrics_campaign_id_metric_date"),)

    campaign_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("ad_campaigns.id", ondelete="CASCADE"), nullable=False, index=True)
    metric_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    spend: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    impressions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    reach: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    clicks: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    messages: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    leads: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    orders: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    revenue: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    net_profit: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, nullable=False)

    campaign = relationship("AdCampaign", back_populates="metrics")
