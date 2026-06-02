from typing import TypeVar
from uuid import UUID

from sqlalchemy import Select

from app.database.base import TenantMixin

TenantModel = TypeVar("TenantModel", bound=TenantMixin)


def apply_workspace_filter(statement: Select[tuple[TenantModel]], model: type[TenantModel], workspace_id: UUID) -> Select[tuple[TenantModel]]:
    """Apply mandatory workspace filtering for future tenant-owned queries."""
    return statement.where(model.workspace_id == workspace_id)
