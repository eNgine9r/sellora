import asyncio
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.dependencies.rbac import require_roles
from app.models.customer import Customer
from app.models.import_job import ImportJob, ImportJobStatus
from app.models.import_job_log import ImportJobLog, ImportJobLogStatus
from app.models.inventory import Inventory
from app.models.product import Product
from app.models.product_variant import ProductVariant
from app.models.role import RoleName
from app.schemas.import_center import ImportValidationRequest
from app.services.import_center_service import EntityImportService, ExcelParserService, ImportService, MappingValidationService


class FakeDb:
    def __init__(self) -> None:
        self.added = []
        self.commits = 0

    def add(self, obj):
        self.added.append(obj)

    def flush(self) -> None:
        for obj in self.added:
            if getattr(obj, "id", None) is None:
                obj.id = uuid4()

    def commit(self) -> None:
        self.commits += 1

    def refresh(self, obj) -> None:
        pass


class FakeJobs:
    def __init__(self, job: ImportJob | None = None) -> None:
        self.job = job

    def create(self, job):
        job.id = job.id or uuid4()
        self.job = job
        return job

    def get(self, workspace_id, job_id):
        if self.job and self.job.workspace_id == workspace_id and self.job.id == job_id:
            return self.job
        return None


class FakeLogs:
    def __init__(self) -> None:
        self.logs = []

    def create(self, log):
        log.id = log.id or uuid4()
        self.logs.append(log)
        return log

    def list(self, workspace_id, import_job_id, status=None):
        return [log for log in self.logs if log.workspace_id == workspace_id and log.import_job_id == import_job_id and (status is None or log.status == status)]


class FakeAuditLogs:
    def __init__(self) -> None:
        self.records = []

    def create(self, **kwargs):
        self.records.append(kwargs)
        return SimpleNamespace(**kwargs)


class FakeParser:
    def __init__(self) -> None:
        self.rows = [{"Name": "Alice", "Phone": "1"}, {"Name": None, "Phone": None}]

    def list_sheets(self, file_path):
        return ["Customers", "Products"]

    def preview(self, file_path, sheet_name, limit):
        return ["Name", "Phone"], self.rows[:limit]

    def read_rows(self, file_path, sheet_name):
        return ["Name", "Phone"], self.rows


class FakeUploadFile:
    def __init__(self, filename: str, content: bytes) -> None:
        self.filename = filename
        self._content = content

    async def read(self) -> bytes:
        return self._content


def _import_service(tmp_path: Path) -> ImportService:
    workspace_id = uuid4()
    job = ImportJob(id=uuid4(), workspace_id=workspace_id, file_name="import.xlsx", file_type="xlsx", file_path=str(tmp_path / "import.xlsx"), status=ImportJobStatus.UPLOADED.value)
    service = ImportService.__new__(ImportService)
    service.db = FakeDb()
    service.jobs = FakeJobs(job)
    service.logs = FakeLogs()
    service.parser = FakeParser()
    service.validator = MappingValidationService()
    service.entity_importer = SimpleNamespace(import_row=lambda workspace_id, entity_type, row, mapping: (ImportJobLogStatus.SUCCESS if row.get("Name") else ImportJobLogStatus.FAILED, "ok" if row.get("Name") else "missing"))
    service.audit_logs = FakeAuditLogs()
    return service


def test_import_job_creation(tmp_path, monkeypatch) -> None:
    service = _import_service(tmp_path)
    service.jobs = FakeJobs()
    monkeypatch.setattr("app.services.import_center_service.get_settings", lambda: SimpleNamespace(import_max_file_size_mb=1, import_storage_path=str(tmp_path)))

    job = asyncio.run(service.upload(uuid4(), FakeUploadFile("safe.xlsx", b"file"), actor_user_id=uuid4()))
    assert job.status == ImportJobStatus.UPLOADED.value
    assert Path(job.file_path).name == "safe.xlsx"


