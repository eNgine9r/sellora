from __future__ import annotations

from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.role import RoleName


class OnboardingNextAction(StrEnum):
    CONFIGURE_WORKSPACE = "CONFIGURE_WORKSPACE"
    ADD_PRODUCT = "ADD_PRODUCT"
    ADD_STOCK = "ADD_STOCK"
    ADD_LEAD_OR_CUSTOMER = "ADD_LEAD_OR_CUSTOMER"
    CREATE_ORDER = "CREATE_ORDER"
    EXPLORE_DASHBOARD = "EXPLORE_DASHBOARD"


class OnboardingSteps(BaseModel):
    workspace_configured: bool
    product_created: bool
    stock_added: bool
    lead_or_customer_created: bool
    order_created: bool


class OnboardingStatusResponse(BaseModel):
    workspace_id: UUID
    role: RoleName
    is_demo_workspace: bool = False
    is_empty: bool
    progress_percent: int
    completed_steps: int
    total_steps: int
    steps: OnboardingSteps
    suggested_next_action: OnboardingNextAction

    model_config = ConfigDict(from_attributes=True)
