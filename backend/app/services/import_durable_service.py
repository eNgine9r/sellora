from __future__ import annotations

from pathlib import Path
from uuid import UUID

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.import_job import ImportJob, ImportJobStatus
from app.schemas.import_center import (
    ImportReportResponse,
    ImportValidationIssue,
    ImportValidationReport,
    SuggestMappingResponse,
)
from app.services.import_center_service import (
    HISTORICAL_ORDER_IGNORED_FIELDS if False else IMPORT_ALLOWED_SUFFIXES,
)
