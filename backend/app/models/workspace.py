from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Workspace(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "workspaces"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(120), unique=True, index=True, nullable=False)
    subscription_plan: Mapped[str] = mapped_column(String(50), default="free", nullable=False)
    currency_code: Mapped[str] = mapped_column(String(3), default="UAH", server_default="UAH", nullable=False)
    timezone: Mapped[str] = mapped_column(String(80), default="Europe/Kyiv", server_default="Europe/Kyiv", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    members = relationship("WorkspaceUser", back_populates="workspace", cascade="all, delete-orphan")
