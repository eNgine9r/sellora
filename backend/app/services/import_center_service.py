from collections import defaultdict
from datetime import UTC, date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from re import sub
from uuid import UUID

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.ad_campaign import AdCampaign
from app.models.ad_metric import AdMetric
from app.models.customer import Customer
from app.models.import_job import ImportJob, ImportJobStatus
from app.models.import_job_log import ImportJobLog, ImportJobLogStatus
from app.models.inventory import Inventory
from app.models.order import Order, OrderStatus, PaymentStatus
from app.models.product import Product
from app.models.product_variant import ProductVariant
from app.repositories.audit_log_repository import AuditLogRepository
from app.repositories.import_center_repository import ImportEntityLookupRepository, ImportJobLogRepository, ImportJobRepository
from app.schemas.import_center import ImportReportResponse, ImportValidationIssue, ImportValidationReport, SuggestMappingResponse, YourJewelryPresetResponse
from app.services.business_utils import snapshot

SUPPORTED_ENTITY_TYPES = {"customers", "products", "product_variants", "inventory", "orders", "ad_campaigns", "ad_metrics"}
YOUR_JEWELRY_SHEETS = ["Замовлення 2022-2025", "Аналітика Реклами 2023-2025", "Наявність на складі годинників", "Main Watchh інфа про товар"]
FIELD_ALIASES: dict[str, dict[str, list[str]]] = {
    "customers": {
        "name": ["Імʼя", "Ім'я", "Клієнт", "Customer", "Name", "name"],
        "phone": ["Телефон", "Phone", "customer_phone", "phone"],
        "instagram_username": ["Instagram", "Інстаграм", "instagram_username"],
        "city": ["Місто", "City", "city"],
        "region": ["Область", "Region", "region"],
    },
    "products": {
        "name": ["Назва", "Товар", "Product", "Product Name", "name"],
        "sku": ["Артикул", "SKU", "product_sku", "sku"],
        "description": ["Опис", "Description", "description"],
    },
    "product_variants": {
        "product_name": ["Товар", "Назва", "Product", "product_name"],
        "product_sku": ["Артикул товару", "product_sku"],
        "variant_sku": ["Модель годинника", "Модель", "variant_sku", "SKU", "Артикул"],
        "color": ["Колір", "Color", "color"],
        "size": ["Розмір", "Size", "size"],
        "selling_price": ["Ціна", "Selling Price", "selling_price"],
    },
    "inventory": {
        "variant_sku": ["Модель годинника", "Модель", "variant_sku", "SKU", "Артикул"],
        "stock_quantity": ["Залишок", "stock_quantity", "Кількість"],
        "reserved_quantity": ["Зарезервовано", "reserved_quantity"],
        "incoming_quantity": ["У дорозі", "incoming_quantity"],
        "minimum_quantity": ["Мінімальний залишок", "minimum_quantity"],
    },
    "ad_campaigns": {
        "name": ["Кампанія", "Campaign", "Campaign Name", "campaign_name", "name"],
        "platform": ["Платформа", "Platform", "platform"],
        "objective": ["Ціль", "Objective", "objective"],
        "budget_type": ["Тип бюджету", "Budget Type", "budget_type"],
        "daily_budget": ["Денний бюджет", "Daily Budget", "daily_budget"],
        "total_budget": ["Загальний бюджет", "Total Budget", "total_budget"],
        "start_date": ["Дата старту", "Start Date", "start_date"],
        "end_date": ["Дата завершення", "End Date", "end_date"],
        "notes": ["Нотатки", "Notes", "notes"],
    },
    "ad_metrics": {
        "campaign_name": ["Кампанія", "Campaign", "campaign_name"],
        "campaign_id": ["campaign_id"],
        "metric_date": ["Дата", "Date", "metric_date"],
        "spend": ["Витрати на рекламу", "Реклама", "Spend", "ad_spend", "spend"],
        "impressions": ["Покази", "Impressions", "impressions"],
        "reach": ["Охоплення", "Reach", "reach"],
        "clicks": ["Кліки", "Clicks", "clicks"],
        "messages": ["Повідомлення", "Звернення", "Direct", "Messages", "messages"],
        "leads": ["Ліди", "Leads", "leads"],
        "orders": ["Замовлення", "Orders", "orders"],
        "revenue": ["Виручка", "Дохід", "Revenue", "revenue"],
        "net_profit": ["Прибуток", "Profit", "net_profit"],
    },
    "orders": {
        "customer_name": ["Клієнт", "Customer", "customer_name"],
        "customer_phone": ["Телефон", "Phone", "customer_phone"],
        "instagram_username": ["Instagram", "instagram_username"],
        "created_at": ["Дата замовлення", "Дата", "Order Date", "created_at"],
        "order_date": ["Дата замовлення", "Дата", "Order Date", "order_date"],
        "revenue": ["Сума замовлення", "Сума", "Revenue", "revenue"],
        "order_total": ["Сума замовлення", "Сума", "Order Total", "order_total"],
        "net_profit": ["Прибуток", "Profit", "net_profit"],
        "ad_cost": ["Витрати на рекламу", "Реклама", "ad_cost"],
        "shipping_cost": ["Доставка", "Shipping", "shipping_cost"],
        "cod_fee": ["Накладений платіж", "cod_fee"],
        "other_cost": ["Інші витрати", "other_cost"],
        "city": ["Місто", "City", "city"],
        "region": ["Область", "Region", "region"],
        "product_variant_sku": ["Модель годинника", "Модель", "variant_sku"],
        "quantity": ["Кількість", "Quantity", "quantity"],
    },
}
YOUR_JEWELRY_EXCEL_V1 = {
    "name": "your_jewelry_excel_v1",
    "sheets": YOUR_JEWELRY_SHEETS,
    "mappings": {
        "customers": {"name": "Імʼя", "phone": "Телефон", "instagram_username": "Instagram", "city": "Місто", "region": "Область"},
        "products": {"name": "Назва", "sku": "Артикул", "description": "Опис"},
        "inventory": {"variant_sku": "Артикул", "stock_quantity": "Кількість", "minimum_quantity": "Мінімальний залишок"},
        "orders": {"customer_name": "Клієнт", "customer_phone": "Телефон", "revenue": "Сума", "created_at": "Дата", "city": "Місто", "region": "Область"},
        "ad_campaigns": {"name": "Кампанія", "platform": "Платформа", "objective": "Ціль"},
        "ad_metrics": {"campaign_name": "Кампанія", "metric_date": "Дата", "spend": "Витрати на рекламу", "impressions": "Покази", "reach": "Охоплення", "clicks": "Кліки", "messages": "Повідомлення", "leads": "Ліди", "orders": "Замовлення", "revenue": "Виручка", "net_profit": "Прибуток"},
    },
}


