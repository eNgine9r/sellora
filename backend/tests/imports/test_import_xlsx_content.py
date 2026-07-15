from io import BytesIO

import pytest
from openpyxl import Workbook

from app.services.import_center_service import ImportServiceError
from app.services.import_pilot_safe_service import PilotSafeImportService


def validator() -> PilotSafeImportService:
    return PilotSafeImportService.__new__(PilotSafeImportService)


def valid_xlsx_bytes() -> bytes:
    workbook = Workbook()
    workbook.active.append(["Name", "Phone"])
    workbook.active.append(["QA Customer", "SYNTHETIC"])
    stream = BytesIO()
    workbook.save(stream)
    workbook.close()
    return stream.getvalue()


def test_valid_xlsx_content_is_accepted() -> None:
    validator()._validate_upload_content("customers.xlsx", valid_xlsx_bytes())


def test_pk_prefixed_corrupted_xlsx_is_rejected_safely() -> None:
    with pytest.raises(ImportServiceError, match="not a valid workbook"):
        validator()._validate_upload_content("corrupted.xlsx", b"PK-not-a-real-xlsx")


def test_non_xlsx_content_keeps_existing_validation() -> None:
    with pytest.raises(ImportServiceError, match="UTF-8"):
        validator()._validate_upload_content("customers.csv", b"\xff\xfe\xfd")
