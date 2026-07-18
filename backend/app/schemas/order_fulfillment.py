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

class FulfillmentRecipient(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    phone: str = Field(min_length=1, max_length=50)

    @field_validator("phone", mode="before")
    @classmethod
    def normalize_recipient_phone(cls, value):
        try:
            return normalize_ua_phone(value)
        except PhoneNormalizationError as exc:
            raise ValueError("INVALID_UA_PHONE") from exc


class FulfillmentDelivery(BaseModel):
    provider: str = Field(default="NOVA_POSHTA", min_length=1, max_length=40)
    city_ref: str = Field(min_length=1, max_length=120)
    city_description: str = Field(min_length=1, max_length=255)
    warehouse_ref: str = Field(min_length=1, max_length=120)
    warehouse_description: str = Field(min_length=1, max_length=255)
    warehouse_number: str | None = Field(default=None, max_length=40)
    service_type: str = Field(default="WAREHOUSE_WAREHOUSE", min_length=1, max_length=80)
    payer_type: str = Field(default="Recipient", min_length=1, max_length=40)
    payment_method: str = Field(default="Cash", min_length=1, max_length=40)
    declared_value: Decimal = Field(default=Decimal("0"), ge=0)
    weight: Decimal = Field(default=Decimal("1"), gt=0)
    place_count: int = Field(default=1, gt=0)
    cargo_description: str = Field(default="Товари Instagram-магазину", min_length=1, max_length=120)


class FulfillmentPayment(BaseModel):
    mode: str = Field(default="PREPAID_OR_COD", min_length=1, max_length=40)
    already_paid: Decimal = Field(default=Decimal("0"), ge=0)
    cod_amount: Decimal = Field(default=Decimal("0"), ge=0)


class FulfillmentRequest(BaseModel):
    customer_id: UUID | None = None
    address_id: UUID | None = None
    recipient: FulfillmentRecipient
    delivery: FulfillmentDelivery
    payment: FulfillmentPayment = Field(default_factory=FulfillmentPayment)

    @model_validator(mode="after")
    def validate_cod(self):
        if self.payment.cod_amount > Decimal("0") and self.payment.mode not in {"COD", "PREPAID_OR_COD"}:
            raise ValueError("COD_AMOUNT_REQUIRES_COD_PAYMENT_MODE")
        return self


class FulfillmentExecuteRequest(FulfillmentRequest):
    create_provider_document: bool = True


class FulfillmentPrepareResponse(BaseModel):
    ready: bool
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    inventory: dict
    provider_readiness: dict
    finance_preview: dict
    existing_operation: dict | None = None


class FulfillmentExecuteResponse(BaseModel):
    operation_id: UUID
    state: str
    result_code: OrderFulfillmentResultCode | None = None
    reused: bool = False
    shipment_id: UUID | None = None
    tracking_number: str | None = None
    document_ref: str | None = None
    manual_reconciliation_required: bool = False
    blind_retry_blocked: bool = False
    inventory_reserved: bool = False
    reservation_verified: bool = False
    retry_available: bool = False
    safe_message: str


class FulfillmentStatusResponse(BaseModel):
    operation_id: UUID | None = None
    state: str | None = None
    result_code: OrderFulfillmentResultCode | None = None
    shipment_id: UUID | None = None
    tracking_number: str | None = None
    document_ref: str | None = None
    manual_reconciliation_required: bool = False
    blind_retry_blocked: bool = False
    last_error_code: str | None = None
    last_error_message: str | None = None
