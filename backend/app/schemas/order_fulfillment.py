from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

from app.models.order import PaymentStatus
from app.models.order_fulfillment import OrderFulfillmentResultCode
from app.schemas.order import OrderItemCreate, OrderResponse
from app.schemas.shipment import ShipmentResponse
from app.utils.phone import PhoneNormalizationError, normalize_ua_phone


class OrderFulfillmentCreate(BaseModel):
    idempotency_key: str = Field(min_length=8, max_length=100)
    customer_id: UUID | None = None
    customer_name: str | None = Field(default=None, max_length=255)
    customer_phone: str | None = Field(default=None, max_length=50)
    instagram_username: str | None = Field(default=None, max_length=120)
    address_id: UUID | None = None
    recipient_name: str = Field(min_length=1, max_length=255)
    recipient_phone: str = Field(min_length=1, max_length=50)
    nova_poshta_city_ref: str = Field(min_length=1, max_length=120)
    city: str = Field(min_length=1, max_length=120)
    nova_poshta_warehouse_ref: str = Field(min_length=1, max_length=120)
    warehouse: str = Field(min_length=1, max_length=255)
    warehouse_number: str | None = Field(default=None, max_length=40)
    save_address_as_default: bool = True
    items: list[OrderItemCreate] = Field(min_length=1)
    payment_status: PaymentStatus = PaymentStatus.PENDING
    cod_amount: Decimal | None = Field(default=None, ge=0)
    declared_value: Decimal | None = Field(default=None, ge=0)
    campaign_id: UUID | None = None
    ad_cost: Decimal = Field(default=Decimal("0"), ge=0)
    shipping_cost: Decimal = Field(default=Decimal("0"), ge=0)
    cod_fee: Decimal = Field(default=Decimal("0"), ge=0)
    other_cost: Decimal = Field(default=Decimal("0"), ge=0)
    notes: str | None = None
    create_ttn: bool = True

    @field_validator("customer_phone", "recipient_phone", mode="before")
    @classmethod
    def normalize_phone(cls, value):
        try:
            return normalize_ua_phone(value)
        except PhoneNormalizationError as exc:
            raise ValueError("INVALID_UA_PHONE") from exc

    @model_validator(mode="after")
    def validate_customer_and_payment(self):
        if self.customer_id is None and not (self.customer_name or "").strip():
            raise ValueError("CUSTOMER_NAME_REQUIRED")
        if self.payment_status == PaymentStatus.REFUNDED:
            raise ValueError("REFUNDED_PAYMENT_NOT_ALLOWED_FOR_NEW_ORDER")
        return self


class OrderFulfillmentResponse(BaseModel):
    result_code: OrderFulfillmentResultCode
    idempotency_key: str
    idempotent_replay: bool = False
    order: OrderResponse
    shipment: ShipmentResponse
    tracking_number: str | None = None
    provider_error_code: str | None = None
    retry_available: bool = False
    message: str
