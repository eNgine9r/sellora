"""Durable, auditable, tenant-scoped relationship between Direct, shipment and order.

An order can be evidenced in multiple conversations; a conversation may have
multiple independently evidenced shipments/orders. No order finances are changed.
"""
from uuid import UUID

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.database.mixins import SoftDeleteMixin, WorkspaceScopedMixin


class DirectOrderShipmentLink(
    UUIDPrimaryKeyMixin, WorkspaceScopedMixin, SoftDeleteMixin, TimestampMixin, Base
):
    __tablename__ = "direct_order_shipment_links"
    __table_args__ = (
        UniqueConstraint(
            "workspace_id", "conversation_id", "shipment_id",
            name="uq_direct_order_shipment_links_workspace_conversation_shipment",
        ),
    )

    conversation_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("direct_conversations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    order_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True
    )
    shipment_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("shipments.id", ondelete="CASCADE"), nullable=False, index=True
    )
    source_message_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("direct_messages.id", ondelete="SET NULL"), nullable=True
    )
    evidence_type: Mapped[str] = mapped_column(String(40), nullable=False, default="EXACT_SHIPMENT_TTN")
    created_by: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )