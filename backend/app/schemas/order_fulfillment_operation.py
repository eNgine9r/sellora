from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.order_fulfillment_operation import OrderFulfillmentOperationState
from app.models.shipment import ShipmentCarrier
from app.utils.phone import PhoneNormalizationError, normalize_ua_phone


class FulfillmentRecipient(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    phone: str = Field(min_length=1, max_length=50)

    @field_validator("phone", mode="before")
    @classmethod
    def normalize_phone(cls, value):
        try:
            return normalize_ua_phone(value)
        except PhoneNormalizationError as exc:
            raise ValueError("INVALID_UA_PHONE") from exc


class FulfillmentDelivery(BaseModel):
    provider: ShipmentCarrier = ShipmentCarrier.NOVA_POSHTA
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
    state: OrderFulfillmentOperationState
    reused: bool = False
    shipment_id: UUID | None = None
    tracking_number: str | None = None
    document_ref: str | None = None
    manual_reconciliation_required: bool = False
    blind_retry_blocked: bool = False
    inventory_reserved: bool = False
    safe_message: str


class FulfillmentStatusResponse(BaseModel):
    operation_id: UUID | None = None
    state: OrderFulfillmentOperationState | None = None
    shipment_id: UUID | None = None
    tracking_number: str | None = None
    document_ref: str | None = None
    manual_reconciliation_required: bool = False
    blind_retry_blocked: bool = False
    safe_error_code: str | None = None
    safe_error_message: str | None = None

    model_config = ConfigDict(from_attributes=True)
