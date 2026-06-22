from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.shipment import ShipmentCarrier, ShipmentStatus


class ShipmentBase(BaseModel):
    tracking_number: str | None = None
    carrier: ShipmentCarrier = ShipmentCarrier.NOVA_POSHTA
    status: ShipmentStatus = ShipmentStatus.DRAFT
    recipient_name: str | None = None
    recipient_phone: str | None = None
    city: str | None = None
    warehouse: str | None = None
    shipping_cost: Decimal | None = Field(default=None, ge=0)
    cod_amount: Decimal | None = Field(default=None, ge=0)
    declared_value: Decimal | None = Field(default=None, ge=0)
    notes: str | None = None
    nova_poshta_city_ref: str | None = None
    nova_poshta_warehouse_ref: str | None = None

    @model_validator(mode="after")
    def tracking_required_for_non_draft(self):
        if self.status != ShipmentStatus.DRAFT and not self.tracking_number:
            raise ValueError("tracking_number is required for non-draft shipments")
        return self


class ShipmentCreate(ShipmentBase):
    order_id: UUID
    customer_id: UUID | None = None


class ShipmentUpdate(BaseModel):
    tracking_number: str | None = None
    carrier: ShipmentCarrier | None = None
    status: ShipmentStatus | None = None
    customer_id: UUID | None = None
    recipient_name: str | None = None
    recipient_phone: str | None = None
    city: str | None = None
    warehouse: str | None = None
    shipping_cost: Decimal | None = Field(default=None, ge=0)
    cod_amount: Decimal | None = Field(default=None, ge=0)
    declared_value: Decimal | None = Field(default=None, ge=0)
    notes: str | None = None
    nova_poshta_city_ref: str | None = None
    nova_poshta_warehouse_ref: str | None = None


class ShipmentStatusUpdate(BaseModel):
    status: ShipmentStatus


class ShipmentResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    order_id: UUID
    customer_id: UUID | None
    tracking_number: str | None
    carrier: ShipmentCarrier
    status: ShipmentStatus
    recipient_name: str | None
    recipient_phone: str | None
    city: str | None
    warehouse: str | None
    shipping_cost: Decimal | None
    cod_amount: Decimal | None
    declared_value: Decimal | None
    notes: str | None
    shipped_at: datetime | None
    delivered_at: datetime | None
    returned_at: datetime | None
    external_provider: str | None
    external_ref: str | None
    external_status: str | None
    nova_poshta_city_ref: str | None
    nova_poshta_warehouse_ref: str | None
    nova_poshta_document_ref: str | None
    nova_poshta_document_number: str | None
    nova_poshta_raw_status: str | None
    nova_poshta_synced_at: datetime | None
    order_number: str | None = None
    order_status: str | None = None
    order_payment_status: str | None = None
    order_total: Decimal | None = None
    customer_name: str | None = None
    customer_phone: str | None = None
    customer_instagram_username: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ShipmentSummaryResponse(BaseModel):
    in_transit_count: int
    arrived_count: int
    delivered_today: int
    returned_this_month: int
