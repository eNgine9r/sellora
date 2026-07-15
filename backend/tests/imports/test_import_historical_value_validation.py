from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

from app.services.import_center_service import MappingValidationService
from app.services.import_pilot_safe_service import PilotSafeImportService


class FakeParser:
    def __init__(self, rows: list[dict]) -> None:
        self.rows = rows

    def read_rows(self, _file_path: str, _sheet_name: str):
        return list(self.rows[0].keys()), self.rows


class FakeLookup:
    pass


def test_historical_order_invalid_date_is_structured_non_executable_issue() -> None:
    service = object.__new__(PilotSafeImportService)
    service.validator = MappingValidationService()
    service.lookup = FakeLookup()
    service.parser = FakeParser([
        {
            "Order Date": "not-a-date",
            "Variant SKU": "QA-VARIANT",
            "Quantity": "1",
            "Unit Price": "799",
            "Order Status": "completed",
            "Payment Status": "paid",
        }
    ])
    service._job = lambda _workspace_id, _job_id: SimpleNamespace(file_path="synthetic.csv")

    issues = service._historical_issues(
        uuid4(),
        uuid4(),
        "orders_history",
        "CSV",
        {
            "order_date": "Order Date",
            "variant_sku": "Variant SKU",
            "quantity": "Quantity",
            "unit_price": "Unit Price",
            "order_status": "Order Status",
            "payment_status": "Payment Status",
        },
    )

    date_issues = [item for item in issues if item.field == "order_date"]
    assert len(date_issues) == 1
    assert date_issues[0].row_number == 2
    assert date_issues[0].severity == "ERROR"
    assert date_issues[0].message == "order_date must be a valid date"