class ImportServiceError(ValueError):
    pass


class ExcelValueNormalizer:
    empty_tokens = {"", "-", "—", "–", "n/a", "none", "null"}

    def text(self, value) -> str | None:
        if value is None:
            return None
        if isinstance(value, str):
            cleaned = " ".join(value.strip().split())
            return None if cleaned.lower() in self.empty_tokens else cleaned
        return str(value).strip()

    def number(self, value) -> Decimal | None:
        if value is None:
            return None
        if isinstance(value, bool):
            return Decimal(int(value))
        if isinstance(value, int | float | Decimal):
            return Decimal(str(value))
        text = self.text(value)
        if text is None:
            return None
        text = text.replace("%", "")
        text = sub(r"[^0-9,\.\-]", "", text.replace(" ", ""))
        if text.count(",") == 1 and text.count(".") == 0:
            text = text.replace(",", ".")
        elif text.count(",") > 0 and text.count(".") > 0:
            text = text.replace(",", "")
        try:
            return Decimal(text)
        except (InvalidOperation, ValueError):
            return None

    def date(self, value) -> datetime | None:
        if value in (None, ""):
            return None
        if isinstance(value, datetime):
            return value if value.tzinfo else value.replace(tzinfo=UTC)
        if isinstance(value, date):
            return datetime(value.year, value.month, value.day, tzinfo=UTC)
        if isinstance(value, int | float) and value > 0:
            from datetime import timedelta
            # Excel serial dates use 1899-12-30 as the common epoch.
            return datetime(1899, 12, 30, tzinfo=UTC) + timedelta(days=float(value))
        text = self.text(value)
        if text is None:
            return None
        formats = ["%d.%m.%Y", "%d/%m/%Y", "%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%d.%m.%Y %H:%M:%S"]
        for fmt in formats:
            try:
                parsed = datetime.strptime(text, fmt)
                return parsed.replace(tzinfo=UTC)
            except ValueError:
                continue
        try:
            parsed = datetime.fromisoformat(text)
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
        except ValueError:
            return None

    def boolean(self, value) -> bool | None:
        text = self.text(value)
        if text is None:
            return None
        if text.lower() in {"true", "yes", "так", "1"}:
            return True
        if text.lower() in {"false", "no", "ні", "0"}:
            return False
        return None

    def percent(self, value) -> Decimal | None:
        number = self.number(value)
        return None if number is None else number / Decimal("100")


