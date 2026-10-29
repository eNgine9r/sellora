from datetime import datetime
from enum import Enum
from typing import Literal
from uuid import UUID

from pydantic import BaseModel


class SubscriptionDisplayStatus(str, Enum):
    UNMANAGED = "UNMANAGED"
    PENDING = "PENDING"
    TRIALING = "TRIALING"
    ACTIVE = "ACTIVE"
    PAST_DUE = "PAST_DUE"
    CANCELED = "CANCELED"
    EXPIRED = "EXPIRED"


class SubscriptionStatusResponse(BaseModel):
    workspace_id: UUID
    status: SubscriptionDisplayStatus
    plan_code: str | None = None
    current_period_start: datetime | None = None
    current_period_end: datetime | None = None
    cancel_at_period_end: bool = False
    has_current_term: bool = False
    # This package observes terms; it does not change existing CRM authorization.
    enforcement_enabled: Literal[False] = False
