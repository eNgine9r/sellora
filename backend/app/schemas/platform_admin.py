from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.models.platform_admin import PlatformRole
from app.schemas.subscription import SubscriptionStatusResponse


class PlatformIdentity(BaseModel):
    operator_id: UUID
    role: PlatformRole
    capabilities: list[str]


class PlatformWorkspace(BaseModel):
    id: UUID
    name: str
    slug: str
    is_active: bool
    is_demo: bool
    created_at: datetime
    subscription: SubscriptionStatusResponse


class PlatformWorkspaceDetail(PlatformWorkspace):
    currency_code: str
    timezone: str
    active_member_count: int


class PlatformWorkspacePage(BaseModel):
    items: list[PlatformWorkspace]
    next_cursor: str | None
    as_of: datetime


class PlatformSummary(BaseModel):
    as_of: datetime
    total_workspaces: int
    enabled_workspaces: int
    demo_workspaces: int
    workspaces_with_current_term: int
