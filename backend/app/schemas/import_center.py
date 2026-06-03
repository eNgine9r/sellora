from datetime import datetime
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
    warning_rows: int
    error_rows: int
    skipped_rows: int
    duplicate_rows: int
    ready_to_import_rows: int
    estimated_entities_to_create: int
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
