from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.utils.phone import PhoneNormalizationError, normalize_ua_phone


class CustomerPhoneMixin(BaseModel):
    @field_validator("phone", mode="before", check_fields=False)
    @classmethod
    def normalize_phone(cls, value):
        try:
            return normalize_ua_phone(value)
        except PhoneNormalizationError as exc:
            raise ValueError("INVALID_UA_PHONE") from exc


class CustomerCreate(CustomerPhoneMixin):
    name: str = Field(min_length=1, max_length=255)
    phone: str | None = Field(default=None, max_length=50)
    instagram_username: str | None = Field(default=None, max_length=120)
    city: str | None = Field(default=None, max_length=120)
    region: str | None = Field(default=None, max_length=120)


class CustomerUpdate(CustomerPhoneMixin):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    phone: str | None = Field(default=None, max_length=50)
    instagram_username: str | None = Field(default=None, max_length=120)
    city: str | None = Field(default=None, max_length=120)
    region: str | None = Field(default=None, max_length=120)


class CustomerResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    name: str
    phone: str | None
    instagram_username: str | None
    city: str | None
    region: str | None
    total_orders: int
    total_spent: Decimal
    last_order_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
