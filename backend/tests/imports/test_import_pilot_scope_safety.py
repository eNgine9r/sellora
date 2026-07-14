from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.repositories.import_center_repository import ImportJobLogRepository
from app.services.import_center_service import ImportServiceError
from app.services.import_durable_service import (
    HISTORICAL_ORDER_IGNORED_FIELDS,
    ensure_pilot_entity_type,
    pilot_safe_mapping,
)


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


def test_import_log_repository_never_persists_raw_source_row() -> None:
    db = FakeDb()
    repository = ImportJobLogRepository(db)
    log = SimpleNamespace(
        row_number=2,
        status="SUCCESS",
        message="Customer created",
        raw_data={
            "Name": "QA Customer",
            "Phone": "+380000000001",
            "Address": "Synthetic address",
        },
    )

    created = repository.create(log)

    assert created.raw_data is None
    assert db.added == [log]
    assert db.flushes == 1