class ExcelParserService:
    def __init__(self) -> None:
        self.normalizer = ExcelValueNormalizer()

    def list_sheets(self, file_path: str) -> list[str]:
        from openpyxl import load_workbook
        workbook = load_workbook(file_path, read_only=True, data_only=True)
        try:
            return list(workbook.sheetnames)
        finally:
            workbook.close()

    def preview(self, file_path: str, sheet_name: str, limit: int = 20) -> tuple[list[str], list[dict]]:
        return self.read_rows(file_path, sheet_name, limit)

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
            columns = [self.normalizer.text(value) or f"column_{index + 1}" for index, value in enumerate(header)]
            rows: list[dict] = []
            for row in iterator:
                if limit is not None and len(rows) >= limit:
                    break
                if row is None or all(self.normalizer.text(value) is None for value in row):
                    continue
                rows.append({columns[index]: self._clean_cell(value) for index, value in enumerate(row[: len(columns)])})
            return columns, rows
        finally:
            workbook.close()

    def _clean_cell(self, value):
        if isinstance(value, datetime):
            return value.isoformat()
        return self.normalizer.text(value) if isinstance(value, str) else value


class MappingSuggestionService:
    def suggest(self, columns: list[str], entity_type: str) -> SuggestMappingResponse:
        aliases = FIELD_ALIASES.get(entity_type, {})
        suggested: dict[str, str] = {}
        confidence: dict[str, float] = {}
        normalized_columns = {normalize_name(column): column for column in columns}
        for field, field_aliases in aliases.items():
            best_column = None
            best_score = 0.0
            for alias in field_aliases + [field]:
                normalized_alias = normalize_name(alias)
                for normalized_column, original_column in normalized_columns.items():
                    score = 1.0 if normalized_column == normalized_alias else (0.75 if normalized_alias in normalized_column or normalized_column in normalized_alias else 0.0)
                    if score > best_score:
                        best_score = score
                        best_column = original_column
            if best_column and best_score >= 0.75:
                suggested[field] = best_column
                confidence[field] = best_score
        mapped_columns = set(suggested.values())
        required_missing = [", ".join(group) for group in MappingValidationService.required_groups.get(entity_type, []) if not any(field in suggested for field in group)]
        return SuggestMappingResponse(suggested_mapping=suggested, confidence=confidence, unmapped_columns=[column for column in columns if column not in mapped_columns], required_fields_missing=required_missing)

    def your_jewelry_preset(self) -> YourJewelryPresetResponse:
        return YourJewelryPresetResponse(
            preset_name="your_jewelry_excel_v1",
            supported_sheets=YOUR_JEWELRY_SHEETS,
            suggested_entity_type_per_sheet={
                "Замовлення 2022-2025": "orders",
                "Аналітика Реклами 2023-2025": "ad_metrics",
                "Наявність на складі годинників": "inventory",
                "Main Watchh інфа про товар": "products",
            },
            suggested_column_mapping_per_sheet={sheet: FIELD_ALIASES for sheet in YOUR_JEWELRY_SHEETS},
            notes=["Preset contains sheet and column aliases only.", "Preview and confirm mappings before import."],
        )


