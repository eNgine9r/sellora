from typing import TypeVar
from uuid import UUID

from sqlalchemy import Select

from app.database.mixins import WorkspaceScopedMixin

WorkspaceScopedModel = TypeVar("WorkspaceScopedModel", bound=WorkspaceScopedMixin)


def apply_workspace_filter(statement: Select[tuple[WorkspaceScopedModel]], model: type[WorkspaceScopedModel], workspace_id: UUID) -> Select[tuple[WorkspaceScopedModel]]:
    """Apply mandatory workspace filtering for future tenant-owned queries."""
    return statement.where(model.workspace_id == workspace_id)
