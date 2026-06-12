from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.database.mixins import SoftDeleteMixin, WorkspaceScopedMixin


class IntegrationProvider(StrEnum):
    NOVA_POSHTA = "NOVA_POSHTA"


class IntegrationStatus(StrEnum):
    DISCONNECTED = "DISCONNECTED"
    CONNECTED = "CONNECTED"
    ERROR = "ERROR"


class IntegrationConnection(UUIDPrimaryKeyMixin, WorkspaceScopedMixin, SoftDeleteMixin, TimestampMixin, Base):
    __tablename__ = "integration_connections"

    provider: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    connection_name: Mapped[str] = mapped_column(String(120), nullable=False)
    status: Mapped[str] = mapped_column(String(40), default=IntegrationStatus.DISCONNECTED.value, nullable=False)
    connected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    settings: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    credentials = relationship("IntegrationCredential", back_populates="connection", cascade="all, delete-orphan")
