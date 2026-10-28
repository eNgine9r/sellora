"""Minimal, workspace-isolated representation of outside carrier documents."""
from datetime import date, datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict


class NovaPoshtaExternalScanRequest(BaseModel):
    from_date: date
    to_date: date
    dry_run: bool = True


class NovaPoshtaExternalDocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    tracking_number: str
    document_ref: str | None
    provider_status: str | None
    match_state: str
    matched_shipment_id: UUID | None
    first_seen_at: datetime
    last_seen_at: datetime
