"""Reviewable external-TTN sale proposals. A TTN alone is NOT sales evidence."""
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class SmartSaleSuggestion(BaseModel):
    variant_id: UUID
    sku: str
    product_name: str
    quantity: int = Field(gt=0)
    suggested_unit_price: Decimal = Field(gt=0, decimal_places=2)
    available_quantity: int | None = None
    price_source: Literal["CATALOG_SUGGESTION"] = "CATALOG_SUGGESTION"


class SmartSalePriceHint(BaseModel):
    # Manager-authored quote; never bank-confirmed or final negotiated price.
    unit_price: Decimal = Field(gt=0, decimal_places=2)
    message_id: UUID


class SmartSaleCandidate(BaseModel):
    document_id: UUID
    tracking_masked: str
    provider_status: str | None
    state: Literal["READY_FOR_REVIEW", "NEEDS_INFO", "CONFIRMED"]
    conversation_id: UUID | None = None
    customer_id: UUID | None = None
    customer_instagram: str | None = None
    suggested_item: SmartSaleSuggestion | None = None
    price_hints: list[SmartSalePriceHint] = Field(default_factory=list, max_length=4)
    reason: str
    order_id: UUID | None = None


class SmartSaleConfirmRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expected_conversation_id: UUID
    product_variant_id: UUID
    selection_source: Literal["CATALOG_SUGGESTION", "MANAGER_SELECTED"] = "CATALOG_SUGGESTION"
    quantity: int = Field(gt=0, le=100)
    unit_price: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    # The sole explicit click is a legally meaningful human attestation.
    receipt_checked_in_direct: Literal[True]
    funds_received_in_bank: Literal[True]
    details_reviewed: Literal[True]

    @model_validator(mode="after")
    def supported_total(self):
        if self.unit_price * self.quantity > Decimal("9999999999.99"):
            raise ValueError("Order total outside supported range")
        return self


class SmartSaleConfirmResult(BaseModel):
    document_id: UUID
    order_id: UUID
    customer_id: UUID
    shipment_id: UUID
    payment_status: Literal["PAID"]
    already_confirmed: bool = False