class MappingValidationService:
    required_groups = {
        "customers": [("name", "phone", "instagram_username")],
        "products": [("name",)],
        "product_variants": [("product_name", "product_sku"), ("variant_sku", "color", "size")],
        "inventory": [("variant_sku",), ("stock_quantity",)],
        "orders": [("customer_name", "customer_phone", "instagram_username"), ("revenue", "order_total"), ("created_at", "order_date")],
        "ad_campaigns": [("name",)],
        "ad_metrics": [("campaign_name", "campaign_id"), ("metric_date",)],
    }
    numeric_fields = {"stock_quantity", "reserved_quantity", "incoming_quantity", "minimum_quantity", "purchase_price", "shipping_cost", "selling_price", "weight", "quantity", "ad_cost", "cod_fee", "other_cost", "net_profit", "revenue", "order_total", "daily_budget", "total_budget", "spend", "impressions", "reach", "clicks", "messages", "leads", "orders"}
    non_negative_fields = {"stock_quantity", "reserved_quantity", "incoming_quantity", "minimum_quantity", "quantity", "daily_budget", "total_budget", "spend", "impressions", "reach", "clicks", "messages", "leads", "orders", "revenue", "order_total"}
    date_fields = {"created_at", "order_date", "metric_date", "start_date", "end_date"}

    def __init__(self) -> None:
        self.normalizer = ExcelValueNormalizer()

    def validate(self, entity_type: str, column_mapping: dict[str, str], rows: list[dict], workspace_id: UUID | None = None, lookup: ImportEntityLookupRepository | None = None) -> ImportValidationReport:
        issues: list[ImportValidationIssue] = []
        if entity_type not in SUPPORTED_ENTITY_TYPES:
            issues.append(issue(None, "ERROR", None, "Unsupported entity_type"))
            return report_from_issues(rows, issues)
        for group in self.required_groups[entity_type]:
            if not any(column_mapping.get(field) for field in group):
                issues.append(issue(None, "ERROR", None, f"Required mapping missing: one of {', '.join(group)}"))
        seen_inventory: set[str] = set()
        seen_ad_metrics: set[tuple[object, str]] = set()
        for row_number, row in enumerate(rows, start=2):
            mapped = map_row(row, column_mapping)
            normalized = self.normalized_row(mapped)
            issues.extend(self._row_required_issues(entity_type, row_number, normalized, mapped))
            for field in self.numeric_fields.intersection(mapped):
                raw = mapped.get(field)
                if raw in (None, ""):
                    continue
                number = self.normalizer.number(raw)
                if number is None:
                    issues.append(issue(row_number, "ERROR", field, f"{field} must be numeric", raw, None))
                elif field in self.non_negative_fields and number < 0:
                    issues.append(issue(row_number, "ERROR", field, f"{field} cannot be negative", raw, number))
            for field in self.date_fields.intersection(mapped):
                raw = mapped.get(field)
                if raw in (None, ""):
                    continue
                parsed = self.normalizer.date(raw)
                if parsed is None:
                    issues.append(issue(row_number, "ERROR", field, f"{field} must be a valid date", raw, None))
            if entity_type == "inventory" and normalized.get("variant_sku"):
                sku = str(normalized["variant_sku"])
                if sku in seen_inventory:
                    issues.append(issue(row_number, "WARNING", "variant_sku", "Duplicate inventory row for variant SKU", None, sku))
                seen_inventory.add(sku)
            if entity_type == "ad_metrics":
                metric_key = (normalized.get("campaign_id") or normalized.get("campaign_name"), str(normalized.get("metric_date")) if normalized.get("metric_date") else None)
                if all(metric_key) and metric_key in seen_ad_metrics:
                    issues.append(issue(row_number, "WARNING", "metric_date", "Duplicate ad metric row for campaign/date", None, metric_key[1]))
                if all(metric_key):
                    seen_ad_metrics.add(metric_key)
            if lookup and workspace_id:
                issues.extend(self._duplicate_issues(entity_type, row_number, normalized, lookup, workspace_id))
        return report_from_issues(rows, issues)

    def normalized_row(self, mapped: dict) -> dict:
        normalized = {}
        for field, value in mapped.items():
            if field in self.numeric_fields:
                normalized[field] = self.normalizer.number(value)
            elif field in self.date_fields:
                normalized[field] = self.normalizer.date(value)
            else:
                normalized[field] = self.normalizer.text(value)
        return normalized

    def _row_required_issues(self, entity_type: str, row_number: int, normalized: dict, mapped: dict) -> list[ImportValidationIssue]:
        issues: list[ImportValidationIssue] = []
        for group in self.required_groups[entity_type]:
            if not any(normalized.get(field) for field in group):
                issues.append(issue(row_number, "ERROR", "/".join(group), f"Row requires one of {', '.join(group)}"))
        return issues

    def _duplicate_issues(self, entity_type: str, row_number: int, normalized: dict, lookup: ImportEntityLookupRepository, workspace_id: UUID) -> list[ImportValidationIssue]:
        if entity_type == "customers" and lookup.find_customer(workspace_id, normalized.get("phone"), normalized.get("instagram_username")):
            return [issue(row_number, "WARNING", "customer", "Duplicate customer in workspace")]
        if entity_type == "products" and lookup.find_product_by_sku(workspace_id, normalized.get("sku")):
            return [issue(row_number, "WARNING", "sku", "Duplicate product SKU in workspace")]
        if entity_type == "product_variants" and lookup.find_variant(workspace_id, sku=normalized.get("variant_sku")):
            return [issue(row_number, "WARNING", "variant_sku", "Duplicate variant SKU in workspace")]
        if entity_type == "ad_campaigns" and lookup.find_ad_campaign_by_name(workspace_id, normalized.get("name")):
            return [issue(row_number, "WARNING", "name", "Duplicate ad campaign in workspace")]
        if entity_type == "ad_metrics":
            campaign = lookup.find_ad_campaign_by_id(workspace_id, normalized.get("campaign_id")) or lookup.find_ad_campaign_by_name(workspace_id, normalized.get("campaign_name"))
            if campaign and normalized.get("metric_date") and lookup.find_ad_metric_by_campaign_date(workspace_id, campaign.id, normalized.get("metric_date").date()):
                return [issue(row_number, "WARNING", "metric_date", "Duplicate ad metric in workspace")]
        return []


