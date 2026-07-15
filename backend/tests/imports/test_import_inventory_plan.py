from uuid import UUID

from app.schemas.import_center import ImportReportResponse
from app.services.import_pilot_safe_service import append_inventory_update_plan


def base_report() -> ImportReportResponse:
    return ImportReportResponse(
        job_id=UUID("00000000-0000-0000-0000-000000000001"),
        entity_type="inventory",
        sheet_name="CSV",
        total_rows=2,
        valid_rows=2,
        invalid_rows=0,
        warning_rows=0,
        error_rows=0,
        skipped_rows=0,
        duplicate_rows=0,
        ready_to_import_rows=2,
        estimated_entities_to_create=2,
        created_count=2,
        updated_count=0,
    )


def test_existing_inventory_is_reported_as_absolute_update() -> None:
    report = append_inventory_update_plan(base_report(), [2, 3])

    assert report.updated_count == 2
    assert report.created_count == 0
    assert report.estimated_entities_to_create == 0
    assert report.ready_to_import_rows == 2
    assert report.warning_rows == 2
    assert report.warnings_count == 2
    assert set(report.warnings_by_row) == {2, 3}
    assert all("absolute quantities" in item.message for item in report.sample_warnings)


def test_new_inventory_remains_creation_plan() -> None:
    report = append_inventory_update_plan(base_report(), [])

    assert report.updated_count == 0
    assert report.created_count == 2
    assert report.estimated_entities_to_create == 2
    assert report.warnings_count == 0
