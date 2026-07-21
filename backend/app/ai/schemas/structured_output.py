from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.ai_direct import AIIntent, AIPriority, AISentiment


class RecommendedAction(StrEnum):
    ASK_CLARIFICATION = "ASK_CLARIFICATION"
    CREATE_LEAD_DRAFT = "CREATE_LEAD_DRAFT"
    CREATE_CUSTOMER_DRAFT = "CREATE_CUSTOMER_DRAFT"
    CREATE_ORDER_DRAFT = "CREATE_ORDER_DRAFT"
    REPLY_ONLY = "REPLY_ONLY"
    ESCALATE_TO_MANAGER = "ESCALATE_TO_MANAGER"
    MARK_AS_SPAM = "MARK_AS_SPAM"


class ProductMention(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: str = Field(max_length=240)
    quantity: int | None = Field(default=None, ge=1, le=999)
    color: str | None = Field(default=None, max_length=80)
    size: str | None = Field(default=None, max_length=80)
    sku: str | None = Field(default=None, max_length=120)


class ExtractedEntities(BaseModel):
    model_config = ConfigDict(extra="forbid")
    customer_name: str | None = Field(default=None, max_length=160)
    phone: str | None = Field(default=None, max_length=60)
    product_mentions: list[ProductMention] = Field(default_factory=list, max_length=20)
    city_name: str | None = Field(default=None, max_length=120)
    warehouse_text: str | None = Field(default=None, max_length=180)
    payment_method: str | None = Field(default=None, max_length=40)
    budget_min: float | None = Field(default=None, ge=0)
    budget_max: float | None = Field(default=None, ge=0)
    delivery_deadline: str | None = Field(default=None, max_length=120)


class DirectMessageAnalysisOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    language: str = Field(default="uk", max_length=12)
    intent: AIIntent
    intent_confidence: float = Field(ge=0, le=1)
    sentiment: AISentiment = AISentiment.UNKNOWN
    sentiment_confidence: float = Field(default=0, ge=0, le=1)
    urgency: AIPriority = AIPriority.NORMAL
    requires_human: bool = True
    clarification_required: bool = False
    summary: str = Field(max_length=1000)
    extracted_entities: ExtractedEntities = Field(default_factory=ExtractedEntities)
    missing_fields: list[str] = Field(default_factory=list, max_length=20)
    recommended_action: RecommendedAction
    suggested_reply: str | None = Field(default=None, max_length=2000)

    @field_validator("intent_confidence", "sentiment_confidence", mode="before")
    @classmethod
    def normalize_confidence(cls, value: float | int | str) -> float:
        numeric = float(value)
        if numeric > 1 and numeric <= 100:
            numeric = numeric / 100
        return max(0, min(1, numeric))


class CustomerDeliveryProvider(StrEnum):
    NOVA_POSHTA = "NOVA_POSHTA"
    UKRPOSHTA = "UKRPOSHTA"
    MEEST = "MEEST"
    COURIER = "COURIER"
    OTHER = "OTHER"
    UNKNOWN = "UNKNOWN"


class CustomerDeliveryPointType(StrEnum):
    WAREHOUSE = "WAREHOUSE"
    POSTOMAT = "POSTOMAT"
    ADDRESS = "ADDRESS"
    UNKNOWN = "UNKNOWN"


class DirectCustomerDataExtractionOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    recipient_name: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=80)
    city: str | None = Field(default=None, max_length=160)
    region: str | None = Field(default=None, max_length=160)
    delivery_provider: CustomerDeliveryProvider = CustomerDeliveryProvider.UNKNOWN
    delivery_point_type: CustomerDeliveryPointType = CustomerDeliveryPointType.UNKNOWN
    warehouse_number: str | None = Field(default=None, max_length=40)
    warehouse_text: str | None = Field(default=None, max_length=255)
    notes: str | None = Field(default=None, max_length=500)

    recipient_name_confidence: float = Field(default=0, ge=0, le=1)
    phone_confidence: float = Field(default=0, ge=0, le=1)
    city_confidence: float = Field(default=0, ge=0, le=1)
    delivery_provider_confidence: float = Field(default=0, ge=0, le=1)
    warehouse_confidence: float = Field(default=0, ge=0, le=1)
    overall_confidence: float = Field(default=0, ge=0, le=1)

    clarification_required: bool = False
    missing_fields: list[str] = Field(default_factory=list, max_length=20)

    @field_validator(
        "recipient_name_confidence",
        "phone_confidence",
        "city_confidence",
        "delivery_provider_confidence",
        "warehouse_confidence",
        "overall_confidence",
        mode="before",
    )
    @classmethod
    def normalize_extraction_confidence(cls, value: float | int | str) -> float:
        numeric = float(value)
        if numeric > 1 and numeric <= 100:
            numeric = numeric / 100
        return max(0, min(1, numeric))