class EntityImportService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.lookup = ImportEntityLookupRepository(db)
        self.validator = MappingValidationService()

    def import_row(self, workspace_id: UUID, entity_type: str, raw_row: dict, column_mapping: dict[str, str]) -> tuple[ImportJobLogStatus, str]:
        data = self.validator.normalized_row(map_row(raw_row, column_mapping))
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
        if entity_type == "ad_campaigns":
            return self._ad_campaign(workspace_id, data)
        if entity_type == "ad_metrics":
            return self._ad_metric(workspace_id, data)
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
        variant = ProductVariant(workspace_id=workspace_id, product_id=product.id, sku=sku or f"{product.sku or product.name}-{data.get('color') or ''}-{data.get('size') or ''}", color=data.get("color"), size=data.get("size"), price=data.get("selling_price"))
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
        inventory.stock_quantity = int(data.get("stock_quantity") or 0)
        inventory.reserved_quantity = int(data.get("reserved_quantity") or 0)
        inventory.minimum_quantity = int(data.get("minimum_quantity") or 0)
        self.db.flush()
        return ImportJobLogStatus.SUCCESS, "Inventory updated"

    def _order(self, workspace_id: UUID, data: dict) -> tuple[ImportJobLogStatus, str]:
        customer = self.lookup.find_customer(workspace_id, data.get("customer_phone"), data.get("instagram_username"))
        revenue = data.get("revenue") or data.get("order_total")
        created_at = data.get("created_at") or data.get("order_date")
        if revenue is None or created_at is None:
            return ImportJobLogStatus.FAILED, "Order requires revenue/order_total and created_at/order_date"
        order = Order(workspace_id=workspace_id, order_number=f"IMP-{datetime.now(UTC).strftime('%Y%m%d%H%M%S%f')}", customer_id=customer.id if customer else None, status=OrderStatus.COMPLETED.value, payment_status=PaymentStatus.PAID.value, revenue=revenue, product_cost=Decimal("0"), ad_cost=data.get("ad_cost") or Decimal("0"), shipping_cost=data.get("shipping_cost") or Decimal("0"), cod_fee=data.get("cod_fee") or Decimal("0"), other_cost=data.get("other_cost") or Decimal("0"), net_profit=data.get("net_profit") or revenue, created_at=created_at, completed_at=created_at)
        self.db.add(order); self.db.flush()
        return ImportJobLogStatus.WARNING if customer is None else ImportJobLogStatus.SUCCESS, "Order created" if customer else "Order created without matched customer"

    def _ad_campaign(self, workspace_id: UUID, data: dict) -> tuple[ImportJobLogStatus, str]:
        if not data.get("name"):
            return ImportJobLogStatus.FAILED, "Ad campaign requires name"
        if self.lookup.find_ad_campaign_by_name(workspace_id, data.get("name")):
            return ImportJobLogStatus.SKIPPED, "Duplicate ad campaign skipped"
        campaign = AdCampaign(workspace_id=workspace_id, name=data["name"], platform=(data.get("platform") or "INSTAGRAM"), objective=(data.get("objective") or "MESSAGES"), budget_type=(data.get("budget_type") or "MANUAL"), daily_budget=data.get("daily_budget"), total_budget=data.get("total_budget"), start_date=data.get("start_date").date() if data.get("start_date") else None, end_date=data.get("end_date").date() if data.get("end_date") else None, notes=data.get("notes"))
        self.db.add(campaign); self.db.flush()
        return ImportJobLogStatus.SUCCESS, "Ad campaign created"

    def _ad_metric(self, workspace_id: UUID, data: dict) -> tuple[ImportJobLogStatus, str]:
        campaign = self.lookup.find_ad_campaign_by_id(workspace_id, data.get("campaign_id")) or self.lookup.find_ad_campaign_by_name(workspace_id, data.get("campaign_name"))
        if campaign is None:
            return ImportJobLogStatus.FAILED, "Ad campaign not found for metric"
        metric_date = data.get("metric_date")
        if metric_date is None:
            return ImportJobLogStatus.FAILED, "Ad metric requires metric_date"
        metric_date_value = metric_date.date()
        if self.lookup.find_ad_metric_by_campaign_date(workspace_id, campaign.id, metric_date_value):
            return ImportJobLogStatus.SKIPPED, "Duplicate ad metric skipped"
        metric = AdMetric(workspace_id=workspace_id, campaign_id=campaign.id, metric_date=metric_date_value, spend=data.get("spend") or Decimal("0"), impressions=int(data.get("impressions") or 0), reach=int(data.get("reach") or 0), clicks=int(data.get("clicks") or 0), messages=int(data.get("messages") or 0), leads=int(data.get("leads") or 0), orders=int(data.get("orders") or 0), revenue=data.get("revenue") or Decimal("0"), net_profit=data.get("net_profit") or Decimal("0"))
        self.db.add(metric); self.db.flush()
        return ImportJobLogStatus.SUCCESS, "Ad metric created"


