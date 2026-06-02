from datetime import datetime

from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.database.mixins import SoftDeleteMixin, WorkspaceScopedMixin


class TestBase(DeclarativeBase):
    pass


class TenantOwnedExample(WorkspaceScopedMixin, SoftDeleteMixin, TestBase):
    __tablename__ = "tenant_owned_examples"

    id: Mapped[int] = mapped_column(primary_key=True)


def test_workspace_scoped_mixin_adds_indexed_workspace_id_column_for_future_entities() -> None:
    workspace_id_column = TenantOwnedExample.__table__.columns["workspace_id"]

    assert isinstance(workspace_id_column.type, PG_UUID)
    assert not workspace_id_column.nullable
    assert workspace_id_column.index
    assert workspace_id_column.foreign_keys


def test_soft_delete_mixin_adds_nullable_delete_metadata() -> None:
    deleted_at_column = TenantOwnedExample.__table__.columns["deleted_at"]
    deleted_by_column = TenantOwnedExample.__table__.columns["deleted_by"]

    assert deleted_at_column.nullable
    assert deleted_at_column.type.python_type is datetime
    assert deleted_by_column.nullable
    assert isinstance(deleted_by_column.type, PG_UUID)
    assert deleted_by_column.foreign_keys
