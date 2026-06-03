from uuid import UUID

from sqlalchemy import ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.database.mixins import SoftDeleteMixin, WorkspaceScopedMixin


class CustomerNote(UUIDPrimaryKeyMixin, WorkspaceScopedMixin, SoftDeleteMixin, TimestampMixin, Base):
    __tablename__ = "customer_notes"

    customer_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("customers.id", ondelete="CASCADE"), nullable=False)
    note: Mapped[str] = mapped_column(Text, nullable=False)
    created_by: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    customer = relationship("Customer", back_populates="notes")
