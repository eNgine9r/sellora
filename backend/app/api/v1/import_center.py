from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.dependencies.rbac import get_workspace_id, require_roles
from app.models.import_job import ImportJobStatus
from app.models.import_job_log import ImportJobLogStatus
from app.models.role import RoleName
from app.models.user import User
from app.schemas.import_center import (
    ImportExecuteRequest,
    ImportExecuteResponse,
    ImportJobLogResponse,
    ImportReportResponse,
    ImportPreviewRequest,
    ImportPreviewResponse,
    ImportUploadResponse,
    ImportValidationReport,
    ImportValidationRequest,
    MappingPresetResponse,
    SuggestMappingRequest,
    SuggestMappingResponse,
    YourJewelryPresetResponse,
    SheetListResponse,
)
from app.services.import_atomic_execution import AtomicImportSession, persist_rolled_back_import
from app.services.import_center_service import ImportServiceError, MappingSuggestionService, YOUR_JEWELRY_EXCEL_V1
from app.services.import_durable_service import DurableImportService as ImportService
from app.services.import_execution_guard import ImportExecutionGuard, ImportExecutionGuardError

router = APIRouter(prefix="/import", tags=["Import Center"])


def _bad_request(exc: ImportServiceError | ImportExecutionGuardError) -> HTTPException:
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.post("/upload", response_model=ImportUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_import_file(
    file: UploadFile = File(...),
    workspace_id: UUID = Depends(get_workspace_id),
    current_user: User = Depends(require_roles(RoleName.OWNER)),
    db: Session = Depends(get_db),
) -> ImportUploadResponse:
    try:
        job = await ImportService(db).upload(workspace_id, file, current_user.id)
    except ImportServiceError as exc:
        raise _bad_request(exc)
    return ImportUploadResponse(job_id=job.id, status=job.status, file_name=job.file_name)


@router.get("/presets/your_jewelry_excel_v1", response_model=MappingPresetResponse, dependencies=[Depends(require_roles(RoleName.OWNER))])
def your_jewelry_preset() -> MappingPresetResponse:
    return MappingPresetResponse(**YOUR_JEWELRY_EXCEL_V1)


@router.get("/presets/your_jewelry_product_catalog_v1", response_model=MappingPresetResponse, dependencies=[Depends(require_roles(RoleName.OWNER))])
def your_jewelry_product_catalog_preset() -> MappingPresetResponse:
    return MappingPresetResponse(**MappingSuggestionService().product_catalog_preset())


@router.get("/presets/your_jewelry_orders_history_v1", response_model=MappingPresetResponse, dependencies=[Depends(require_roles(RoleName.OWNER))])
def your_jewelry_orders_history_preset() -> MappingPresetResponse:
    return MappingPresetResponse(**MappingSuggestionService().orders_history_preset())


@router.get("/presets/your_jewelry_advertising_history_v1", response_model=MappingPresetResponse, dependencies=[Depends(require_roles(RoleName.OWNER))])
def your_jewelry_advertising_history_preset() -> MappingPresetResponse:
    return MappingPresetResponse(**MappingSuggestionService().advertising_history_preset())


@router.get("/presets/your-jewelry", response_model=YourJewelryPresetResponse, dependencies=[Depends(require_roles(RoleName.OWNER))])
def your_jewelry_hardened_preset() -> YourJewelryPresetResponse:
    return MappingSuggestionService().your_jewelry_preset()


@router.get("/{job_id}/sheets", response_model=SheetListResponse, dependencies=[Depends(require_roles(RoleName.OWNER))])
def list_sheets(job_id: UUID, workspace_id: UUID = Depends(get_workspace_id), db: Session = Depends(get_db)) -> SheetListResponse:
    try:
        return SheetListResponse(sheets=ImportService(db).list_sheets(workspace_id, job_id))
    except ImportServiceError as exc:
        raise _bad_request(exc)


@router.post("/{job_id}/preview", response_model=ImportPreviewResponse, dependencies=[Depends(require_roles(RoleName.OWNER))])
def preview_import(job_id: UUID, payload: ImportPreviewRequest, workspace_id: UUID = Depends(get_workspace_id), db: Session = Depends(get_db)) -> ImportPreviewResponse:
    try:
        columns, rows = ImportService(db).preview(workspace_id, job_id, payload.sheet_name, payload.limit)
    except ImportServiceError as exc:
        raise _bad_request(exc)
    return ImportPreviewResponse(columns=columns, rows=rows)


@router.post("/{job_id}/validate", response_model=ImportValidationReport)
def validate_import(job_id: UUID, payload: ImportValidationRequest, workspace_id: UUID = Depends(get_workspace_id), current_user: User = Depends(require_roles(RoleName.OWNER)), db: Session = Depends(get_db)) -> ImportValidationReport:
    try:
        return ImportService(db).validate(workspace_id, job_id, payload.entity_type, payload.sheet_name, payload.column_mapping, current_user.id, payload.options)
    except ImportServiceError as exc:
        raise _bad_request(exc)


@router.post("/{job_id}/suggest-mapping", response_model=SuggestMappingResponse, dependencies=[Depends(require_roles(RoleName.OWNER))])
def suggest_mapping(job_id: UUID, payload: SuggestMappingRequest, workspace_id: UUID = Depends(get_workspace_id), db: Session = Depends(get_db)) -> SuggestMappingResponse:
    try:
        return ImportService(db).suggest_mapping(workspace_id, job_id, payload.sheet_name, payload.entity_type)
    except ImportServiceError as exc:
        raise _bad_request(exc)


@router.post("/{job_id}/dry-run", response_model=ImportReportResponse)
def dry_run_import(job_id: UUID, payload: ImportValidationRequest, workspace_id: UUID = Depends(get_workspace_id), current_user: User = Depends(require_roles(RoleName.OWNER)), db: Session = Depends(get_db)) -> ImportReportResponse:
    try:
        report = ImportService(db).dry_run(workspace_id, job_id, payload.entity_type, payload.sheet_name, payload.column_mapping, current_user.id, payload.options)
        if report.error_rows == 0:
            ImportExecutionGuard(db).record_successful_dry_run(
                workspace_id=workspace_id,
                job_id=job_id,
                entity_type=payload.entity_type,
                sheet_name=payload.sheet_name,
                column_mapping=payload.column_mapping,
                options=payload.options,
                actor_user_id=current_user.id,
                total_rows=report.total_rows,
            )
        return report
    except (ImportServiceError, ImportExecutionGuardError) as exc:
        raise _bad_request(exc)


@router.post("/{job_id}/execute", response_model=ImportExecuteResponse | ImportReportResponse)
def execute_import(job_id: UUID, payload: ImportExecuteRequest, workspace_id: UUID = Depends(get_workspace_id), current_user: User = Depends(require_roles(RoleName.OWNER)), db: Session = Depends(get_db)) -> ImportExecuteResponse | ImportReportResponse:
    guard = ImportExecutionGuard(db)
    if payload.dry_run:
        try:
            result = ImportService(db).execute(workspace_id, job_id, payload.entity_type, payload.sheet_name, payload.column_mapping, payload.mode, current_user.id, True, payload.options)
            if isinstance(result, ImportReportResponse) and result.error_rows == 0:
                guard.record_successful_dry_run(
                    workspace_id=workspace_id,
                    job_id=job_id,
                    entity_type=payload.entity_type,
                    sheet_name=payload.sheet_name,
                    column_mapping=payload.column_mapping,
                    options=payload.options,
                    actor_user_id=current_user.id,
                    total_rows=result.total_rows,
                )
            return result
        except (ImportServiceError, ImportExecutionGuardError) as exc:
            raise _bad_request(exc)

    try:
        guard.require_matching_dry_run(
            workspace_id=workspace_id,
            job_id=job_id,
            entity_type=payload.entity_type,
            sheet_name=payload.sheet_name,
            column_mapping=payload.column_mapping,
            options=payload.options,
        )
    except ImportExecutionGuardError as exc:
        raise _bad_request(exc)

    atomic_service = ImportService(AtomicImportSession(db))
    total_rows = 0
    try:
        job = atomic_service.execute(workspace_id, job_id, payload.entity_type, payload.sheet_name, payload.column_mapping, payload.mode, current_user.id, False, payload.options)
        total_rows = int(job.total_rows or 0)
        if job.status != ImportJobStatus.COMPLETED.value or int(job.failed_rows or 0) > 0:
            raise ImportServiceError("One or more import rows failed; the import was rolled back")
        db.commit()
        db.refresh(job)
        return ImportExecuteResponse(job=job)
    except Exception as exc:
        db.rollback()
        reason = str(exc) if isinstance(exc, ImportServiceError) else f"{exc.__class__.__name__} during import execution"
        try:
            persist_rolled_back_import(
                db,
                workspace_id=workspace_id,
                job_id=job_id,
                actor_user_id=current_user.id,
                total_rows=total_rows,
                reason=reason,
            )
        except Exception:
            db.rollback()
        safe_error = exc if isinstance(exc, ImportServiceError) else ImportServiceError("Import execution failed and all business writes were rolled back")
        raise _bad_request(safe_error)


@router.get("/{job_id}/logs", response_model=list[ImportJobLogResponse], dependencies=[Depends(require_roles(RoleName.OWNER))])
def import_logs(job_id: UUID, workspace_id: UUID = Depends(get_workspace_id), log_status: ImportJobLogStatus | None = Query(default=None, alias="status"), db: Session = Depends(get_db)) -> list[ImportJobLogResponse]:
    try:
        return ImportService(db).list_logs(workspace_id, job_id, log_status.value if log_status else None)
    except ImportServiceError as exc:
        raise _bad_request(exc)
