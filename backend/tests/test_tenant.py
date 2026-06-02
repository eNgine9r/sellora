from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from app.database.base import TenantMixin


class TestBase(DeclarativeBase):
    pass


class TenantOwnedExample(TenantMixin, TestBase):
    __tablename__ = "tenant_owned_examples"

    id: Mapped[int] = mapped_column(primary_key=True)


def test_tenant_mixin_adds_workspace_id_column_for_future_entities() -> None:
    workspace_id_column = TenantOwnedExample.__table__.columns["workspace_id"]

    assert isinstance(workspace_id_column.type, PG_UUID)
    assert not workspace_id_column.nullable
    assert workspace_id_column.index
    assert workspace_id_column.foreign_keys
