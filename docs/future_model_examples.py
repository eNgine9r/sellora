"""Illustrative future model usage for Sellora database mixins.

These examples are intentionally not imported by Alembic or the application and
must not be treated as Sprint 1.1 business module implementations.
"""

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.database.mixins import SoftDeleteMixin, WorkspaceScopedMixin


class FutureWorkspaceEntity(UUIDPrimaryKeyMixin, WorkspaceScopedMixin, SoftDeleteMixin, TimestampMixin, Base):
    """Example shape for future CRM entities such as leads or orders."""

    __abstract__ = True

    name: Mapped[str] = mapped_column(String(255), nullable=False)


# Example future concrete model, shown as comments to avoid implementing a
# business module in this bootstrap sprint:
#
# class Lead(UUIDPrimaryKeyMixin, WorkspaceScopedMixin, SoftDeleteMixin, TimestampMixin, Base):
#     __tablename__ = "leads"
#
#     name: Mapped[str] = mapped_column(String(255), nullable=False)
