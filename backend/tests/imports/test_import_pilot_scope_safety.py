from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.repositories.import_center_repository import ImportJobLogRepository
from app.services.import_center_service import ImportServiceError
from app.services.import_durable_service import (
    HISTORICAL_ORDER_IGNORED_FIELDS,
    append_report_issues,
    ensure_pilot_entity_type,
    historical_status_issues,
    pilot_safe_mapping,
)
from app.schemas.import_center import ImportReportResponse


class FakeDb:
    def __init__(self) -> None:
        self.added = []
        self.flushes = 0

    def add(self, value) -> None:
        self.added.append(value)

    def flush(self) -> None:
        self.flushes += 1


def test_historical_order_mapping_ignores_shipment_side_effect_fields() -> None:
    mapping = {
        "order_number": "Order Number",
        "variant_sku": "SKU",
        "quantity": "Quantity",
        "unit_price": "Unit Price",
        "tracking_number": "Tracking Number",
        "carrier": "Carrier",
        "city": "City",
        "warehouse": "Warehouse",
    }

    safe = pilot_safe_mapping("orders_history", mapping)

    assert safe["order_number"] == "Order Number"
    assert safe["variant_sku"] == "SKU"
    assert safe["quantity"] == "Quantity"
    assert safe["unit_price"] == "Unit Price"
    assert HISTORICAL_ORDER_IGNORED_FIELDS.isdisjoint(safe)


def test_non_historical_mapping_is_copied_without_mutation() -> None:
    mapping = {"name": "Name", "phone": "Phone"}

    safe = pilot_safe_mapping("customers", mapping)

    assert safe == mapping
    assert safe is not mapping


def test_shipments_import_is_explicitly_unsupported_for_controlled_pilot() -> None:
    with pytest.raises(ImportServiceError, match="not supported in the controlled pilot"):
        ensure_pilot_entity_type("shipments")


def test_unknown_historical_order_and_payment_statuses_are_errors() -> None:
    rows = [
        {
            "Order Status": "mystery-status",
            "Payment Status": "unknown-payment",
        },
        {
            "Order Status": "completed",
            "Payment Status": "paid",
        },
    ]
    mapping = {
        "order_status": "Order Status",
        "payment_status": "Payment Status",
    }

    issues = historical_status_issues(rows, mapping)

    assert len(issues) == 2
    assert {item.field for item in issues} == {"order_status", "payment_status"}
    assert {item.row_number for item in issues} == {2}
    assert all(item.severity == "ERROR" for item in issues)


def test_strict_status_errors_make_dry_run_non_executable() -> None:
    report = ImportReportResponse(
        job_id="00000000-0000-0000-0000-000000000001",
        entity_type="orders_history",
        sheet_name="CSV",
        total_rows=1,
        valid_rows=1,
        invalid_rows=0,
        warning_rows=0,
        error_rows=0,
        skipped_rows=0,
        duplicate_rows=0,
        ready_to_import_rows=1,
        estimated_entities_to_create=1,
    )
    issues = historical_status_issues(
        [{"Order Status": "not-real"}],
        {"order_status": "Order Status"},
    )

    append_report_issues(report, issues)

    assert report.error_rows == 1
    assert report.invalid_rows == 1
    assert report.valid_rows == 0
    assert report.ready_to_import_rows == 0
    assert report.estimated_entities_to_create == 0


def test_import_log_repository_never_persists_raw_source_row() -> None:
    db = FakeDb()
    repository = ImportJobLogRepository(db)
    log = SimpleNamespace(
        row_number=2,
        status="SUCCESS",
        message="Customer created",
        raw_data={
            "Name": "QA Customer",
            "Phone": "SYNTHETIC_PHONE_MARKER",
            "Address": "Synthetic address",
        },
    )

    created = repository.create(log)

    assert created.raw_data is None
    assert db.added == [log]
    assert db.flushes == 1