def test_owner_only_access_and_manager_forbidden() -> None:
    workspace_id = uuid4()
    owner = SimpleNamespace(workspaces=[SimpleNamespace(workspace_id=workspace_id, workspace=SimpleNamespace(is_active=True), role=SimpleNamespace(name=RoleName.OWNER.value))])
    manager = SimpleNamespace(workspaces=[SimpleNamespace(workspace_id=workspace_id, workspace=SimpleNamespace(is_active=True), role=SimpleNamespace(name=RoleName.MANAGER.value))])
    guard = require_roles(RoleName.OWNER)

    assert guard(owner, workspace_id) is owner
    with pytest.raises(HTTPException) as exc:
        guard(manager, workspace_id)
    assert exc.value.status_code == 403


def test_excel_sheet_listing_and_preview_rows(tmp_path) -> None:
    service = _import_service(tmp_path)
    job = service.jobs.job

    assert service.list_sheets(job.workspace_id, job.id) == ["Customers", "Products"]
    columns, rows = service.preview(job.workspace_id, job.id, "Customers", 1)
    assert columns == ["Name", "Phone"]
    assert rows == [{"Name": "Alice", "Phone": "1"}]
    assert job.status == ImportJobStatus.PREVIEWED.value


def test_mapping_validation_success_and_failure() -> None:
    validator = MappingValidationService()
    valid = validator.validate("customers", {"name": "Name", "phone": "Phone"}, [{"Name": "Alice", "Phone": "1"}])
    invalid = validator.validate("orders", {"revenue": "Revenue"}, [{"Revenue": "bad"}])

    assert valid.is_valid
    assert not invalid.is_valid
    assert invalid.errors


def test_customer_product_inventory_and_order_import_success(monkeypatch) -> None:
    db = FakeDb()
    service = EntityImportService.__new__(EntityImportService)
    service.db = db
    product = Product(id=uuid4(), workspace_id=uuid4(), name="Watch", sku="W1")
    variant = ProductVariant(id=uuid4(), workspace_id=product.workspace_id, product_id=product.id, sku="W1-BLK")
    service.lookup = SimpleNamespace(
        find_customer=lambda workspace_id, phone=None, instagram_username=None: None,
        find_product_by_sku=lambda workspace_id, sku: None,
        find_product_by_name_or_sku=lambda workspace_id, name, sku: product,
        find_variant=lambda workspace_id, sku=None, product_id=None, color=None, size=None: variant if sku == "W1-BLK" else None,
        inventory_by_variant=lambda workspace_id, variant_id: Inventory(workspace_id=workspace_id, product_variant_id=variant_id, stock_quantity=0, reserved_quantity=0, minimum_quantity=0),
    )

    assert service.import_row(product.workspace_id, "customers", {"Name": "Alice"}, {"name": "Name"})[0] == ImportJobLogStatus.SUCCESS
    assert service.import_row(product.workspace_id, "products", {"Name": "Watch"}, {"name": "Name"})[0] == ImportJobLogStatus.SUCCESS
    assert service.import_row(product.workspace_id, "inventory", {"SKU": "W1-BLK", "Qty": 5}, {"variant_sku": "SKU", "stock_quantity": "Qty"})[0] == ImportJobLogStatus.SUCCESS
    assert service.import_row(product.workspace_id, "orders", {"Customer": "Alice", "Revenue": 10, "Date": "2026-01-01"}, {"customer_name": "Customer", "revenue": "Revenue", "created_at": "Date"})[0] in {ImportJobLogStatus.SUCCESS, ImportJobLogStatus.WARNING}


def test_failed_row_logging_and_workspace_isolation(tmp_path) -> None:
    service = _import_service(tmp_path)
    job = service.jobs.job

    imported = service.execute(job.workspace_id, job.id, "customers", "Customers", {"name": "Name", "phone": "Phone"}, "create_only", actor_user_id=uuid4())

    assert imported.processed_rows == 2
    assert imported.failed_rows == 1
    assert service.list_logs(job.workspace_id, job.id, ImportJobLogStatus.FAILED.value)[0].message == "missing"
    assert service.jobs.get(uuid4(), job.id) is None
