"""Read-only, provenance-bearing Direct ↔ Nova Poshta order evidence."""
from uuid import UUID
from pydantic import BaseModel, Field


class VerifiedDirectShipmentOrder(BaseModel):
    order_id: UUID
    order_number: str
    order_status: str
    payment_status: str
    is_historical: bool
    shipment_id: UUID
    shipment_status: str
    tracking_masked: str
    source_message_id: UUID
    evidence_type: str  # EXACT_SHIPMENT_TTN
    confirmed_in_crm: bool = False


class DirectUnmatchedTtn(BaseModel):
    tracking_masked: str
    source_message_id: UUID
    reason: str  # SHIPMENT_NOT_IN_CRM / MULTIPLE_SHIPMENT_MATCHES / CUSTOMER_MISMATCH


class DirectOrderEvidenceResponse(BaseModel):
    conversation_id: UUID
    verified_orders: list[VerifiedDirectShipmentOrder]
    needs_review: list[DirectUnmatchedTtn]
    has_multiple_orders: bool
    scan_truncated: bool

class ConfirmDirectOrderEvidenceRequest(BaseModel):
    expected_order_ids: list[UUID] = Field(min_length=1, max_length=100)


class ConfirmDirectOrderEvidenceResponse(BaseModel):
    confirmed_order_count: int
    created_links: int
    existing_links: int
    primary_order_linked: bool