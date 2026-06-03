from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from uuid import UUID

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.customer import Customer
from app.models.import_job import ImportJob, ImportJobStatus
from app.models.import_job_log import ImportJobLog, ImportJobLogStatus
from app.models.inventory import Inventory
from app.models.order import Order, OrderStatus, PaymentStatus
from app.models.product import Product
from app.models.product_variant import ProductVariant
from app.repositories.audit_log_repository import AuditLogRepository
from app.repositories.import_center_repository import ImportEntityLookupRepository, ImportJobLogRepository, ImportJobRepository
from app.schemas.import_center import ImportValidationReport
from app.services.business_utils import snapshot

SUPPORTED_ENTITY_TYPES = {"customers", "products", "product_variants", "inventory", "orders"}
YOUR_JEWELRY_EXCEL_V1 = {
    "name": "your_jewelry_excel_v1",
    "sheets": ["Замовлення 2022-2025", "Аналітика Реклами 2023-2025", "Наявність на складі годинників", "Main Watchh інфа про товар"],
    "mappings": {
        "customers": {"name": "Імʼя", "phone": "Телефон", "instagram_username": "Instagram", "city": "Місто", "region": "Область"},
        "products": {"name": "Назва", "sku": "Артикул", "description": "Опис"},
        "inventory": {"variant_sku": "Артикул", "stock_quantity": "Кількість", "minimum_quantity": "Мінімум"},
        "orders": {"customer_name": "Клієнт", "customer_phone": "Телефон", "revenue": "Сума", "created_at": "Дата", "city": "Місто", "region": "Область"},
    },
}


class ImportServiceError(ValueError):
    pass


class ExcelParserService:
    def list_sheets(self, file_path: str) -> list[str]:
        from openpyxl import load_workbook
        workbook = load_workbook(file_path, read_only=True, data_only=True)
        try:
            return list(workbook.sheetnames)
        finally:
            workbook.close()

    def preview(self, file_path: str, sheet_name: str, limit: int = 20) -> tuple[list[str], list[dict]]:
        columns, rows = self.read_rows(file_path, sheet_name, limit)
        return columns, rows

    def read_rows(self, file_path: str, sheet_name: str, limit: int | None = None) -> tuple[list[str], list[dict]]:
        from openpyxl import load_workbook
        workbook = load_workbook(file_path, read_only=True, data_only=True)
        try:
            if sheet_name not in workbook.sheetnames:
                raise ImportServiceError("Sheet not found")
            sheet = workbook[sheet_name]
            iterator = sheet.iter_rows(values_only=True)
            header = next(iterator, None)
            if not header:
                return [], []
            columns = [str(value).strip() if value is not None else f"column_{index + 1}" for index, value in enumerate(header)]
            rows: list[dict] = []
            for row in iterator:
                if limit is not None and len(rows) >= limit:
                    break
                if row is None or all(value is None for value in row):
                    continue
                rows.append({columns[index]: self._clean_cell(value) for index, value in enumerate(row[: len(columns)])})
            return columns, rows
        finally:
            workbook.close()

    def _clean_cell(self, value):
        if isinstance(value, datetime):
            return value.isoformat()
        return value


class MappingValidationService:
    required_groups = {
        "customers": [("name", "phone", "instagram_username")],
        "products": [("name",)],
        "product_variants": [("product_name", "product_sku"), ("variant_sku", "color", "size")],
        "inventory": [("variant_sku",), ("stock_quantity",)],
        "orders": [("customer_name", "customer_phone", "instagram_username"), ("revenue", "order_total"), ("created_at", "order_date")],
    }
    numeric_fields = {"stock_quantity", "reserved_quantity", "incoming_quantity", "minimum_quantity", "purchase_price", "shipping_cost", "selling_price", "weight", "quantity", "ad_cost", "cod_fee", "other_cost", "net_profit", "revenue", "order_total"}
    date_fields = {"created_at", "order_date"}

    def validate(self, entity_type: str, column_mapping: dict[str, str], rows: list[dict]) -> ImportValidationReport:
        errors: list[str] = []
        warnings: list[str] = []
        if entity_type not in SUPPORTED_ENTITY_TYPES:
            errors.append("Unsupported entity_type")
            return ImportValidationReport(is_valid=False, total_rows=len(rows), errors=errors, warnings=warnings)
        for group in self.required_groups[entity_type]:
            if not any(column_mapping.get(field) for field in group):
                errors.append(f"Required mapping missing: one of {', '.join(group)}")
        for row_number, row in enumerate(rows, start=2):
            mapped = map_row(row, column_mapping)
            for field in self.numeric_fields.intersection(mapped):
                if mapped.get(field) in (None, ""):
                    continue
                if parse_decimal(mapped[field]) is None:
                    errors.append(f"Row {row_number}: {field} must be numeric")
            for field in self.date_fields.intersection(mapped):
                if mapped.get(field) in (None, ""):
                    continue
                if parse_datetime(mapped[field]) is None:
                    errors.append(f"Row {row_number}: {field} must be a valid date")
        return ImportValidationReport(is_valid=not errors, total_rows=len(rows), errors=errors, warnings=warnings)


