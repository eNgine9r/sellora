from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.schemas.customer import CustomerResponse
from app.utils.phone import PhoneNormalizationError, normalize_ua_phone


class DirectCustomerAutomationState(BaseModel):
    conversation_id: UUID
    customer: CustomerResponse | None = None
    linked_order_id: UUID | None = None
    stage: str
    missing_fields: list[str] = Field(default_factory=list)
    can_create_order: bool = False
    profile_complete: bool = False
    created_automatically: bool = False


class DirectCustomerCompleteRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    phone: str = Field(min_length=1, max_length=50)
    city: str = Field(min_length=1, max_length=120)
    region: str | None = Field(default=None, max_length=120)
    recipient_name: str | None = Field(default=None, max_length=255)
    recipient_phone: str | None = Field(default=None, max_length=50)
    warehouse: str = Field(min_length=1, max_length=255)
    warehouse_number: str | None = Field(default=None, max_length=40)
    nova_poshta_city_ref: str = Field(min_length=1, max_length=120)
    nova_poshta_warehouse_ref: str = Field(min_length=1, max_length=120)

    @field_validator("phone", "recipient_phone", mode="before")
    @classmethod
    def normalize_phone(cls, value):
        if value in (None, ""):
            return value
        try:
            return normalize_ua_phone(value)
        except PhoneNormalizationError as exc:
            raise ValueError("INVALID_UA_PHONE") from exc
