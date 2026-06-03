import asyncio
from decimal import Decimal
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
from app.services.import_center_service import EntityImportService, ExcelParserService, ExcelValueNormalizer, ImportService, MappingSuggestionService, MappingValidationService


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
        self.rows = [{"Name": "Alice", "Phone": "1"}, {"Name": "Bob", "Phone": None}]

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
    service.lookup = SimpleNamespace(find_customer=lambda *args, **kwargs: None, find_product_by_sku=lambda *args, **kwargs: None, find_variant=lambda *args, **kwargs: None, find_ad_campaign_by_name=lambda *args, **kwargs: None, find_ad_campaign_by_id=lambda *args, **kwargs: None, find_ad_metric_by_campaign_date=lambda *args, **kwargs: None)
    service.entity_importer = SimpleNamespace(import_row=lambda workspace_id, entity_type, row, mapping: (ImportJobLogStatus.SUCCESS if row.get("Phone") else ImportJobLogStatus.FAILED, "ok" if row.get("Phone") else "missing"))
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
    service.validator = MappingValidationService()
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


def test_dry_run_does_not_create_business_records_and_reports_counters(tmp_path) -> None:
    service = _import_service(tmp_path)
    job = service.jobs.job

    report = service.dry_run(job.workspace_id, job.id, "customers", "Customers", {"name": "Name", "phone": "Phone"}, actor_user_id=uuid4())

    assert report.total_rows == 2
    assert report.ready_to_import_rows == 2
    assert report.estimated_entities_to_create == 2
    assert service.db.added == []


def test_excel_value_normalizer_handles_numbers_dates_currency_dash_and_empty_values() -> None:
    normalizer = ExcelValueNormalizer()

    assert normalizer.number("1 250 грн") == 1250
    assert normalizer.number("1,25") == Decimal("1.25")
    assert normalizer.text("-") is None
    assert normalizer.text("") is None
    assert normalizer.text("  Instagram  ") == "Instagram"
    assert normalizer.date("01.06.2026").date().isoformat() == "2026-06-01"
    assert normalizer.date("2026-06-01").date().isoformat() == "2026-06-01"
    assert normalizer.date(45444) is not None
    assert normalizer.boolean("так") is True
    assert normalizer.percent("10%") == Decimal("0.1")


def test_suggested_mapping_for_your_jewelry_orders_sheet_uses_synthetic_columns() -> None:
    suggestion = MappingSuggestionService().suggest(["Дата замовлення", "Сума", "Прибуток", "Реклама", "Місто"], "orders")

    assert suggestion.suggested_mapping["created_at"] == "Дата замовлення"
    assert suggestion.suggested_mapping["revenue"] == "Сума"
    assert suggestion.suggested_mapping["net_profit"] == "Прибуток"
    assert suggestion.confidence["created_at"] >= 0.75


def test_stronger_validation_detects_invalid_number_invalid_date_and_missing_required_fields() -> None:
    validator = MappingValidationService()
    report = validator.validate("orders", {"customer_name": "Customer", "revenue": "Revenue", "created_at": "Date"}, [{"Customer": "Test Customer", "Revenue": "bad", "Date": "not-a-date"}])
    missing = validator.validate("inventory", {"stock_quantity": "Qty"}, [{"Qty": 1}])

    assert not report.is_valid
    assert any(issue.field == "revenue" for issue in report.issues)
    assert any(issue.field == "created_at" for issue in report.issues)
    assert not missing.is_valid


def test_validation_detects_duplicate_customer_product_variant_and_inventory_rows() -> None:
    workspace_id = uuid4()
    lookup = SimpleNamespace(
        find_customer=lambda workspace_id, phone=None, instagram_username=None: Customer(id=uuid4(), workspace_id=workspace_id, name="Existing") if phone else None,
        find_product_by_sku=lambda workspace_id, sku: Product(id=uuid4(), workspace_id=workspace_id, name="Existing", sku=sku) if sku else None,
        find_variant=lambda workspace_id, sku=None, product_id=None, color=None, size=None: ProductVariant(id=uuid4(), workspace_id=workspace_id, product_id=uuid4(), sku=sku) if sku else None,
    )
    validator = MappingValidationService()

    customer = validator.validate("customers", {"phone": "Phone"}, [{"Phone": "+380000000000"}], workspace_id, lookup)
    product = validator.validate("products", {"name": "Name", "sku": "SKU"}, [{"Name": "Synthetic Product", "SKU": "SKU-1"}], workspace_id, lookup)
    variant = validator.validate("product_variants", {"product_name": "Product", "variant_sku": "SKU"}, [{"Product": "Synthetic Product", "SKU": "SKU-1"}], workspace_id, lookup)
    inventory = validator.validate("inventory", {"variant_sku": "SKU", "stock_quantity": "Qty"}, [{"SKU": "SKU-1", "Qty": 1}, {"SKU": "SKU-1", "Qty": 2}], workspace_id, lookup)

    assert any("Duplicate customer" in issue.message for issue in customer.issues)
    assert any("Duplicate product" in issue.message for issue in product.issues)
    assert any("Duplicate variant" in issue.message for issue in variant.issues)
    assert any("Duplicate inventory" in issue.message for issue in inventory.issues)


