#!/usr/bin/env python3
"""Controlled-write E2E gate for the dedicated Sellora staging QA workspace.

This temporary runner creates only synthetic records in the explicitly supplied QA
workspace, exercises the core commerce flow, performs tenant-negative checks, and
archives or resets every created record in a finally block. It never calls Nova
Poshta or other external-provider endpoints and never prints credentials or tokens.
"""
from __future__ import annotations

import json
import os
import sys
import time
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urljoin
from urllib.request import Request, urlopen
from uuid import uuid4

ARTIFACT_PATH = Path("artifacts/staging-controlled-write-e2e.json")
SUMMARY_PATH = Path("artifacts/staging-controlled-write-summary.json")
TIMEOUT_SECONDS = 30
EXPECTED_QA_WORKSPACE_NAME = "Sellora QA — Sprint 8A.1"
EXPECTED_REVISION = "202607080020"


class GateFailure(RuntimeError):
    pass


def utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def clean_base_url(value: str) -> str:
    return value.rstrip("/")


def api_url(base: str, path: str) -> str:
    normalized = clean_base_url(base)
    prefix = "/api/v1"
    if normalized.endswith(prefix):
        return urljoin(f"{normalized}/", path.lstrip("/"))
    return urljoin(f"{normalized}{prefix}/", path.lstrip("/"))


def parse_payload(raw: str, content_type: str) -> Any:
    if not raw:
        return None
    if "application/json" in content_type:
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {"error": "invalid JSON response"}
    return raw[:500]


def http_request(
    url: str,
    *,
    method: str = "GET",
    headers: dict[str, str] | None = None,
    body: dict[str, Any] | None = None,
) -> tuple[int, Any]:
    payload = None
    request_headers = dict(headers or {})
    if body is not None:
        payload = json.dumps(body).encode("utf-8")
        request_headers["Content-Type"] = "application/json"
    request = Request(url, data=payload, method=method, headers=request_headers)
    try:
        with urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            raw = response.read().decode("utf-8", errors="replace")
            return response.status, parse_payload(raw, response.headers.get("content-type", ""))
    except HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        return exc.code, parse_payload(raw, exc.headers.get("content-type", ""))
    except (URLError, TimeoutError) as exc:
        return 0, {"error": exc.__class__.__name__}


def decimal_value(value: Any) -> Decimal:
    return Decimal(str(value or 0))


def numeric_delta(after: Any, before: Any) -> Decimal:
    return decimal_value(after) - decimal_value(before)


def safe_detail(payload: Any) -> str:
    if isinstance(payload, dict):
        detail = payload.get("detail") or payload.get("error")
        if detail is not None:
            return str(detail)[:240]
    return ""


