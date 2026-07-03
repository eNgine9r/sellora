from datetime import datetime
from enum import StrEnum
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.database.mixins import SoftDeleteMixin, WorkspaceScopedMixin


class MetaAdConnectionStatus(StrEnum):
    NOT_CONNECTED = "NOT_CONNECTED"
    MOCK_ONLY = "MOCK_ONLY"
    CONNECTING = "CONNECTING"
    CONNECTED = "CONNECTED"
    NEEDS_REAUTH = "NEEDS_REAUTH"
    PERMISSION_MISSING = "PERMISSION_MISSING"
    TOKEN_EXPIRED = "TOKEN_EXPIRED"
    DISCONNECTED = "DISCONNECTED"
    ERROR = "ERROR"


class MetaAdConnection(UUIDPrimaryKeyMixin, WorkspaceScopedMixin, SoftDeleteMixin, TimestampMixin, Base):
    __tablename__ = "meta_ad_connections"

    provider: Mapped[str] = mapped_column(String(40), default="meta_ads", nullable=False, index=True)
    connection_status: Mapped[str] = mapped_column(String(40), default=MetaAdConnectionStatus.NOT_CONNECTED.value, nullable=False, index=True)
    external_business_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    external_ad_account_id: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    account_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    currency: Mapped[str | None] = mapped_column(String(12), nullable=True)
    timezone: Mapped[str | None] = mapped_column(String(80), nullable=True)
    encrypted_access_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    token_fingerprint: Mapped[str | None] = mapped_column(String(64), nullable=True)
    token_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    scopes: Mapped[str | None] = mapped_column(Text, nullable=True)
    connected_by_user_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    connected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    disconnected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    last_error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