def test_gitignore_protects_private_import_files() -> None:
    gitignore = Path("../.gitignore").read_text()

    for pattern in ["backend/storage/imports/", "backend/storage/test-files/", "backend/storage/private-imports/", "*.xlsx", "*.xls", "*.csv"]:
        assert pattern in gitignore


def test_tests_use_synthetic_excel_files_only(tmp_path) -> None:
    openpyxl = pytest.importorskip("openpyxl")
    Workbook = openpyxl.Workbook

    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Synthetic"
    sheet.append(["Customer", "Revenue"])
    sheet.append(["Test Customer", 1000])
    path = tmp_path / "synthetic.xlsx"
    workbook.save(path)

    columns, rows = ExcelParserService().read_rows(str(path), "Synthetic")

    assert columns == ["Customer", "Revenue"]
    assert rows == [{"Customer": "Test Customer", "Revenue": 1000}]


def test_owner_only_dry_run_access() -> None:
    workspace_id = uuid4()
    manager = SimpleNamespace(workspaces=[SimpleNamespace(workspace_id=workspace_id, workspace=SimpleNamespace(is_active=True), role=SimpleNamespace(name=RoleName.MANAGER.value))])
    guard = require_roles(RoleName.OWNER)

    with pytest.raises(HTTPException):
        guard(manager, workspace_id)


def test_workspace_isolation_during_dry_run(tmp_path) -> None:
    service = _import_service(tmp_path)
    job = service.jobs.job

    with pytest.raises(Exception):
        service.dry_run(uuid4(), job.id, "customers", "Customers", {"name": "Name"}, actor_user_id=uuid4())


def test_import_dry_run_supports_ad_metrics_with_synthetic_data(tmp_path) -> None:
    service = _import_service(tmp_path)
    job = service.jobs.job
    service.parser.rows = [{"Campaign": "Synthetic Campaign", "Date": "2026-06-01", "Spend": "100", "Impressions": "1000", "Clicks": "50", "Leads": "5", "Orders": "1", "Revenue": "250", "Profit": "75"}]
    service.lookup = SimpleNamespace(
        find_customer=lambda *args, **kwargs: None,
        find_product_by_sku=lambda *args, **kwargs: None,
        find_variant=lambda *args, **kwargs: None,
        find_ad_campaign_by_name=lambda *args, **kwargs: SimpleNamespace(id=uuid4()),
        find_ad_campaign_by_id=lambda *args, **kwargs: None,
        find_ad_metric_by_campaign_date=lambda *args, **kwargs: None,
    )

    report = service.dry_run(job.workspace_id, job.id, "ad_metrics", "Ads", {"campaign_name": "Campaign", "metric_date": "Date", "spend": "Spend", "impressions": "Impressions", "clicks": "Clicks", "leads": "Leads", "orders": "Orders", "revenue": "Revenue", "net_profit": "Profit"}, actor_user_id=uuid4())

    assert report.total_rows == 1
    assert report.ready_to_import_rows == 1
    assert report.error_rows == 0


def test_advertising_mapping_suggestion_uses_synthetic_columns_only() -> None:
    suggestion = MappingSuggestionService().suggest(["Кампанія", "Дата", "Витрати на рекламу", "Покази", "Охоплення", "Кліки", "Повідомлення", "Ліди", "Замовлення", "Виручка"], "ad_metrics")

    assert suggestion.suggested_mapping["campaign_name"] == "Кампанія"
    assert suggestion.suggested_mapping["metric_date"] == "Дата"
    assert suggestion.suggested_mapping["spend"] == "Витрати на рекламу"


def test_advertising_import_tests_use_only_synthetic_data() -> None:
    source = Path(__file__).read_text()
    private_filename = "Your " + "Jewelry (Shop).xlsx"

    assert private_filename not in source
    assert "Synthetic Campaign" in source
