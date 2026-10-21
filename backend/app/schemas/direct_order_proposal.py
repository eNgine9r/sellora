from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class OrderProposalCandidate(BaseModel):
    product_id: UUID
    variant_id: UUID
    product_name: str
    sku: str
    color: str | None
    size: str | None
    price: Decimal | None
    available_quantity: int | None


class OrderProposalEvidence(BaseModel):
    message_id: UUID
    snippet: str = Field(max_length=160)


class OrderProposalLine(BaseModel):
    id: str
    mention_text: str = Field(max_length=240)
    quantity: int = Field(ge=1, le=999)
    source: Literal["ANALYSIS_CONTEXT", "INBOUND_SKU", "INBOUND_PRODUCT"]
    evidence: list[OrderProposalEvidence] = Field(default_factory=list, max_length=1)
    requires_review: bool
    match_status: Literal["MATCHED", "AMBIGUOUS", "NOT_FOUND"]
    matched_by: str | None = None
    reason: str
    candidates_truncated: bool = False
    candidates: list[OrderProposalCandidate] = Field(default_factory=list, max_length=10)


class DirectOrderProposal(BaseModel):
    conversation_id: UUID
    analysis_id: UUID | None = None
    analysis_created_at: datetime | None = None
    analysis_context_message_id: UUID | None = None
    analysis_state: Literal["MISSING", "COMPLETED", "STALE", "FAILED", "MALFORMED", "PENDING"]
    commercial_stage: Literal["NONE", "INTEREST", "PRODUCT_QUESTION", "PURCHASE_REQUEST"] = "NONE"
    commercial_reason: str | None = None
    catalog_truncated: bool = False
    context_truncated: bool = False
    lines: list[OrderProposalLine] = Field(default_factory=list, max_length=40)