class EntityImportService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.lookup = ImportEntityLookupRepository(db)

    def import_row(self, workspace_id: UUID, entity_type: str, raw_row: dict, column_mapping: dict[str, str]) -> tuple[ImportJobLogStatus, str]:
        data = map_row(raw_row, column_mapping)
        if entity_type == "customers":
            return self._customer(workspace_id, data)
        if entity_type == "products":
            return self._product(workspace_id, data)
        if entity_type == "product_variants":
            return self._variant(workspace_id, data)
        if entity_type == "inventory":
            return self._inventory(workspace_id, data)
        if entity_type == "orders":
            return self._order(workspace_id, data)
        return ImportJobLogStatus.FAILED, "Unsupported entity type"

    def _customer(self, workspace_id: UUID, data: dict) -> tuple[ImportJobLogStatus, str]:
        if not any(data.get(field) for field in ("name", "phone", "instagram_username")):
            return ImportJobLogStatus.FAILED, "Customer requires name, phone, or instagram_username"
        if self.lookup.find_customer(workspace_id, data.get("phone"), data.get("instagram_username")):
            return ImportJobLogStatus.SKIPPED, "Duplicate customer skipped"
        self.db.add(Customer(workspace_id=workspace_id, name=data.get("name") or data.get("phone") or data.get("instagram_username"), phone=data.get("phone"), instagram_username=data.get("instagram_username"), city=data.get("city"), region=data.get("region")))
        self.db.flush()
        return ImportJobLogStatus.SUCCESS, "Customer created"

    def _product(self, workspace_id: UUID, data: dict) -> tuple[ImportJobLogStatus, str]:
        if not data.get("name"):
            return ImportJobLogStatus.FAILED, "Product requires name"
        if self.lookup.find_product_by_sku(workspace_id, data.get("sku")):
            return ImportJobLogStatus.SKIPPED, "Duplicate product skipped"
        self.db.add(Product(workspace_id=workspace_id, name=data["name"], sku=data.get("sku"), description=data.get("description")))
        self.db.flush()
        return ImportJobLogStatus.SUCCESS, "Product created"

    def _variant(self, workspace_id: UUID, data: dict) -> tuple[ImportJobLogStatus, str]:
        product = self.lookup.find_product_by_name_or_sku(workspace_id, data.get("product_name"), data.get("product_sku"))
        if product is None:
            return ImportJobLogStatus.FAILED, "Product not found for variant"
        sku = data.get("variant_sku")
        if self.lookup.find_variant(workspace_id, sku=sku, product_id=product.id, color=data.get("color"), size=data.get("size")):
            return ImportJobLogStatus.SKIPPED, "Duplicate variant skipped"
        variant = ProductVariant(workspace_id=workspace_id, product_id=product.id, sku=sku or f"{product.sku or product.name}-{data.get('color') or ''}-{data.get('size') or ''}", color=data.get("color"), size=data.get("size"), price=parse_decimal(data.get("selling_price")))
        self.db.add(variant); self.db.flush()
        self.db.add(Inventory(workspace_id=workspace_id, product_variant_id=variant.id, stock_quantity=0, reserved_quantity=0, minimum_quantity=0)); self.db.flush()
        return ImportJobLogStatus.SUCCESS, "Variant created"

    def _inventory(self, workspace_id: UUID, data: dict) -> tuple[ImportJobLogStatus, str]:
        variant = self.lookup.find_variant(workspace_id, sku=data.get("variant_sku"))
        if variant is None:
            return ImportJobLogStatus.FAILED, "Variant not found for inventory"
        inventory = self.lookup.inventory_by_variant(workspace_id, variant.id)
        if inventory is None:
            inventory = Inventory(workspace_id=workspace_id, product_variant_id=variant.id)
            self.db.add(inventory)
        inventory.stock_quantity = int(parse_decimal(data.get("stock_quantity")) or 0)
        inventory.reserved_quantity = int(parse_decimal(data.get("reserved_quantity")) or 0)
        inventory.minimum_quantity = int(parse_decimal(data.get("minimum_quantity")) or 0)
        self.db.flush()
        return ImportJobLogStatus.SUCCESS, "Inventory updated"

    def _order(self, workspace_id: UUID, data: dict) -> tuple[ImportJobLogStatus, str]:
        customer = self.lookup.find_customer(workspace_id, data.get("customer_phone"), data.get("instagram_username"))
        revenue = parse_decimal(data.get("revenue") or data.get("order_total"))
        created_at = parse_datetime(data.get("created_at") or data.get("order_date"))
        if revenue is None or created_at is None:
            return ImportJobLogStatus.FAILED, "Order requires revenue/order_total and created_at/order_date"
        order = Order(workspace_id=workspace_id, order_number=f"IMP-{datetime.now(UTC).strftime('%Y%m%d%H%M%S%f')}", customer_id=customer.id if customer else None, status=OrderStatus.COMPLETED.value, payment_status=PaymentStatus.PAID.value, revenue=revenue, product_cost=Decimal("0"), ad_cost=parse_decimal(data.get("ad_cost")) or Decimal("0"), shipping_cost=parse_decimal(data.get("shipping_cost")) or Decimal("0"), cod_fee=parse_decimal(data.get("cod_fee")) or Decimal("0"), other_cost=parse_decimal(data.get("other_cost")) or Decimal("0"), net_profit=parse_decimal(data.get("net_profit")) or revenue, created_at=created_at, completed_at=created_at)
        self.db.add(order); self.db.flush()
        return ImportJobLogStatus.WARNING if customer is None else ImportJobLogStatus.SUCCESS, "Order created" if customer else "Order created without matched customer"


