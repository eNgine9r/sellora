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


class ImportValidationReport(BaseModel):
    is_valid: bool
    total_rows: int
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class ImportExecuteRequest(ImportValidationRequest):
    mode: str = "create_only"


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
