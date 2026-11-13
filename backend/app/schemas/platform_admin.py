from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.platform_admin import PlatformRole
from app.schemas.subscription import SubscriptionDisplayStatus, SubscriptionStatusResponse


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


class PlatformWorkspaceListParams(BaseModel):
    model_config = ConfigDict(extra="forbid")

    active: bool | None = None
    demo: bool | None = None
    limit: int = Field(default=50, ge=1, le=100)


class PlatformWorkspaceSearchParams(PlatformWorkspaceListParams):
    q: str | None = Field(default=None, max_length=120)
    subscription_status: SubscriptionDisplayStatus | None = None
    cursor: str | None = Field(default=None, min_length=1, max_length=900)


class PlatformWorkspaceRequestError(BaseModel):
    detail: str