class ImportService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.jobs = ImportJobRepository(db)
        self.logs = ImportJobLogRepository(db)
        self.parser = ExcelParserService()
        self.validator = MappingValidationService()
        self.suggestions = MappingSuggestionService()
        self.entity_importer = EntityImportService(db)
        self.lookup = ImportEntityLookupRepository(db)
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
        self.audit_logs.create(workspace_id=workspace_id, user_id=actor_user_id, entity_type="ImportJob", entity_id=job.id, action="IMPORT_UPLOAD", new_value=safe_job_snapshot(job))
        self.db.commit(); self.db.refresh(job); return job

    def list_sheets(self, workspace_id: UUID, job_id: UUID) -> list[str]:
        return self.parser.list_sheets(self._job(workspace_id, job_id).file_path)

    def preview(self, workspace_id: UUID, job_id: UUID, sheet_name: str, limit: int) -> tuple[list[str], list[dict]]:
        job = self._job(workspace_id, job_id)
        columns, rows = self.parser.preview(job.file_path, sheet_name, limit)
        job.status = ImportJobStatus.PREVIEWED.value
        self.db.commit()
        return columns, rows

    def suggest_mapping(self, workspace_id: UUID, job_id: UUID, sheet_name: str, entity_type: str) -> SuggestMappingResponse:
        job = self._job(workspace_id, job_id)
        columns, _rows = self.parser.preview(job.file_path, sheet_name, 1)
        return self.suggestions.suggest(columns, entity_type)

    def dry_run(self, workspace_id: UUID, job_id: UUID, entity_type: str, sheet_name: str, column_mapping: dict[str, str], actor_user_id: UUID | None = None) -> ImportReportResponse:
        job = self._job(workspace_id, job_id)
        _columns, rows = self.parser.read_rows(job.file_path, sheet_name)
        report = self.validator.validate(entity_type, column_mapping, rows, workspace_id, self.lookup)
        response = import_report(job.id, entity_type, sheet_name, rows, report)
        self.audit_logs.create(workspace_id=workspace_id, user_id=actor_user_id, entity_type="ImportJob", entity_id=job.id, action="IMPORT_DRY_RUN", new_value=response.model_dump(mode="json", exclude={"sample_errors", "sample_warnings"}))
        self.db.commit()
        return response

    def validate(self, workspace_id: UUID, job_id: UUID, entity_type: str, sheet_name: str, column_mapping: dict[str, str], actor_user_id: UUID | None) -> ImportValidationReport:
        job = self._job(workspace_id, job_id)
        _columns, rows = self.parser.read_rows(job.file_path, sheet_name)
        report = self.validator.validate(entity_type, column_mapping, rows, workspace_id, self.lookup)
        job.total_rows = report.total_rows
        if report.is_valid:
            job.status = ImportJobStatus.VALIDATED.value
        self.audit_logs.create(workspace_id=workspace_id, user_id=actor_user_id, entity_type="ImportJob", entity_id=job.id, action="IMPORT_VALIDATE", new_value={"is_valid": report.is_valid, "total_rows": report.total_rows, "errors": len(report.errors), "warnings": len(report.warnings)})
        self.db.commit()
        return report

    def execute(self, workspace_id: UUID, job_id: UUID, entity_type: str, sheet_name: str, column_mapping: dict[str, str], mode: str, actor_user_id: UUID | None, dry_run: bool = False):
        if dry_run:
            return self.dry_run(workspace_id, job_id, entity_type, sheet_name, column_mapping, actor_user_id)
        if mode != "create_only":
            raise ImportServiceError("Only create_only import mode is supported")
        job = self._job(workspace_id, job_id)
        _columns, rows = self.parser.read_rows(job.file_path, sheet_name)
        report = self.validator.validate(entity_type, column_mapping, rows, workspace_id, self.lookup)
        if report.error_rows if hasattr(report, "error_rows") else any(item.severity == "ERROR" for item in report.issues):
            job.status = ImportJobStatus.FAILED.value
            job.failed_rows = len(rows)
            self.audit_logs.create(workspace_id=workspace_id, user_id=actor_user_id, entity_type="ImportJob", entity_id=job.id, action="IMPORT_FAILED", new_value={"total_rows": len(rows), "errors": len(report.errors)})
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
        self.audit_logs.create(workspace_id=workspace_id, user_id=actor_user_id, entity_type="ImportJob", entity_id=job.id, action="IMPORT_COMPLETED" if job.success_rows else "IMPORT_FAILED", new_value=safe_job_snapshot(job))
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
    return ExcelValueNormalizer().number(value)


