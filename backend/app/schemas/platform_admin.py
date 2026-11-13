from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.platform_admin import PlatformRole
from app.models.role import RoleName
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
    archived_at: datetime | None = None


class PlatformWorkspaceDetail(PlatformWorkspace):
    currency_code: str
    timezone: str
    active_member_count: int
    archive_allowed: bool = False


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
    archived_workspaces: int


class PlatformWorkspaceListParams(BaseModel):
    model_config = ConfigDict(extra="forbid")

    active: bool | None = None
    demo: bool | None = None
    limit: int = Field(default=50, ge=1, le=100)


class PlatformWorkspaceSearchParams(PlatformWorkspaceListParams):
    q: str | None = Field(default=None, max_length=120)
    subscription_status: SubscriptionDisplayStatus | None = None
    archived: bool | None = None
    cursor: str | None = Field(default=None, min_length=1, max_length=900)


class PlatformWorkspaceRequestError(BaseModel):
    detail: str


class PlatformUserSearchParams(BaseModel):
    model_config = ConfigDict(extra="forbid")

    q: str | None = Field(default=None, max_length=255)
    cursor: str | None = Field(default=None, min_length=1, max_length=900)
    without_workspaces: bool = False
    limit: int = Field(default=20, ge=1, le=50)


class PlatformUser(BaseModel):
    id: UUID
    email: str
    first_name: str
    last_name: str
    is_active: bool
    created_at: datetime


class PlatformUserPage(BaseModel):
    items: list[PlatformUser]
    next_cursor: str | None


class PlatformUserWorkspace(BaseModel):
    id: UUID
    name: str
    slug: str
    role: RoleName
    is_active: bool
    archived_at: datetime | None


class PlatformUserDetail(PlatformUser):
    workspaces: list[PlatformUserWorkspace]
    next_cursor: str | None
