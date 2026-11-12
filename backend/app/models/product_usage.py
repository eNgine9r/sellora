from datetime import date, datetime
from enum import StrEnum
from uuid import UUID

from sqlalchemy import BigInteger, Date, DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, UUIDPrimaryKeyMixin


class UsageEvent(StrEnum):
    WORKSPACE_ACTIVATED = "workspace.activated"
    FIRST_PRODUCT = "product.first_created"
    FIRST_ORDER = "order.first_created"
    ORDER_CREATED = "order.created"
    INTEGRATION_USED = "integration.used"


class UsageSource(StrEnum):
    WORKSPACE = "WORKSPACE"
    CATALOG = "CATALOG"
    ORDERS = "ORDERS"
    NOVA_POSHTA = "NOVA_POSHTA"
    META_ADS = "META_ADS"
    INSTAGRAM = "INSTAGRAM"


DROPPED_EVENTS = "capture.dropped"


class ProductUsageEvent(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "product_usage_events"
    __table_args__ = (UniqueConstraint("workspace_id", "event_type", "source_key", name="uq_product_usage_event_source"),)

    workspace_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False)
    event_type: Mapped[str] = mapped_column(String(32), nullable=False)
    schema_version: Mapped[int] = mapped_column(default=1, nullable=False)
    source: Mapped[str] = mapped_column(String(16), nullable=False)
    source_key: Mapped[str] = mapped_column(String(40), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class ProductUsageDaily(Base):
    __tablename__ = "product_usage_daily"

    workspace_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), primary_key=True)
    day: Mapped[date] = mapped_column(Date, primary_key=True)
    event_type: Mapped[str] = mapped_column(String(32), primary_key=True)
    event_count: Mapped[int] = mapped_column(BigInteger, nullable=False)
