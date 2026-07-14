#!/usr/bin/env python3
from __future__ import annotations

import csv
import io
import json
import os
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable

import httpx

API = os.getenv("STAGING_API_URL", "https://sellora-api-staging.onrender.com").rstrip("/")
EXPECTED_COMMIT = os.getenv("EXPECTED_RUNTIME_COMMIT", "96a95bca5e378d6dc6da5e6d9bddbb96d935d3b4")
WORKSPACE_A = os.environ["STAGING_TEST_WORKSPACE_ID"]
WORKSPACE_B = "56e8a724-782a-4494-a3a7-0bbf7deb03b7"
PHASE_A_JOB = "e0b6cd02-4272-40cb-ad4c-9084c2a35dff"
OUT = Path("artifacts/sprint-8c-phase-b-core.json")


def csv_bytes(headers: list[str], rows: list[list[Any]]) -> bytes:
    stream = io.StringIO(newline="")
    writer = csv.writer(stream)
    writer.writerow(headers)
    writer.writerows(rows)
    return stream.getvalue().encode("utf-8")


def required(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required input: {name}")
    return value


def safe_detail(response: httpx.Response) -> str:
    try:
        body = response.json()
        detail = body.get("detail") if isinstance(body, dict) else None
        return str(detail or f"HTTP {response.status_code}")[:400]
    except Exception:
        return f"HTTP {response.status_code}"


def request_retry(operation: Callable[[], httpx.Response], attempts: int = 6) -> httpx.Response:
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            response = operation()
            if response.status_code < 500:
                return response
        except (httpx.TimeoutException, httpx.NetworkError) as exc:
            last_error = exc
        if attempt < attempts:
            time.sleep(min(attempt * 5, 20))
    if last_error:
        raise last_error
    return operation()


class Closure:
    def __init__(self) -> None:
        self.result: dict[str, Any] = {
            "phase": "B-core",
            "decision": "FAIL",
            "runtime": {},
            "checks": [],
            "jobs": {},
            "timings_seconds": {},
            "safe_error": None,
        }
        self.timeout = httpx.Timeout(connect=30, read=600, write=600, pool=30)
        self.client = httpx.Client(timeout=self.timeout, follow_redirects=True)
        self.owner_token = ""
        self.suffix = datetime.now(UTC).strftime("%m%d%H%M%S").lower()

    def close(self) -> None:
        self.client.close()

    def check(self, name: str, condition: bool, detail: str = "") -> None:
        self.result["checks"].append({"name": name, "status": "PASS" if condition else "FAIL", "detail": detail[:400]})
        if not condition:
            raise RuntimeError(f"Gate failed: {name}")

    def wait_runtime(self) -> None:
        deadline = time.monotonic() + 25 * 60
        last = "unavailable"
        while time.monotonic() < deadline:
            try:
                response = self.client.get(f"{API}/health")
                if response.status_code == 200:
                    body = response.json()
                    last = str(body.get("runtime_commit") or "legacy")
                    if last.startswith(EXPECTED_COMMIT[:12]) and body.get("process_started_at"):
                        self.result["runtime"] = {
                            "runtime_commit": last,
                            "process_started_at": body["process_started_at"],
                        }
                        self.check("new identified Render process", True)
                        self.check("restart commit boundary", last.startswith(EXPECTED_COMMIT[:12]))
                        return
            except Exception:
                last = "health-unavailable"
            time.sleep(15)
        raise RuntimeError(f"Expected runtime not observed; last marker {last[:20]}")

    def login(self, role: str) -> str:
        response = request_retry(lambda: self.client.post(
            f"{API}/api/v1/auth/login",
            json={"email": required(f"STAGING_{role}_EMAIL"), "password": required(f"STAGING_{role}_PASSWORD")},
        ))
        self.check(f"{role} login", response.status_code == 200, safe_detail(response))
        token = response.json().get("access_token")
        self.check(f"{role} access token present", bool(token))
        return token

    def headers(self, workspace_id: str = WORKSPACE_A, token: str | None = None) -> dict[str, str]:
        return {"Authorization": f"Bearer {token or self.owner_token}", "X-Workspace-ID": workspace_id}

    def upload(self, name: str, content: bytes, mime: str = "text/csv", workspace_id: str = WORKSPACE_A) -> tuple[httpx.Response, str | None]:
        response = request_retry(lambda: self.client.post(
            f"{API}/api/v1/import/upload",
            headers=self.headers(workspace_id),
            files={"file": (name, content, mime)},
        ))
        job_id = str(response.json().get("job_id")) if response.status_code == 201 else None
        return response, job_id

    def import_flow(
        self,
        label: str,
        entity_type: str,
        content: bytes,
        mapping: dict[str, str],
        options: dict[str, Any] | None = None,
        execute: bool = True,
    ) -> dict[str, Any]:
        started = time.perf_counter()
        upload, job_id = self.upload(f"qa8c-{label}-{self.suffix}.csv", content)
        self.check(f"{label}: upload", upload.status_code == 201, safe_detail(upload))
        assert job_id
        self.result["jobs"][label] = job_id
        sheets = request_retry(lambda: self.client.get(f"{API}/api/v1/import/{job_id}/sheets", headers=self.headers()))
        self.check(f"{label}: sheet selection", sheets.status_code == 200 and sheets.json().get("sheets") == ["CSV"], safe_detail(sheets))
        preview = request_retry(lambda: self.client.post(
            f"{API}/api/v1/import/{job_id}/preview", headers=self.headers(), json={"sheet_name": "CSV", "limit": 20}
        ))
        self.check(f"{label}: preview", preview.status_code == 200, safe_detail(preview))
        payload = {"entity_type": entity_type, "sheet_name": "CSV", "column_mapping": mapping, "options": options}
        validation = request_retry(lambda: self.client.post(f"{API}/api/v1/import/{job_id}/validate", headers=self.headers(), json=payload))
        self.check(f"{label}: validation HTTP", validation.status_code == 200, safe_detail(validation))
        self.check(f"{label}: validation valid", validation.json().get("is_valid") is True, json.dumps(validation.json())[:300])
        dry_started = time.perf_counter()
        dry = request_retry(lambda: self.client.post(f"{API}/api/v1/import/{job_id}/dry-run", headers=self.headers(), json=payload))
        dry_seconds = time.perf_counter() - dry_started
        self.check(f"{label}: dry-run HTTP", dry.status_code == 200, safe_detail(dry))
        dry_data = dry.json()
        self.check(f"{label}: dry-run safe", dry_data.get("error_rows") == 0, json.dumps(dry_data)[:300])
        execution: dict[str, Any] | None = None
        execute_seconds = 0.0
        if execute:
            exec_payload = {**payload, "mode": "create_only", "dry_run": False}
            exec_started = time.perf_counter()
            executed = request_retry(lambda: self.client.post(f"{API}/api/v1/import/{job_id}/execute", headers=self.headers(), json=exec_payload), attempts=2)
            execute_seconds = time.perf_counter() - exec_started
            self.check(f"{label}: execute", executed.status_code == 200, safe_detail(executed))
            execution = executed.json()
            self.check(f"{label}: completed", execution.get("job", {}).get("status") == "COMPLETED", json.dumps(execution)[:300])
            logs = request_retry(lambda: self.client.get(f"{API}/api/v1/import/{job_id}/logs", headers=self.headers()))
            self.check(f"{label}: logs", logs.status_code == 200, safe_detail(logs))
            self.check(f"{label}: logs sanitized", all(item.get("raw_data") is None for item in logs.json()))
        self.result["timings_seconds"][label] = {
            "total": round(time.perf_counter() - started, 3),
            "dry_run": round(dry_seconds, 3),
            "execute": round(execute_seconds, 3),
        }
        return {"job_id": job_id, "dry": dry_data, "execution": execution, "payload": payload}

    def invalid_upload(self, label: str, filename: str, content: bytes, mime: str) -> None:
        response, _job = self.upload(filename, content, mime)
        detail = safe_detail(response)
        self.check(f"invalid {label}: rejected", response.status_code == 400, detail)
        lowered = detail.lower()
        self.check(f"invalid {label}: no stack/sql leak", not any(term in lowered for term in ("traceback", "sqlalchemy", "postgresql", "select ", "insert ")))

    def invalid_dry_run(self, label: str, content: bytes, entity_type: str, mapping: dict[str, str], expected_field: str | None = None) -> None:
        upload, job_id = self.upload(f"qa8c-invalid-{label}-{self.suffix}.csv", content)
        self.check(f"invalid {label}: upload", upload.status_code == 201, safe_detail(upload))
        assert job_id
        request_retry(lambda: self.client.post(f"{API}/api/v1/import/{job_id}/preview", headers=self.headers(), json={"sheet_name": "CSV", "limit": 20}))
        payload = {"entity_type": entity_type, "sheet_name": "CSV", "column_mapping": mapping, "options": None}
        dry = request_retry(lambda: self.client.post(f"{API}/api/v1/import/{job_id}/dry-run", headers=self.headers(), json=payload))
        self.check(f"invalid {label}: dry-run response", dry.status_code in {200, 400}, safe_detail(dry))
        if dry.status_code == 200:
            body = dry.json()
            self.check(f"invalid {label}: execute unavailable", body.get("error_rows", 0) > 0)
            issues = body.get("sample_errors", []) + [item for values in body.get("errors_by_row", {}).values() for item in values]
            self.check(f"invalid {label}: row evidence", any(item.get("row_number") is not None for item in issues))
            if expected_field:
                self.check(f"invalid {label}: column evidence", any(item.get("field") == expected_field for item in issues))
        else:
            self.check(f"invalid {label}: safe 400", "traceback" not in safe_detail(dry).lower())

    def run(self) -> int:
        self.wait_runtime()
        self.owner_token = self.login("OWNER")
        manager = self.login("MANAGER")
        analyst = self.login("ANALYST")

        # Gate 2: execute the exact Phase A job after a real identified process boundary.
        phase_a_payload = {
            "entity_type": "customers", "sheet_name": "CSV",
            "column_mapping": {"name": "Name", "phone": "Phone", "instagram_username": "Instagram"},
            "mode": "create_only", "dry_run": False, "options": {"duplicate_policy": "SKIP"},
        }
        restarted_execute = request_retry(lambda: self.client.post(
            f"{API}/api/v1/import/{PHASE_A_JOB}/execute", headers=self.headers(), json=phase_a_payload
        ), attempts=2)
        self.check("restart-boundary execute", restarted_execute.status_code == 200, safe_detail(restarted_execute))
        self.check("persisted approval survived restart", restarted_execute.json().get("job", {}).get("status") == "COMPLETED")
        phase_a_logs = request_retry(lambda: self.client.get(f"{API}/api/v1/import/{PHASE_A_JOB}/logs", headers=self.headers()))
        self.check("restart job logs", phase_a_logs.status_code == 200)
        self.check("restart job raw rows absent", all(item.get("raw_data") is None for item in phase_a_logs.json()))
        cross_logs = request_retry(lambda: self.client.get(f"{API}/api/v1/import/{PHASE_A_JOB}/logs", headers=self.headers(WORKSPACE_B)))
        self.check("cross-workspace log visibility zero", cross_logs.status_code in {400, 404})
        phase_a_customers = request_retry(lambda: self.client.get(f"{API}/api/v1/customers", headers=self.headers(), params={"search": "QA8C Restart Customer"}))
        self.check("restart entities visible in Workspace A", phase_a_customers.status_code == 200 and len(phase_a_customers.json()) == 2)
        phase_a_customers_b = request_retry(lambda: self.client.get(f"{API}/api/v1/customers", headers=self.headers(WORKSPACE_B), params={"search": "QA8C Restart Customer"}))
        self.check("restart entities absent in Workspace B", phase_a_customers_b.status_code == 200 and len(phase_a_customers_b.json()) == 0)

        # Runtime RBAC is rechecked on the new process.
        manager_upload = self.client.post(f"{API}/api/v1/import/upload", headers=self.headers(token=manager), files={"file": ("denied.csv", b"Name\nDenied\n", "text/csv")})
        analyst_upload = self.client.post(f"{API}/api/v1/import/upload", headers=self.headers(token=analyst), files={"file": ("denied.csv", b"Name\nDenied\n", "text/csv")})
        self.check("MANAGER mutation denied after restart", manager_upload.status_code == 403)
        self.check("ANALYST mutation denied after restart", analyst_upload.status_code == 403)

        s = self.suffix
        product_name = f"QA8C Product {s}"
        product_sku = f"QA8C-P-{s}"
        variant_sku = f"QA8C-V-{s}"
        campaign_name = f"QA8C Campaign {s}"
        order_number = f"QA8C-ORD-{s}"

        customers_content = csv_bytes(["Name", "Phone", "Instagram"], [[f"QA8C Customer {s}", f"38099{s[-7:]}", f"qa8c_customer_{s}"]])
        customers = self.import_flow("customers", "customers", customers_content, {"name": "Name", "phone": "Phone", "instagram_username": "Instagram"})
        products_content = csv_bytes(["Name", "SKU", "Description"], [[product_name, product_sku, "Synthetic Sprint 8C product"]])
        products = self.import_flow("products", "products", products_content, {"name": "Name", "sku": "SKU", "description": "Description"})
        variants_content = csv_bytes(["Product SKU", "Variant SKU", "Color", "Size", "Selling Price"], [[product_sku, variant_sku, "Black", "M", "999"]])
        variants = self.import_flow("variants", "product_variants", variants_content, {"product_sku": "Product SKU", "variant_sku": "Variant SKU", "color": "Color", "size": "Size", "selling_price": "Selling Price"})
        inventory_content = csv_bytes(["Variant SKU", "Stock", "Reserved", "Minimum"], [[variant_sku, "25", "0", "3"]])
        inventory = self.import_flow("inventory", "inventory", inventory_content, {"variant_sku": "Variant SKU", "stock_quantity": "Stock", "reserved_quantity": "Reserved", "minimum_quantity": "Minimum"})
        self.check("inventory dry-run reports update", inventory["dry"].get("updated_count") == 1 and inventory["dry"].get("created_count") == 0, json.dumps(inventory["dry"])[:300])

        orders_headers = ["Order Number", "Order Date", "Customer Name", "Customer Phone", "Instagram", "Variant SKU", "Quantity", "Unit Price", "Unit Cost", "Payment Status", "Order Status", "Tracking Number", "Carrier", "City", "Warehouse"]
        orders_row = [order_number, "2026-07-01", f"QA8C Historical {s}", f"38088{s[-7:]}", f"qa8c_order_{s}", variant_sku, "1", "799", "300", "paid", "completed", f"TTN-{s}", "NOVA_POSHTA", "Synthetic City", "Synthetic Warehouse"]
        orders_mapping = {"order_number": "Order Number", "order_date": "Order Date", "customer_name": "Customer Name", "customer_phone": "Customer Phone", "instagram_username": "Instagram", "variant_sku": "Variant SKU", "quantity": "Quantity", "unit_price": "Unit Price", "unit_cost": "Unit Cost", "payment_status": "Payment Status", "order_status": "Order Status", "tracking_number": "Tracking Number", "carrier": "Carrier", "city": "City", "warehouse": "Warehouse"}
        shipments_before = request_retry(lambda: self.client.get(f"{API}/api/v1/shipments", headers=self.headers())).json()
        inventory_before_order = request_retry(lambda: self.client.get(f"{API}/api/v1/inventory", headers=self.headers())).json()
        orders = self.import_flow("orders-history", "orders_history", csv_bytes(orders_headers, [orders_row]), orders_mapping, {"affect_inventory": False})
        shipments_after = request_retry(lambda: self.client.get(f"{API}/api/v1/shipments", headers=self.headers())).json()
        inventory_after_order = request_retry(lambda: self.client.get(f"{API}/api/v1/inventory", headers=self.headers())).json()
        self.check("historical order created no shipment", len(shipments_after) == len(shipments_before))
        self.check("historical order did not alter stock", inventory_after_order == inventory_before_order)

        ads_headers = ["Campaign Name", "Platform", "Date", "Spend", "Impressions", "Reach", "Clicks", "Messages", "Leads", "Orders", "Revenue", "Net Profit"]
        ads_row = [campaign_name, "INSTAGRAM", "2026-07-01", "120", "10000", "8000", "300", "40", "20", "5", "3995", "1200"]
        ads_mapping = {"campaign_name": "Campaign Name", "platform": "Platform", "metric_date": "Date", "spend": "Spend", "impressions": "Impressions", "reach": "Reach", "clicks": "Clicks", "messages": "Messages", "leads": "Leads", "orders": "Orders", "revenue": "Revenue", "net_profit": "Net Profit"}
        ads = self.import_flow("advertising-history", "advertising_history", csv_bytes(ads_headers, [ads_row]), ads_mapping)

        # Shipments are truthfully unsupported in the controlled pilot.
        ship_content = csv_bytes(["Order Number", "Tracking Number"], [[order_number, f"SHIP-{s}"]])
        ship_upload, ship_job = self.upload(f"qa8c-shipments-{s}.csv", ship_content)
        self.check("shipments unsupported upload accepted for inspection", ship_upload.status_code == 201)
        ship_dry = self.client.post(f"{API}/api/v1/import/{ship_job}/dry-run", headers=self.headers(), json={"entity_type": "shipments", "sheet_name": "CSV", "column_mapping": {"order_number": "Order Number", "tracking_number": "Tracking Number"}, "options": None})
        self.check("shipments explicitly unsupported", ship_dry.status_code == 400 and "not supported" in safe_detail(ship_dry).lower(), safe_detail(ship_dry))

        # Duplicate rerun matrix.
        duplicate_cases = [
            ("duplicate-customers", "customers", customers_content, {"name": "Name", "phone": "Phone", "instagram_username": "Instagram"}, None, "duplicate_rows", 1),
            ("duplicate-products", "products", products_content, {"name": "Name", "sku": "SKU", "description": "Description"}, None, "duplicate_rows", 1),
            ("duplicate-variants", "product_variants", variants_content, {"product_sku": "Product SKU", "variant_sku": "Variant SKU", "color": "Color", "size": "Size", "selling_price": "Selling Price"}, None, "duplicate_rows", 1),
            ("duplicate-orders", "orders_history", csv_bytes(orders_headers, [orders_row]), orders_mapping, {"affect_inventory": False}, "duplicate_orders", 1),
            ("duplicate-advertising", "advertising_history", csv_bytes(ads_headers, [ads_row]), ads_mapping, None, "duplicate_metrics", 1),
        ]
        duplicate_results: dict[str, Any] = {}
        for label, entity, content, mapping, options, metric, expected in duplicate_cases:
            duplicate_results[label] = self.import_flow(label, entity, content, mapping, options)
            self.check(f"{label}: planned duplicate behavior", duplicate_results[label]["dry"].get(metric, 0) >= expected, json.dumps(duplicate_results[label]["dry"])[:300])
        duplicate_inventory = self.import_flow("duplicate-inventory", "inventory", inventory_content, {"variant_sku": "Variant SKU", "stock_quantity": "Stock", "reserved_quantity": "Reserved", "minimum_quantity": "Minimum"})
        self.check("duplicate inventory planned as absolute update", duplicate_inventory["dry"].get("updated_count") == 1 and duplicate_inventory["dry"].get("created_count") == 0)
        inventory_final = request_retry(lambda: self.client.get(f"{API}/api/v1/inventory", headers=self.headers())).json()
        matching_inventory = [item for item in inventory_final if str(item.get("stock_quantity")) == "25"]
        self.check("opening stock not multiplied", bool(matching_inventory))

        # Invalid upload matrix.
        self.invalid_upload("corrupted XLSX", "corrupted.xlsx", b"PK-not-a-real-workbook", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        self.invalid_upload("binary CSV", "binary.csv", b"Name\x00Phone\n", "text/csv")
        self.invalid_upload("non-UTF8 CSV", "nonutf8.csv", b"\xff\xfe\xfd", "text/csv")
        self.invalid_upload("oversized metadata", "oversized.csv", b"Name\n" + b"A" * (10 * 1024 * 1024 + 1), "text/csv")

        dup_header_upload, dup_header_job = self.upload(f"duplicate-headers-{s}.csv", b"Name,Name\nA,B\n")
        self.check("duplicate headers upload", dup_header_upload.status_code == 201)
        dup_header_preview = self.client.post(f"{API}/api/v1/import/{dup_header_job}/preview", headers=self.headers(), json={"sheet_name": "CSV", "limit": 20})
        self.check("duplicate headers rejected", dup_header_preview.status_code == 400 and "duplicate" in safe_detail(dup_header_preview).lower(), safe_detail(dup_header_preview))

        self.invalid_dry_run("invalid-number", csv_bytes(["Variant SKU", "Stock"], [[variant_sku, "abc"]]), "inventory", {"variant_sku": "Variant SKU", "stock_quantity": "Stock"}, "stock_quantity")
        self.invalid_dry_run("negative-stock", csv_bytes(["Variant SKU", "Stock"], [[variant_sku, "-5"]]), "inventory", {"variant_sku": "Variant SKU", "stock_quantity": "Stock"}, "stock_quantity")
        invalid_order_row = list(orders_row); invalid_order_row[1] = "not-a-date"
        self.invalid_dry_run("invalid-date", csv_bytes(orders_headers, [invalid_order_row]), "orders_history", orders_mapping, "order_date")
        invalid_status_row = list(orders_row); invalid_status_row[0] = f"QA8C-BAD-{s}"; invalid_status_row[10] = "mystery-status"
        self.invalid_dry_run("unsupported-status", csv_bytes(orders_headers, [invalid_status_row]), "orders_history", orders_mapping, "order_status")
        self.invalid_dry_run("formula-value", csv_bytes(["Name", "Instagram"], [["=2+2", f"qa8c_formula_{s}"]]), "customers", {"name": "Name", "instagram_username": "Instagram"}, "name")

        # Missing mapping is a global validation error; no execute approval is created.
        missing_upload, missing_job = self.upload(f"missing-mapping-{s}.csv", csv_bytes(["Value"], [["QA"]]))
        self.check("missing mapping upload", missing_upload.status_code == 201)
        missing_dry = self.client.post(f"{API}/api/v1/import/{missing_job}/dry-run", headers=self.headers(), json={"entity_type": "customers", "sheet_name": "CSV", "column_mapping": {}, "options": None})
        self.check("missing required mapping rejected", missing_dry.status_code == 200 and missing_dry.json().get("error_rows", 0) > 0)

        # Atomic rollback: row 1 valid, row 2 violates VARCHAR(255) after dry-run.
        rollback_prefix = f"QA8C Rollback {s}"
        rollback_content = csv_bytes(["Name", "Instagram"], [[f"{rollback_prefix} Valid", f"qa8c_rollback_valid_{s}"], [f"{rollback_prefix} " + "X" * 300, f"qa8c_rollback_bad_{s}"]])
        rollback_upload, rollback_job = self.upload(f"rollback-{s}.csv", rollback_content)
        self.check("rollback upload", rollback_upload.status_code == 201)
        rollback_payload = {"entity_type": "customers", "sheet_name": "CSV", "column_mapping": {"name": "Name", "instagram_username": "Instagram"}, "options": None}
        rollback_dry = self.client.post(f"{API}/api/v1/import/{rollback_job}/dry-run", headers=self.headers(), json=rollback_payload)
        self.check("rollback dry-run passes", rollback_dry.status_code == 200 and rollback_dry.json().get("error_rows") == 0, safe_detail(rollback_dry))
        rollback_exec = self.client.post(f"{API}/api/v1/import/{rollback_job}/execute", headers=self.headers(), json={**rollback_payload, "mode": "create_only", "dry_run": False})
        self.check("controlled execute fails safely", rollback_exec.status_code == 400, safe_detail(rollback_exec))
        self.check("rollback response no SQL leak", not any(value in safe_detail(rollback_exec).lower() for value in ("sqlalchemy", "postgres", "insert into", "traceback")))
        rollback_customers = self.client.get(f"{API}/api/v1/customers", headers=self.headers(), params={"search": rollback_prefix})
        self.check("atomic rollback created entities zero", rollback_customers.status_code == 200 and len(rollback_customers.json()) == 0)

        # Direct API workspace isolation after all writes.
        products_b = self.client.get(f"{API}/api/v1/products", headers=self.headers(WORKSPACE_B), params={"search": "QA8C"})
        customers_b = self.client.get(f"{API}/api/v1/customers", headers=self.headers(WORKSPACE_B), params={"search": "QA8C"})
        self.check("Workspace B products unchanged", products_b.status_code == 200 and len(products_b.json()) == 0)
        self.check("Workspace B customers unchanged", customers_b.status_code == 200 and len(customers_b.json()) == 0)

        self.result["decision"] = "PASS"
        return 0


def main() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    closure = Closure()
    try:
        return closure.run()
    except Exception as exc:
        closure.result["safe_error"] = str(exc)[:400]
        return 1
    finally:
        closure.close()
        OUT.write_text(json.dumps(closure.result, indent=2, ensure_ascii=False), encoding="utf-8")
        print(json.dumps(closure.result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    raise SystemExit(main())