class ImportService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.jobs = ImportJobRepository(db)
        self.logs = ImportJobLogRepository(db)
        self.parser = ExcelParserService()
        self.validator = MappingValidationService()
        self.entity_importer = EntityImportService(db)
        self.audit_logs = AuditLogRepository(db)

    async def upload(self, workspace_id: UUID, file: UploadFile, actor_user_id: UUID | None) -> ImportJob:
        safe_name = self._safe_filename(file.filename or "import.xlsx")
        if not safe_name.lower().endswith(".xlsx"):
            raise ImportServiceError("Only .xlsx files are supported")
        content = await file.read()
        if len(content) > get_settings().import_max_file_size_mb * 1024 * 1024:
            raise ImportServiceError("Import file exceeds size limit")
        job = self.jobs.create(ImportJob(workspace_id=workspace_id, file_name=safe_name, file_type="xlsx", file_path="pending", status=ImportJobStatus.UPLOADED.value, created_by=actor_user_id))
        directory = Path(get_settings().import_storage_path) / str(workspace_id) / str(job.id)
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / safe_name
        path.write_bytes(content)
        job.file_path = str(path)
        self.audit_logs.create(workspace_id=workspace_id, user_id=actor_user_id, entity_type="ImportJob", entity_id=job.id, action="IMPORT_UPLOAD", new_value=snapshot(job))
        self.db.commit(); self.db.refresh(job); return job

    def list_sheets(self, workspace_id: UUID, job_id: UUID) -> list[str]:
        return self.parser.list_sheets(self._job(workspace_id, job_id).file_path)

    def preview(self, workspace_id: UUID, job_id: UUID, sheet_name: str, limit: int) -> tuple[list[str], list[dict]]:
        job = self._job(workspace_id, job_id)
        columns, rows = self.parser.preview(job.file_path, sheet_name, limit)
        job.status = ImportJobStatus.PREVIEWED.value
        self.db.commit()
        return columns, rows

    def validate(self, workspace_id: UUID, job_id: UUID, entity_type: str, sheet_name: str, column_mapping: dict[str, str], actor_user_id: UUID | None) -> ImportValidationReport:
        job = self._job(workspace_id, job_id)
        _columns, rows = self.parser.read_rows(job.file_path, sheet_name)
        report = self.validator.validate(entity_type, column_mapping, rows)
        job.total_rows = report.total_rows
        if report.is_valid:
            job.status = ImportJobStatus.VALIDATED.value
        self.audit_logs.create(workspace_id=workspace_id, user_id=actor_user_id, entity_type="ImportJob", entity_id=job.id, action="IMPORT_VALIDATE", new_value=report.model_dump())
        self.db.commit()
        return report

    def execute(self, workspace_id: UUID, job_id: UUID, entity_type: str, sheet_name: str, column_mapping: dict[str, str], mode: str, actor_user_id: UUID | None) -> ImportJob:
        if mode != "create_only":
            raise ImportServiceError("Only create_only import mode is supported")
        job = self._job(workspace_id, job_id)
        _columns, rows = self.parser.read_rows(job.file_path, sheet_name)
        report = self.validator.validate(entity_type, column_mapping, rows)
        if not report.is_valid:
            job.status = ImportJobStatus.FAILED.value
            job.failed_rows = len(rows)
            self.audit_logs.create(workspace_id=workspace_id, user_id=actor_user_id, entity_type="ImportJob", entity_id=job.id, action="IMPORT_FAILED", new_value=report.model_dump())
            self.db.commit()
            raise ImportServiceError("Import mapping is invalid")
        job.status = ImportJobStatus.IMPORTING.value
        job.total_rows = len(rows)
        job.processed_rows = job.processed_rows or 0
        job.success_rows = job.success_rows or 0
        job.failed_rows = job.failed_rows or 0
        self.audit_logs.create(workspace_id=workspace_id, user_id=actor_user_id, entity_type="ImportJob", entity_id=job.id, action="IMPORT_EXECUTE", new_value={"entity_type": entity_type, "rows": len(rows)})
        for index, row in enumerate(rows, start=2):
            status, message = self.entity_importer.import_row(workspace_id, entity_type, row, column_mapping)
            self.logs.create(ImportJobLog(workspace_id=workspace_id, import_job_id=job.id, row_number=index, entity_type=entity_type, status=status.value, message=message, raw_data=row))
            job.processed_rows += 1
            if status == ImportJobLogStatus.SUCCESS:
                job.success_rows += 1
            elif status == ImportJobLogStatus.FAILED:
                job.failed_rows += 1
        job.completed_at = datetime.now(UTC)
        job.status = ImportJobStatus.COMPLETED.value if job.failed_rows == 0 else (ImportJobStatus.FAILED.value if job.success_rows == 0 else ImportJobStatus.PARTIALLY_COMPLETED.value)
        self.audit_logs.create(workspace_id=workspace_id, user_id=actor_user_id, entity_type="ImportJob", entity_id=job.id, action="IMPORT_COMPLETED" if job.success_rows else "IMPORT_FAILED", new_value=snapshot(job))
        self.db.commit(); self.db.refresh(job); return job

    def list_logs(self, workspace_id: UUID, job_id: UUID, status: str | None = None) -> list[ImportJobLog]:
        self._job(workspace_id, job_id)
        return self.logs.list(workspace_id, job_id, status)

    def _job(self, workspace_id: UUID, job_id: UUID) -> ImportJob:
        job = self.jobs.get(workspace_id, job_id)
        if job is None:
            raise ImportServiceError("Import job not found")
        return job

    def _safe_filename(self, filename: str) -> str:
        return Path(filename).name.replace("/", "_").replace("\\", "_")


def map_row(raw_row: dict, column_mapping: dict[str, str]) -> dict:
    return {field: raw_row.get(column) for field, column in column_mapping.items() if column}


def parse_decimal(value) -> Decimal | None:
    if value in (None, ""):
        return None
    try:
        return Decimal(str(value).replace(",", "."))
    except (InvalidOperation, ValueError):
        return None


def parse_datetime(value) -> datetime | None:
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    try:
        parsed = datetime.fromisoformat(str(value))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
    except ValueError:
        return None
