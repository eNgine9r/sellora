from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.import_job import ImportJobStatus
from app.models.import_job_log import ImportJobLogStatus


class ImportUploadResponse(BaseModel):
    job_id: UUID
    status: ImportJobStatus
    file_name: str


class ImportJobResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    file_name: str
    file_type: str
    status: ImportJobStatus
    total_rows: int
    processed_rows: int
    success_rows: int
    failed_rows: int
    created_by: UUID | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class SheetListResponse(BaseModel):
    sheets: list[str]


class ImportPreviewRequest(BaseModel):
    sheet_name: str
    limit: int = Field(default=20, ge=1, le=100)


class ImportPreviewResponse(BaseModel):
    columns: list[str]
    rows: list[dict]


class ImportValidationRequest(BaseModel):
    entity_type: str
    sheet_name: str
    column_mapping: dict[str, str]
    options: dict | None = None


class ImportValidationIssue(BaseModel):
    row_number: int | None = None
    severity: str
    field: str | None = None
    message: str
    raw_value: object | None = None
    normalized_value: object | None = None


class ImportValidationReport(BaseModel):
    is_valid: bool
    total_rows: int
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    issues: list[ImportValidationIssue] = Field(default_factory=list)


class ImportReportResponse(BaseModel):
    job_id: UUID
    entity_type: str
    sheet_name: str
    total_rows: int
    valid_rows: int
    invalid_rows: int = 0
    created_count: int = 0
    updated_count: int = 0
    warnings_count: int = 0
    errors_count: int = 0
    errors_by_row: dict[int, list[ImportValidationIssue]] = Field(default_factory=dict)
    warnings_by_row: dict[int, list[ImportValidationIssue]] = Field(default_factory=dict)
    warning_rows: int
    error_rows: int
    skipped_rows: int
    duplicate_rows: int
    ready_to_import_rows: int
    estimated_entities_to_create: int
    products_detected: int = 0
    variants_detected: int = 0
    inventory_rows_detected: int = 0
    images_detected: int = 0
    duplicate_products: int = 0
    duplicate_variants: int = 0
    orders_detected: int = 0
    order_items_detected: int = 0
    customers_matched: int = 0
    customers_to_create: int = 0
    variants_matched: int = 0
    variants_missing: int = 0
    shipments_detected: int = 0
    duplicate_orders: int = 0
    ready_orders: int = 0
    ready_items: int = 0
    estimated_revenue: Decimal = Decimal("0")
    estimated_ad_cost: Decimal = Decimal("0")
    estimated_profit: Decimal = Decimal("0")
    campaigns_detected: int = 0
    campaigns_to_create: int = 0
    campaigns_reused: int = 0
    metrics_detected: int = 0
    duplicate_metrics: int = 0
    estimated_spend: Decimal = Decimal("0")
    estimated_net_profit: Decimal = Decimal("0")
    estimated_roas: Decimal = Decimal("0")
    sample_errors: list[ImportValidationIssue] = Field(default_factory=list)
    sample_warnings: list[ImportValidationIssue] = Field(default_factory=list)


class ImportExecuteRequest(ImportValidationRequest):
    mode: str = "create_only"
    dry_run: bool = False


class ImportExecuteResponse(BaseModel):
    job: ImportJobResponse


class ImportJobLogResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    import_job_id: UUID
    row_number: int | None
    entity_type: str
    status: ImportJobLogStatus
    message: str | None
    raw_data: dict | None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class MappingPresetResponse(BaseModel):
    name: str
    sheets: list[str]
    mappings: dict[str, dict[str, str]]


class YourJewelryPresetResponse(BaseModel):
    preset_name: str
    supported_sheets: list[str]
    suggested_entity_type_per_sheet: dict[str, str]
    suggested_column_mapping_per_sheet: dict[str, dict[str, dict[str, list[str]]]]
    notes: list[str]


class SuggestMappingRequest(BaseModel):
    sheet_name: str
    entity_type: str


class SuggestMappingResponse(BaseModel):
    suggested_mapping: dict[str, str]
    confidence: dict[str, float]
    unmapped_columns: list[str]
    required_fields_missing: list[str]
