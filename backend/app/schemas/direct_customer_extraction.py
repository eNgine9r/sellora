from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class DirectCustomerExtractionData(BaseModel):
    recipient_name: str | None = None
    phone: str | None = None
    city: str | None = None
    region: str | None = None
    delivery_provider: str = "UNKNOWN"
    delivery_point_type: str = "UNKNOWN"
    warehouse_number: str | None = None
    warehouse_text: str | None = None
    nova_poshta_city_ref: str | None = None
    nova_poshta_warehouse_ref: str | None = None
    city_verified: bool = False
    warehouse_verified: bool = False
    recipient_name_confidence: float = 0
    phone_confidence: float = 0
    city_confidence: float = 0
    delivery_provider_confidence: float = 0
    warehouse_confidence: float = 0
    overall_confidence: float = 0
    clarification_required: bool = False
    missing_fields: list[str] = Field(default_factory=list)
    conflicts: list[str] = Field(default_factory=list)
    applied_fields: list[str] = Field(default_factory=list)
    notes: str | None = None


class DirectCustomerExtractionResponse(BaseModel):
    analysis_id: UUID
    conversation_id: UUID
    status: str
    data: DirectCustomerExtractionData | None = None
    source_message_count: int = 0
    safe_error_code: str | None = None
    applied: bool = False
    created_at: datetime
    completed_at: datetime | None = None


class DirectCustomerExtractionApplyRequest(BaseModel):
    analysis_id: UUID
    overwrite_fields: list[str] = Field(default_factory=list, max_length=8)
