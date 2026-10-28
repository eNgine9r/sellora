"""Provider documents discovered independently of Sellora sales/orders."""
from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.database.mixins import SoftDeleteMixin, WorkspaceScopedMixin


class NovaPoshtaExternalDocument(UUIDPrimaryKeyMixin, WorkspaceScopedMixin, SoftDeleteMixin, TimestampMixin, Base):
    __tablename__ = "nova_poshta_external_documents"
    __table_args__ = (
        UniqueConstraint("workspace_id", "tracking_number", name="uq_np_external_workspace_tracking"),
        Index("ix_np_external_workspace_match", "workspace_id", "match_state"),
    )

    tracking_number: Mapped[str] = mapped_column(String(32), nullable=False)
    document_ref: Mapped[str | None] = mapped_column(String(120), nullable=True)
    provider_status: Mapped[str | None] = mapped_column(String(255), nullable=True)
    match_state: Mapped[str] = mapped_column(String(20), default="UNMATCHED", nullable=False)
    matched_shipment_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("shipments.id", ondelete="SET NULL"), nullable=True
    )
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