def parse_datetime(value) -> datetime | None:
    return ExcelValueNormalizer().date(value)


def normalize_name(value: str) -> str:
    return sub(r"[^\wа-яА-ЯіїєґІЇЄҐ]+", "", value.lower())


def issue(row_number: int | None, severity: str, field: str | None, message: str, raw_value=None, normalized_value=None) -> ImportValidationIssue:
    return ImportValidationIssue(row_number=row_number, severity=severity, field=field, message=message, raw_value=raw_value, normalized_value=normalized_value)


def report_from_issues(rows: list[dict], issues: list[ImportValidationIssue]) -> ImportValidationReport:
    errors = [item.message for item in issues if item.severity == "ERROR"]
    warnings = [item.message for item in issues if item.severity == "WARNING"]
    return ImportValidationReport(is_valid=not errors, total_rows=len(rows), errors=errors, warnings=warnings, issues=issues)


def import_report(job_id: UUID, entity_type: str, sheet_name: str, rows: list[dict], validation: ImportValidationReport) -> ImportReportResponse:
    issues_by_row: dict[int, list[ImportValidationIssue]] = defaultdict(list)
    for item in validation.issues:
        if item.row_number is not None:
            issues_by_row[item.row_number].append(item)
    error_rows = {row for row, issues in issues_by_row.items() if any(item.severity == "ERROR" for item in issues)}
    warning_rows = {row for row, issues in issues_by_row.items() if any(item.severity == "WARNING" for item in issues) and row not in error_rows}
    duplicate_rows = {row for row, issues in issues_by_row.items() if any("Duplicate" in item.message for item in issues)}
    skipped_rows = duplicate_rows
    ready = max(len(rows) - len(error_rows) - len(skipped_rows), 0)
    return ImportReportResponse(
        job_id=job_id,
        entity_type=entity_type,
        sheet_name=sheet_name,
        total_rows=len(rows),
        valid_rows=len(rows) - len(error_rows),
        warning_rows=len(warning_rows),
        error_rows=len(error_rows),
        skipped_rows=len(skipped_rows),
        duplicate_rows=len(duplicate_rows),
        ready_to_import_rows=ready,
        estimated_entities_to_create=ready,
        sample_errors=[item for item in validation.issues if item.severity == "ERROR"][:5],
        sample_warnings=[item for item in validation.issues if item.severity == "WARNING"][:5],
    )


def safe_job_snapshot(job: ImportJob) -> dict:
    data = snapshot(job)
    data.pop("file_path", None)
    return data