class ControlledWriteGate:
    def __init__(self) -> None:
        self.frontend_url = clean_base_url(os.environ["STAGING_FRONTEND_URL"])
        self.api_base = clean_base_url(os.environ["STAGING_API_URL"])
        self.owner_email = os.environ["STAGING_OWNER_EMAIL"]
        self.owner_password = os.environ["STAGING_OWNER_PASSWORD"]
        self.analyst_email = os.environ.get("STAGING_ANALYST_EMAIL", "")
        self.analyst_password = os.environ.get("STAGING_ANALYST_PASSWORD", "")
        self.workspace_id = os.environ["STAGING_TEST_WORKSPACE_ID"]
        self.expected_revision = os.environ.get("STAGING_EXPECTED_ALEMBIC_REVISION", EXPECTED_REVISION)
        self.runtime_revision = os.environ.get("STAGING_RUNTIME_ALEMBIC_REVISION", "")
        self.allow_writes = os.environ.get("STAGING_ALLOW_CONTROLLED_WRITES", "").lower() == "true"
        self.run_id = f"8A1-CW-{int(time.time())}"
        self.marker = f"QA-8A1-E2E-{int(time.time())}"
        self.suffix = self.marker.replace("QA-8A1-E2E-", "")[-10:]
        self.token: str | None = None
        self.analyst_token: str | None = None
        self.requested_paths: list[str] = []
        self.created: dict[str, str] = {}
        self.inventory_id: str | None = None
        self.baseline: dict[str, Any] = {}
        self.after_flow: dict[str, Any] = {}
        self.final_state: dict[str, Any] = {}
        self.checks: dict[str, dict[str, Any]] = {}
        self.cleanup_actions: list[dict[str, Any]] = []
        self.warnings: list[dict[str, str]] = []
        self.issues: list[dict[str, str]] = []
        self.started_at = utc_now()

    def headers(self, *, token: str | None = None, workspace_id: str | None = None) -> dict[str, str]:
        auth_token = token or self.token
        headers: dict[str, str] = {}
        if auth_token:
            headers["Authorization"] = f"Bearer {auth_token}"
        if workspace_id:
            headers["X-Workspace-ID"] = workspace_id
        return headers

    def request(
        self,
        method: str,
        path: str,
        *,
        body: dict[str, Any] | None = None,
        token: str | None = None,
        workspace_id: str | None = None,
    ) -> tuple[int, Any]:
        self.requested_paths.append(f"{method} {path.split('?', 1)[0]}")
        return http_request(
            api_url(self.api_base, path),
            method=method,
            headers=self.headers(token=token, workspace_id=workspace_id),
            body=body,
        )

    def check(self, name: str, passed: bool, detail: str, *, fatal: bool = True) -> None:
        self.checks[name] = {"status": "PASS" if passed else "FAIL", "detail": detail}
        if not passed:
            self.issues.append({"check": name, "severity": "Major" if fatal else "Minor", "detail": detail})
            if fatal:
                raise GateFailure(f"check failed: {name}")

    def warning(self, code: str, detail: str) -> None:
        self.warnings.append({"code": code, "detail": detail})

    def expect_status(self, name: str, code: int, expected: set[int], payload: Any) -> Any:
        self.check(name, code in expected, f"HTTP {code}; {safe_detail(payload)}")
        return payload

    def login(self, email: str, password: str) -> str:
        code, payload = http_request(
            api_url(self.api_base, "/auth/login"),
            method="POST",
            body={"email": email, "password": password},
        )
        if code != 200 or not isinstance(payload, dict) or not payload.get("access_token"):
            raise GateFailure(f"login failed with HTTP {code}")
        return str(payload["access_token"])

    def get_json(self, path: str, *, workspace_id: str | None = None, token: str | None = None) -> Any:
        code, payload = self.request("GET", path, workspace_id=workspace_id or self.workspace_id, token=token)
        self.expect_status(f"GET {path}", code, {200}, payload)
        return payload

    def active_counts(self) -> dict[str, int]:
        routes = {
            "leads": "/leads",
            "customers": "/customers",
            "products": "/products",
            "variants": "/products/variants",
            "orders": "/orders",
            "shipments": "/shipments",
            "inventory": "/inventory",
        }
        result: dict[str, int] = {}
        for key, path in routes.items():
            payload = self.get_json(path)
            self.check(f"{key}_list_shape", isinstance(payload, list), f"{key} list returned")
            result[key] = len(payload)
        return result

    def current_inventory(self) -> dict[str, Any]:
        payload = self.get_json(f"/inventory/{self.inventory_id}")
        self.check("inventory_workspace_scope", str(payload.get("workspace_id")) == self.workspace_id, "inventory belongs to QA workspace")
        return payload

    def preflight(self) -> None:
        self.check("controlled_write_flag", self.allow_writes, "STAGING_ALLOW_CONTROLLED_WRITES must equal true")
        self.check(
            "runtime_revision",
            self.runtime_revision == self.expected_revision == EXPECTED_REVISION,
            f"expected={self.expected_revision}, runtime={self.runtime_revision}",
        )

        frontend_code, _ = http_request(self.frontend_url)
        self.check("frontend_available", 200 <= frontend_code < 400, f"HTTP {frontend_code}")
        health_code, _ = http_request(urljoin(f"{self.api_base}/", "health"))
        self.check("backend_health", health_code == 200, f"HTTP {health_code}")

        self.token = self.login(self.owner_email, self.owner_password)
        self.check("owner_login", True, "OWNER login succeeded; token suppressed")
        code, me = self.request("GET", "/auth/me", token=self.token)
        self.expect_status("owner_auth_me", code, {200}, me)
        memberships = me.get("memberships", []) if isinstance(me, dict) else []
        membership = next((item for item in memberships if str(item.get("workspace_id")) == self.workspace_id), None)
        self.check("qa_workspace_membership", membership is not None, "requested QA workspace is present")
        self.check("qa_owner_role", membership.get("role") == "OWNER", f"role={membership.get('role') if membership else None}")
        self.check("qa_workspace_name", membership.get("workspace_name") == EXPECTED_QA_WORKSPACE_NAME, f"workspace={membership.get('workspace_name') if membership else None}")

        workspace = self.get_json("/workspaces/current")
        self.check("workspace_id_exact", str(workspace.get("id")) == self.workspace_id, "current workspace ID matches secret")
        self.check("workspace_active", bool(workspace.get("is_active", True)), "QA workspace is active")
        self.check("workspace_name_exact", workspace.get("name") == EXPECTED_QA_WORKSPACE_NAME, f"workspace={workspace.get('name')}")

        self.baseline["counts"] = self.active_counts()
        empty_required = {key: value for key, value in self.baseline["counts"].items() if key != "inventory"}
        self.check("qa_workspace_empty", all(value == 0 for value in empty_required.values()), f"baseline counts={empty_required}")
        self.check("qa_inventory_empty", self.baseline["counts"].get("inventory", 0) == 0, f"baseline inventory={self.baseline['counts'].get('inventory')}")

        today = datetime.now(UTC).date().isoformat()
        self.baseline["orders_dashboard"] = self.get_json("/orders/dashboard")
        self.baseline["finance"] = self.get_json(f"/finance/summary?{urlencode({'date_from': today, 'date_to': today})}")
        self.baseline["dashboard_summary"] = self.get_json(f"/analytics/dashboard-summary?{urlencode({'date_from': today, 'date_to': today})}")

        if self.analyst_email and self.analyst_password:
            self.analyst_token = self.login(self.analyst_email, self.analyst_password)
            denied_code, denied_payload = self.request(
                "POST",
                "/leads",
                token=self.analyst_token,
                workspace_id=self.workspace_id,
                body={"name": f"{self.marker} denied analyst write"},
            )
            self.check("analyst_write_rejected", denied_code == 403, f"HTTP {denied_code}; {safe_detail(denied_payload)}")

    def create_flow(self) -> None:
        lead_body = {
            "instagram_username": f"qa_e2e_{self.suffix}",
            "name": f"{self.marker} Lead",
            "phone": "+380000000001",
            "notes": f"{self.marker}; synthetic staging-only record; safe to archive",
            "expected_revenue": "1598.00",
        }
        code, lead = self.request("POST", "/leads", workspace_id=self.workspace_id, body=lead_body)
        self.expect_status("lead_create", code, {201}, lead)
        self.created["lead_id"] = str(lead["id"])
        self.check("lead_workspace", str(lead.get("workspace_id")) == self.workspace_id, "lead belongs to QA workspace")

        code, customer = self.request("POST", f"/leads/{self.created['lead_id']}/convert", workspace_id=self.workspace_id)
        self.expect_status("lead_convert_customer", code, {200}, customer)
        self.created["customer_id"] = str(customer["id"])
        self.check("customer_workspace", str(customer.get("workspace_id")) == self.workspace_id, "customer belongs to QA workspace")

        product_body = {
            "name": f"{self.marker} Product",
            "sku": f"QA8A1-P-{self.suffix}",
            "description": f"{self.marker}; synthetic controlled-write product",
            "category": "qa-synthetic",
            "brand": "Sellora QA",
            "is_active": True,
            "images": [],
        }
        code, product = self.request("POST", "/products", workspace_id=self.workspace_id, body=product_body)
        self.expect_status("product_create", code, {201}, product)
        self.created["product_id"] = str(product["id"])
        self.check("product_workspace", str(product.get("workspace_id")) == self.workspace_id, "product belongs to QA workspace")

        variant_body = {
            "product_id": self.created["product_id"],
            "sku": f"QA8A1-V-{self.suffix}",
            "color": "Synthetic",
            "size": self.suffix[-4:],
            "price": "799.00",
            "barcode": None,
            "is_active": True,
            "initial_stock_quantity": 0,
            "minimum_quantity": 1,
        }
        code, variant = self.request("POST", "/products/variants", workspace_id=self.workspace_id, body=variant_body)
        self.expect_status("variant_create", code, {201}, variant)
        self.created["variant_id"] = str(variant["id"])
        self.check("variant_workspace", str(variant.get("workspace_id")) == self.workspace_id, "variant belongs to QA workspace")

        inventory_rows = self.get_json("/inventory")
        inventory = next((row for row in inventory_rows if str(row.get("product_variant_id")) == self.created["variant_id"]), None)
        self.check("inventory_auto_created", inventory is not None, "variant inventory record exists")
        self.inventory_id = str(inventory["id"])
        self.created["inventory_id"] = self.inventory_id
        self.check("inventory_initial_state", int(inventory.get("stock_quantity", -1)) == 0 and int(inventory.get("reserved_quantity", -1)) == 0, "stock=0 reserved=0")

        code, stock_tx = self.request(
            "POST",
            f"/inventory/{self.inventory_id}/transactions",
            workspace_id=self.workspace_id,
            body={"transaction_type": "STOCK_IN", "quantity": 5, "reason": f"{self.marker} stock-in"},
        )
        self.expect_status("stock_in", code, {201}, stock_tx)
        self.check("stock_in_quantities", int(stock_tx.get("previous_stock_quantity", -1)) == 0 and int(stock_tx.get("new_stock_quantity", -1)) == 5, "stock 0 -> 5")

        inventory = self.current_inventory()
        self.check("stock_after_stock_in", int(inventory.get("stock_quantity", -1)) == 5 and int(inventory.get("reserved_quantity", -1)) == 0, "stock=5 reserved=0")

        fake_workspace_id = str(uuid4())
        cross_body = {
            "customer_id": self.created["customer_id"],
            "status": "NEW",
            "payment_status": "PENDING",
            "items": [{"product_variant_id": self.created["variant_id"], "quantity": 1, "unit_price": "799.00", "unit_cost": "300.00"}],
        }
        cross_code, cross_payload = self.request("POST", "/orders", workspace_id=fake_workspace_id, body=cross_body)
        self.check("cross_workspace_context_rejected", cross_code == 403, f"HTTP {cross_code}; {safe_detail(cross_payload)}")

        foreign_code, foreign_payload = self.request(
            "POST",
            "/orders",
            workspace_id=self.workspace_id,
            body={
                "customer_id": str(uuid4()),
                "status": "NEW",
                "payment_status": "PENDING",
                "items": [{"product_variant_id": self.created["variant_id"], "quantity": 1, "unit_price": "799.00", "unit_cost": "300.00"}],
            },
        )
        self.check("foreign_customer_reference_rejected", foreign_code == 400, f"HTTP {foreign_code}; {safe_detail(foreign_payload)}")

        order_body = {
            "customer_id": self.created["customer_id"],
            "status": "NEW",
            "payment_status": "PENDING",
            "is_historical": False,
            "items": [{"product_variant_id": self.created["variant_id"], "quantity": 2, "unit_price": "799.00", "unit_cost": "300.00"}],
            "ad_cost": "50.00",
            "shipping_cost": "70.00",
            "cod_fee": "20.00",
            "other_cost": "10.00",
            "notes": f"{self.marker}; controlled-write order",
        }
        code, order = self.request("POST", "/orders", workspace_id=self.workspace_id, body=order_body)
        self.expect_status("order_create", code, {201}, order)
        self.created["order_id"] = str(order["id"])
        self.check("order_workspace", str(order.get("workspace_id")) == self.workspace_id, "order belongs to QA workspace")
        self.check("order_variant_exact", len(order.get("items", [])) == 1 and str(order["items"][0].get("product_variant_id")) == self.created["variant_id"], "order contains the exact synthetic variant")
        self.check("order_quantity_exact", int(order["items"][0].get("quantity", 0)) == 2, "quantity=2")

        expected_order_values = {
            "revenue": Decimal("1598.00"),
            "product_cost": Decimal("600.00"),
            "ad_cost": Decimal("50.00"),
            "shipping_cost": Decimal("70.00"),
            "cod_fee": Decimal("20.00"),
            "other_cost": Decimal("10.00"),
            "net_profit": Decimal("848.00"),
        }
        values_ok = all(decimal_value(order.get(key)) == expected for key, expected in expected_order_values.items())
        self.check("order_revenue_profit_formula", values_ok, f"expected={{{', '.join(f'{k}:{v}' for k, v in expected_order_values.items())}}}")
        self.check("initial_status_history", len(order.get("status_history", [])) >= 1 and order["status_history"][0].get("to_status") == "NEW", "initial NEW history exists")

        inventory = self.current_inventory()
        self.check("order_reservation", int(inventory.get("stock_quantity", -1)) == 5 and int(inventory.get("reserved_quantity", -1)) == 2, "stock remains 5; reserved=2; available=3")

        code, paid_order = self.request("PUT", f"/orders/{self.created['order_id']}", workspace_id=self.workspace_id, body={"payment_status": "PAID"})
        self.expect_status("payment_status_update", code, {200}, paid_order)
        self.check("payment_status_paid", paid_order.get("payment_status") == "PAID", "payment_status=PAID")

        code, confirmed_order = self.request(
            "POST",
            f"/orders/{self.created['order_id']}/status",
            workspace_id=self.workspace_id,
            body={"status": "CONFIRMED", "note": f"{self.marker} status history verification"},
        )
        self.expect_status("order_status_confirmed", code, {200}, confirmed_order)
        history = confirmed_order.get("status_history", [])
        self.check("status_history_created", len(history) >= 2 and any(item.get("to_status") == "CONFIRMED" for item in history), f"history entries={len(history)}")

        shipment_body = {
            "order_id": self.created["order_id"],
            "customer_id": self.created["customer_id"],
            "tracking_number": None,
            "carrier": "NOVA_POSHTA",
            "status": "DRAFT",
            "recipient_name": f"{self.marker} Recipient",
            "recipient_phone": "+380000000001",
            "city": "QA Synthetic City",
            "warehouse": "QA Synthetic Warehouse",
            "shipping_cost": "70.00",
            "cod_amount": "1598.00",
            "declared_value": "1598.00",
            "notes": f"{self.marker}; draft only; do not create TTN",
            "nova_poshta_city_ref": None,
            "nova_poshta_warehouse_ref": None,
        }
        code, shipment = self.request("POST", f"/orders/{self.created['order_id']}/shipment", workspace_id=self.workspace_id, body=shipment_body)
        self.expect_status("shipment_draft_create", code, {201}, shipment)
        self.created["shipment_id"] = str(shipment["id"])
        self.check("shipment_workspace", str(shipment.get("workspace_id")) == self.workspace_id, "shipment belongs to QA workspace")
        self.check("shipment_remains_draft", shipment.get("status") == "DRAFT" and shipment.get("tracking_number") is None, "DRAFT without tracking number")
        external_fields = [
            "external_provider",
            "external_ref",
            "external_status",
            "nova_poshta_document_ref",
            "nova_poshta_document_number",
            "nova_poshta_raw_status",
            "nova_poshta_synced_at",
        ]
        self.check("nova_poshta_fields_absent", all(shipment.get(field) is None for field in external_fields), "no external provider result fields populated")

        forbidden_external_paths = [path for path in self.requested_paths if "/nova-poshta/" in path]
        self.check("nova_poshta_api_not_called", not forbidden_external_paths, "no Nova Poshta route requested by E2E runner")

        today = datetime.now(UTC).date().isoformat()
        self.after_flow["orders_dashboard"] = self.get_json("/orders/dashboard")
        self.after_flow["finance"] = self.get_json(f"/finance/summary?{urlencode({'date_from': today, 'date_to': today})}")
        self.after_flow["dashboard_summary"] = self.get_json(f"/analytics/dashboard-summary?{urlencode({'date_from': today, 'date_to': today})}")

        baseline_dashboard = self.baseline["orders_dashboard"]
        after_dashboard = self.after_flow["orders_dashboard"]
        self.check("dashboard_order_visibility", int(after_dashboard.get("orders_today", 0)) - int(baseline_dashboard.get("orders_today", 0)) == 1, "orders_today delta=1")
        self.check("dashboard_revenue_visibility", numeric_delta(after_dashboard.get("revenue_today"), baseline_dashboard.get("revenue_today")) == Decimal("1598.00"), "revenue_today delta=1598.00")
        self.check("dashboard_profit_visibility", numeric_delta(after_dashboard.get("profit_today"), baseline_dashboard.get("profit_today")) == Decimal("848.00"), "profit_today delta=848.00")

        baseline_sales = self.baseline["dashboard_summary"].get("sales", {})
        after_sales = self.after_flow["dashboard_summary"].get("sales", {})
        self.check("main_dashboard_order_visibility", int(after_sales.get("orders_count", 0)) - int(baseline_sales.get("orders_count", 0)) == 1, "dashboard-summary orders delta=1")
        self.check("main_dashboard_revenue_visibility", numeric_delta(after_sales.get("revenue"), baseline_sales.get("revenue")) == Decimal("1598.00"), "dashboard-summary revenue delta=1598.00")
        self.check("main_dashboard_profit_visibility", numeric_delta(after_sales.get("net_profit"), baseline_sales.get("net_profit")) == Decimal("848.00"), "dashboard-summary profit delta=848.00")

        baseline_finance = self.baseline["finance"]
        after_finance = self.after_flow["finance"]
        finance_expected = {
            "revenue": Decimal("1598.00"),
            "cogs": Decimal("600.00"),
            "shipping_cost": Decimal("70.00"),
            "orders_count": Decimal("1"),
            "paid_orders_count": Decimal("1"),
        }
        finance_checks_ok = all(numeric_delta(after_finance.get(key), baseline_finance.get(key)) == expected for key, expected in finance_expected.items())
        self.check("finance_visibility", finance_checks_ok, f"expected deltas={{{', '.join(f'{k}:{v}' for k, v in finance_expected.items())}}}")
        finance_profit_delta = numeric_delta(after_finance.get("net_profit"), baseline_finance.get("net_profit"))
        self.after_flow["profit_comparison"] = {
            "order_net_profit": "848.00",
            "dashboard_net_profit_delta": "848.00",
            "finance_net_profit_delta": str(finance_profit_delta),
            "finance_formula_note": "Finance uses manual/CSV ad metrics and shipment shipping cost; order ad/cod/other costs are not all sourced from the order-level formula.",
        }
        if finance_profit_delta != Decimal("848.00"):
            self.warning(
                "order_finance_profit_formula_difference",
                f"Order/dashboard net profit delta is 848.00 while Finance net profit delta is {finance_profit_delta}. Source formulas differ and must remain visible to the user.",
            )
        self.check("revenue_profit_state_honest", decimal_value(after_order := confirmed_order.get("net_profit")) == Decimal("848.00") and finance_profit_delta >= Decimal("0"), f"order net profit={after_order}; finance delta={finance_profit_delta}")

    def cleanup_request(self, name: str, method: str, path: str, *, body: dict[str, Any] | None = None, expected: set[int] | None = None) -> tuple[int, Any]:
        code, payload = self.request(method, path, workspace_id=self.workspace_id, body=body)
        accepted = code in (expected or {200, 204, 404})
        self.cleanup_actions.append({"action": name, "status": "PASS" if accepted else "FAIL", "http_status": code, "detail": safe_detail(payload)})
        return code, payload

    def cleanup(self) -> None:
        if not self.token:
            return
        shipment_id = self.created.get("shipment_id")
        order_id = self.created.get("order_id")
        variant_id = self.created.get("variant_id")
        product_id = self.created.get("product_id")
        customer_id = self.created.get("customer_id")
        lead_id = self.created.get("lead_id")

        if shipment_id:
            self.cleanup_request("archive_shipment", "DELETE", f"/shipments/{shipment_id}", expected={204, 404})

        if order_id:
            code, order = self.request("GET", f"/orders/{order_id}", workspace_id=self.workspace_id)
            if code == 200 and isinstance(order, dict) and order.get("status") != "CANCELLED":
                self.cleanup_request("cancel_order", "POST", f"/orders/{order_id}/status", body={"status": "CANCELLED", "note": f"{self.marker} cleanup"}, expected={200})
            self.cleanup_request("archive_order", "DELETE", f"/orders/{order_id}", expected={204, 404})

        if self.inventory_id:
            code, inventory = self.request("GET", f"/inventory/{self.inventory_id}", workspace_id=self.workspace_id)
            if code == 200 and isinstance(inventory, dict):
                reserved = int(inventory.get("reserved_quantity", 0))
                stock = int(inventory.get("stock_quantity", 0))
                if reserved > 0:
                    self.cleanup_request(
                        "release_remaining_reservation",
                        "POST",
                        f"/inventory/{self.inventory_id}/transactions",
                        body={"transaction_type": "UNRESERVE", "quantity": reserved, "reason": f"{self.marker} cleanup"},
                        expected={201},
                    )
                if stock > 0:
                    self.cleanup_request(
                        "reset_stock_to_zero",
                        "POST",
                        f"/inventory/{self.inventory_id}/transactions",
                        body={"transaction_type": "STOCK_OUT", "quantity": stock, "reason": f"{self.marker} cleanup"},
                        expected={201},
                    )
                self.cleanup_request("reset_inventory_metadata", "PUT", f"/inventory/{self.inventory_id}", body={"incoming_quantity": 0, "minimum_quantity": 0}, expected={200})

        if variant_id:
            self.cleanup_request("archive_variant", "DELETE", f"/products/variants/{variant_id}", expected={204, 404})
        if product_id:
            self.cleanup_request("archive_product", "DELETE", f"/products/{product_id}", expected={204, 404})
        if customer_id:
            self.cleanup_request("archive_customer", "DELETE", f"/customers/{customer_id}", expected={204, 404})
        if lead_id:
            self.cleanup_request("archive_lead", "DELETE", f"/leads/{lead_id}", expected={204, 404})

        try:
            counts = self.active_counts()
            self.final_state["counts"] = counts
            absent_ok = all(counts.get(key, 0) == self.baseline.get("counts", {}).get(key, 0) for key in ["leads", "customers", "products", "variants", "orders", "shipments"])
            self.checks["cleanup_entities_archived"] = {"status": "PASS" if absent_ok else "FAIL", "detail": f"final counts={counts}; baseline={self.baseline.get('counts', {})}"}
            if not absent_ok:
                self.issues.append({"check": "cleanup_entities_archived", "severity": "Major", "detail": "active business entity counts did not return to baseline"})

            inventory_state: dict[str, Any] | None = None
            if self.inventory_id:
                code, payload = self.request("GET", f"/inventory/{self.inventory_id}", workspace_id=self.workspace_id)
                if code == 200 and isinstance(payload, dict):
                    inventory_state = {
                        "still_active": True,
                        "stock_quantity": payload.get("stock_quantity"),
                        "reserved_quantity": payload.get("reserved_quantity"),
                        "incoming_quantity": payload.get("incoming_quantity"),
                        "minimum_quantity": payload.get("minimum_quantity"),
                    }
                elif code == 404:
                    inventory_state = {"still_active": False}
            self.final_state["inventory"] = inventory_state
            inventory_reset = inventory_state is None or not inventory_state.get("still_active") or (
                int(inventory_state.get("stock_quantity", -1)) == 0
                and int(inventory_state.get("reserved_quantity", -1)) == 0
                and int(inventory_state.get("incoming_quantity", -1)) == 0
            )
            self.checks["cleanup_inventory_reset"] = {"status": "PASS" if inventory_reset else "FAIL", "detail": str(inventory_state)}
            if not inventory_reset:
                self.issues.append({"check": "cleanup_inventory_reset", "severity": "Major", "detail": str(inventory_state)})
            if inventory_state and inventory_state.get("still_active"):
                self.warning("inventory_archive_endpoint_missing", "Inventory row remains active after product/variant archive because the public API has no inventory archive endpoint; quantities were reset to zero.")
        except Exception as exc:  # cleanup evidence must never suppress the original artifact
            self.issues.append({"check": "cleanup_verification", "severity": "Major", "detail": exc.__class__.__name__})

    def artifact(self) -> dict[str, Any]:
        failed = [name for name, value in self.checks.items() if value.get("status") == "FAIL"]
        cleanup_failed = any(item.get("status") == "FAIL" for item in self.cleanup_actions)
        decision = "PASS" if not failed and not cleanup_failed else "FAIL"
        return {
            "run_id": self.run_id,
            "timestamp_started": self.started_at,
            "timestamp_finished": utc_now(),
            "environment": "staging",
            "mode": "controlled-write",
            "workspace": {"expected_name": EXPECTED_QA_WORKSPACE_NAME, "id_verified": self.checks.get("workspace_id_exact", {}).get("status") == "PASS"},
            "safety": {
                "controlled_write_flag": self.allow_writes,
                "synthetic_marker": self.marker,
                "nova_poshta_routes_requested": [path for path in self.requested_paths if "/nova-poshta/" in path],
                "migrations_executed": False,
                "real_workspace_used": False,
            },
            "checks": self.checks,
            "created_entity_ids": self.created,
            "baseline": self.baseline,
            "after_flow": self.after_flow,
            "cleanup_actions": self.cleanup_actions,
            "final_state": self.final_state,
            "warnings": self.warnings,
            "issues": self.issues,
            "failed_checks": failed,
            "decision": decision,
        }

    def run(self) -> int:
        caught: Exception | None = None
        try:
            self.preflight()
            self.create_flow()
        except Exception as exc:
            caught = exc
            if isinstance(exc, GateFailure):
                self.issues.append({"check": "execution", "severity": "Major", "detail": str(exc)})
            else:
                self.issues.append({"check": "execution", "severity": "Critical", "detail": exc.__class__.__name__})
        finally:
            try:
                self.cleanup()
            except Exception as cleanup_exc:
                self.issues.append({"check": "cleanup", "severity": "Critical", "detail": cleanup_exc.__class__.__name__})

        artifact = self.artifact()
        if caught is not None and artifact["decision"] == "PASS":
            artifact["decision"] = "FAIL"
        ARTIFACT_PATH.parent.mkdir(parents=True, exist_ok=True)
        ARTIFACT_PATH.write_text(json.dumps(artifact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        summary = {
            "run_id": artifact["run_id"],
            "mode": artifact["mode"],
            "decision": artifact["decision"],
            "checks_passed": sum(1 for value in artifact["checks"].values() if value.get("status") == "PASS"),
            "checks_failed": len(artifact["failed_checks"]),
            "warnings": len(artifact["warnings"]),
            "cleanup_actions": len(artifact["cleanup_actions"]),
            "artifact": str(ARTIFACT_PATH),
        }
        SUMMARY_PATH.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 0 if artifact["decision"] == "PASS" else 2


def validate_environment() -> None:
    required = [
        "STAGING_FRONTEND_URL",
        "STAGING_API_URL",
        "STAGING_OWNER_EMAIL",
        "STAGING_OWNER_PASSWORD",
        "STAGING_TEST_WORKSPACE_ID",
        "STAGING_EXPECTED_ALEMBIC_REVISION",
        "STAGING_RUNTIME_ALEMBIC_REVISION",
        "STAGING_ALLOW_CONTROLLED_WRITES",
    ]
    missing = [name for name in required if not os.environ.get(name)]
    if missing:
        raise SystemExit("Missing required controlled-write environment inputs")


if __name__ == "__main__":
    validate_environment()
    sys.exit(ControlledWriteGate().run())
