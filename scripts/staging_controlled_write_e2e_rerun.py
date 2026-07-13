#!/usr/bin/env python3
"""Sprint 8A.1 controlled-write E2E rerun for Sellora staging.

Creates only synthetic records inside the explicit QA workspace, verifies the
Lead -> Customer -> Product -> Variant -> Stock-in -> Order -> Payment/status ->
Shipment draft -> Dashboard/Finance path, then archives/resets everything.
No Nova Poshta endpoints are called and credentials/tokens are never printed.
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

ARTIFACT = Path("artifacts/staging-controlled-write-e2e.json")
SUMMARY = Path("artifacts/staging-controlled-write-summary.json")
EXPECTED_REVISION = "202607130021"
EXPECTED_QA_WORKSPACE_NAME = "Sellora QA — Sprint 8A.1"
TIMEOUT_SECONDS = 35


class GateFailure(RuntimeError):
    pass


def now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def clean_url(value: str) -> str:
    return value.rstrip("/")


def api_url(base: str, path: str) -> str:
    normalized = clean_url(base)
    if normalized.endswith("/api/v1"):
        return urljoin(normalized + "/", path.lstrip("/"))
    return urljoin(normalized + "/api/v1/", path.lstrip("/"))


def parse_response(raw: str, content_type: str) -> Any:
    if not raw:
        return None
    if "application/json" in content_type:
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {"error": "invalid JSON"}
    return raw[:300]


def http(url: str, *, method: str = "GET", headers: dict[str, str] | None = None, body: dict[str, Any] | None = None) -> tuple[int, Any]:
    request_headers = dict(headers or {})
    payload = None
    if body is not None:
        payload = json.dumps(body).encode("utf-8")
        request_headers["Content-Type"] = "application/json"
    req = Request(url, data=payload, method=method, headers=request_headers)
    try:
        with urlopen(req, timeout=TIMEOUT_SECONDS) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            return resp.status, parse_response(raw, resp.headers.get("content-type", ""))
    except HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        return exc.code, parse_response(raw, exc.headers.get("content-type", ""))
    except (URLError, TimeoutError) as exc:
        return 0, {"error": exc.__class__.__name__}


def dec(value: Any) -> Decimal:
    return Decimal(str(value or "0"))


def detail(payload: Any) -> str:
    if isinstance(payload, dict):
        value = payload.get("detail") or payload.get("error")
        if value:
            return str(value)[:220]
    return ""


class Gate:
    def __init__(self) -> None:
        self.frontend_url = clean_url(os.environ["STAGING_FRONTEND_URL"])
        self.api_base = clean_url(os.environ["STAGING_API_URL"])
        self.workspace_id = os.environ["STAGING_TEST_WORKSPACE_ID"]
        self.owner_email = os.environ["STAGING_OWNER_EMAIL"]
        self.owner_password = os.environ["STAGING_OWNER_PASSWORD"]
        self.analyst_email = os.environ.get("STAGING_ANALYST_EMAIL", "")
        self.analyst_password = os.environ.get("STAGING_ANALYST_PASSWORD", "")
        self.expected_revision = os.environ.get("STAGING_EXPECTED_ALEMBIC_REVISION", EXPECTED_REVISION)
        self.runtime_revision = os.environ.get("STAGING_RUNTIME_ALEMBIC_REVISION", "")
        self.allow_writes = os.environ.get("STAGING_ALLOW_CONTROLLED_WRITES", "").lower() == "true"

        stamp = str(int(time.time()))
        self.marker = f"QA-8A1-E2E-{stamp}"
        self.suffix = stamp[-10:]
        self.token: str | None = None
        self.analyst_token: str | None = None
        self.created: dict[str, str] = {}
        self.inventory_id: str | None = None
        self.requested_paths: list[str] = []
        self.baseline: dict[str, Any] = {}
        self.after_flow: dict[str, Any] = {}
        self.final_state: dict[str, Any] = {}
        self.checks: dict[str, dict[str, Any]] = {}
        self.issues: list[dict[str, str]] = []
        self.cleanup_actions: list[dict[str, Any]] = []
        self.warnings: list[dict[str, str]] = []
        self.started_at = now()

    def headers(self, *, token: str | None = None, workspace_id: str | None = None) -> dict[str, str]:
        h: dict[str, str] = {}
        auth_token = token or self.token
        if auth_token:
            h["Authorization"] = f"Bearer {auth_token}"
        if workspace_id:
            h["X-Workspace-ID"] = workspace_id
        return h

    def req(self, method: str, path: str, *, body: dict[str, Any] | None = None, token: str | None = None, workspace_id: str | None = None) -> tuple[int, Any]:
        self.requested_paths.append(f"{method} {path.split('?', 1)[0]}")
        return http(api_url(self.api_base, path), method=method, headers=self.headers(token=token, workspace_id=workspace_id or self.workspace_id), body=body)

    def check(self, name: str, ok: bool, msg: str, *, fatal: bool = True) -> None:
        self.checks[name] = {"status": "PASS" if ok else "FAIL", "detail": msg}
        if not ok:
            self.issues.append({"check": name, "detail": msg, "severity": "Major" if fatal else "Minor"})
            if fatal:
                raise GateFailure(name)

    def expect(self, name: str, code: int, expected: set[int], payload: Any) -> Any:
        self.check(name, code in expected, f"HTTP {code}; {detail(payload)}")
        return payload

    def login(self, email: str, password: str) -> str:
        code, payload = http(api_url(self.api_base, "/auth/login"), method="POST", body={"email": email, "password": password})
        if code != 200 or not isinstance(payload, dict) or not payload.get("access_token"):
            raise GateFailure(f"login failed: HTTP {code}")
        return str(payload["access_token"])

    def get(self, path: str, *, token: str | None = None, workspace_id: str | None = None) -> Any:
        code, payload = self.req("GET", path, token=token, workspace_id=workspace_id)
        return self.expect(f"GET {path}", code, {200}, payload)

    def active_counts(self) -> dict[str, int]:
        routes = {
            "leads": "/leads",
            "customers": "/customers",
            "products": "/products",
            "variants": "/products/variants",
            "inventory": "/inventory",
            "orders": "/orders",
            "shipments": "/shipments",
        }
        counts: dict[str, int] = {}
        for key, path in routes.items():
            payload = self.get(path)
            self.check(f"{key}_list_shape", isinstance(payload, list), f"{key} is a list")
            counts[key] = len(payload)
        return counts

    def preflight(self) -> None:
        self.check("controlled_write_flag", self.allow_writes, "controlled writes explicitly enabled")
        self.check("runtime_revision", self.expected_revision == self.runtime_revision == EXPECTED_REVISION, f"expected={self.expected_revision}, runtime={self.runtime_revision}")

        code, _ = http(self.frontend_url)
        self.check("frontend_available", 200 <= code < 400, f"HTTP {code}")
        health, _ = http(urljoin(self.api_base + "/", "health"))
        self.check("backend_health", health == 200, f"HTTP {health}")

        self.token = self.login(self.owner_email, self.owner_password)
        self.check("owner_login", True, "OWNER login succeeded; token suppressed")

        code, me = self.req("GET", "/auth/me", workspace_id=None)
        self.expect("owner_auth_me", code, {200}, me)
        memberships = me.get("memberships", []) if isinstance(me, dict) else []
        membership = next((m for m in memberships if str(m.get("workspace_id")) == self.workspace_id), None)
        self.check("qa_workspace_membership", membership is not None, "QA workspace membership exists")
        self.check("qa_owner_role", membership and membership.get("role") == "OWNER", f"role={membership.get('role') if membership else None}")
        self.check("qa_workspace_name", membership and membership.get("workspace_name") == EXPECTED_QA_WORKSPACE_NAME, f"name={membership.get('workspace_name') if membership else None}")

        workspace = self.get("/workspaces/current")
        self.check("workspace_id_exact", str(workspace.get("id")) == self.workspace_id, "workspace ID matches secret")
        self.check("workspace_active", bool(workspace.get("is_active", True)), "workspace active")
        self.check("workspace_name_exact", workspace.get("name") == EXPECTED_QA_WORKSPACE_NAME, f"name={workspace.get('name')}")

        self.baseline["counts"] = self.active_counts()
        self.check("qa_workspace_empty", all(v == 0 for k, v in self.baseline["counts"].items() if k != "inventory"), f"baseline={self.baseline['counts']}")
        self.check("qa_inventory_empty", self.baseline["counts"].get("inventory") == 0, f"inventory={self.baseline['counts'].get('inventory')}")

        today = datetime.now(UTC).date().isoformat()
        query = urlencode({"date_from": today, "date_to": today})
        self.baseline["orders_dashboard"] = self.get("/orders/dashboard")
        self.baseline["finance"] = self.get(f"/finance/summary?{query}")
        self.baseline["dashboard_summary"] = self.get(f"/analytics/dashboard-summary?{query}")

        if self.analyst_email and self.analyst_password:
            self.analyst_token = self.login(self.analyst_email, self.analyst_password)
            code, payload = self.req("POST", "/leads", token=self.analyst_token, body={"name": f"{self.marker} denied analyst write"})
            self.check("analyst_write_rejected", code == 403, f"HTTP {code}; {detail(payload)}")

    def create_flow(self) -> None:
        code, lead = self.req("POST", "/leads", body={
            "instagram_username": f"qa_e2e_{self.suffix}",
            "name": f"{self.marker} Lead",
            "phone": "+380000000001",
            "notes": f"{self.marker}; synthetic staging-only record",
            "expected_revenue": "1598.00",
        })
        self.expect("lead_create", code, {201}, lead)
        self.created["lead_id"] = str(lead["id"])
        self.check("lead_workspace", str(lead.get("workspace_id")) == self.workspace_id, "lead in QA workspace")

        code, customer = self.req("POST", f"/leads/{self.created['lead_id']}/convert")
        self.expect("lead_convert_customer", code, {200}, customer)
        self.created["customer_id"] = str(customer["id"])
        self.check("customer_workspace", str(customer.get("workspace_id")) == self.workspace_id, "customer in QA workspace")

        code, product = self.req("POST", "/products", body={
            "name": f"{self.marker} Product",
            "sku": f"QA8A1-P-{self.suffix}",
            "description": "synthetic controlled-write product",
            "category": "qa-synthetic",
            "brand": "Sellora QA",
            "is_active": True,
            "images": [],
        })
        self.expect("product_create", code, {201}, product)
        self.created["product_id"] = str(product["id"])
        self.check("product_workspace", str(product.get("workspace_id")) == self.workspace_id, "product in QA workspace")

        code, variant = self.req("POST", "/products/variants", body={
            "product_id": self.created["product_id"],
            "sku": f"QA8A1-V-{self.suffix}",
            "color": "QA Purple",
            "size": "E2E",
            "price": "799.00",
            "barcode": f"QA8A1{self.suffix}",
            "is_active": True,
            "initial_stock_quantity": 0,
            "minimum_quantity": 1,
        })
        self.expect("variant_create", code, {201}, variant)
        self.created["variant_id"] = str(variant["id"])
        self.check("variant_workspace", str(variant.get("workspace_id")) == self.workspace_id, "variant in QA workspace")

        inventory_rows = self.get("/inventory")
        inventory = next((row for row in inventory_rows if str(row.get("product_variant_id")) == self.created["variant_id"]), None)
        self.check("inventory_auto_created", inventory is not None, "inventory auto-created for variant")
        self.inventory_id = str(inventory["id"])
        self.check("inventory_workspace", str(inventory.get("workspace_id")) == self.workspace_id, "inventory in QA workspace")

        code, stock_tx = self.req("POST", f"/inventory/{self.inventory_id}/transactions", body={
            "transaction_type": "STOCK_IN",
            "quantity": 5,
            "reason": f"{self.marker} stock-in",
        })
        self.expect("stock_in", code, {201}, stock_tx)
        inventory = self.get(f"/inventory/{self.inventory_id}")
        self.check("stock_after_stock_in", inventory.get("stock_quantity") == 5 and inventory.get("reserved_quantity") == 0, f"stock={inventory.get('stock_quantity')} reserved={inventory.get('reserved_quantity')}")

        random_workspace = str(uuid4())
        denied_code, denied_payload = self.req("GET", f"/customers/{self.created['customer_id']}", workspace_id=random_workspace)
        self.check("cross_workspace_context_rejected", denied_code in {403, 404}, f"HTTP {denied_code}; {detail(denied_payload)}")

        code, foreign_payload = self.req("POST", "/orders", body={
            "customer_id": str(uuid4()),
            "status": "NEW",
            "payment_status": "PENDING",
            "items": [{"product_variant_id": self.created["variant_id"], "quantity": 1, "unit_price": "799.00", "unit_cost": "400.00"}],
        })
        self.check("foreign_customer_reference_rejected", code in {400, 422}, f"HTTP {code}; {detail(foreign_payload)}")

        order_body = {
            "customer_id": self.created["customer_id"],
            "status": "NEW",
            "payment_status": "PENDING",
            "items": [{"product_variant_id": self.created["variant_id"], "quantity": 2, "unit_price": "799.00", "unit_cost": "400.00"}],
            "ad_cost": "100.00",
            "shipping_cost": "50.00",
            "cod_fee": "20.00",
            "other_cost": "30.00",
            "notes": f"{self.marker}; synthetic controlled-write order",
        }
        code, order = self.req("POST", "/orders", body=order_body)
        self.expect("order_create", code, {201}, order)
        self.created["order_id"] = str(order["id"])
        self.check("order_workspace", str(order.get("workspace_id")) == self.workspace_id, "order in QA workspace")
        self.check("order_number_created", str(order.get("order_number", "")).startswith("ORD-"), f"order_number={order.get('order_number')}")
        self.check("order_variant_exact", str(order["items"][0]["product_variant_id"]) == self.created["variant_id"], "order item variant matches")
        self.check("order_quantity_exact", order["items"][0]["quantity"] == 2, f"quantity={order['items'][0]['quantity']}")
        self.check("order_revenue_profit_formula", dec(order["revenue"]) == Decimal("1598.00") and dec(order["net_profit"]) == Decimal("598.00"), f"revenue={order.get('revenue')} profit={order.get('net_profit')}")
        self.check("initial_status_history", len(order.get("status_history", [])) >= 1 and order["status_history"][0]["to_status"] == "NEW", "initial status history created")

        inventory = self.get(f"/inventory/{self.inventory_id}")
        self.check("order_reservation", inventory.get("stock_quantity") == 5 and inventory.get("reserved_quantity") == 2, f"stock={inventory.get('stock_quantity')} reserved={inventory.get('reserved_quantity')}")

        code, paid_order = self.req("PUT", f"/orders/{self.created['order_id']}", body={"payment_status": "PAID"})
        self.expect("payment_status_update", code, {200}, paid_order)
        self.check("payment_status_paid", paid_order.get("payment_status") == "PAID", f"payment={paid_order.get('payment_status')}")

        code, confirmed = self.req("POST", f"/orders/{self.created['order_id']}/status", body={"status": "CONFIRMED", "note": f"{self.marker} confirm"})
        self.expect("order_status_confirmed", code, {200}, confirmed)
        self.check("status_history_created", any(row.get("to_status") == "CONFIRMED" for row in confirmed.get("status_history", [])), "CONFIRMED status history exists")

        shipment_body = {
            "order_id": self.created["order_id"],
            "customer_id": self.created["customer_id"],
            "carrier": "NOVA_POSHTA",
            "status": "DRAFT",
            "recipient_name": f"{self.marker} Recipient",
            "recipient_phone": "+380000000001",
            "city": "Луцьк",
            "warehouse": "QA Відділення",
            "shipping_cost": "50.00",
            "cod_amount": "1598.00",
            "declared_value": "1598.00",
            "notes": f"{self.marker}; draft only; no external provider call",
        }
        code, shipment = self.req("POST", f"/orders/{self.created['order_id']}/shipment", body=shipment_body)
        self.expect("shipment_draft_create", code, {201}, shipment)
        self.created["shipment_id"] = str(shipment["id"])
        self.check("shipment_workspace", str(shipment.get("workspace_id")) == self.workspace_id, "shipment in QA workspace")
        self.check("shipment_remains_draft", shipment.get("status") == "DRAFT", f"status={shipment.get('status')}")
        self.check("nova_poshta_fields_absent", not shipment.get("nova_poshta_document_ref") and not shipment.get("nova_poshta_document_number"), "no TTN fields set")
        self.check("nova_poshta_api_not_called", not any("/nova-poshta/" in path for path in self.requested_paths), "no Nova Poshta route requested")

        today = datetime.now(UTC).date().isoformat()
        query = urlencode({"date_from": today, "date_to": today})
        orders_dash = self.get("/orders/dashboard")
        finance = self.get(f"/finance/summary?{query}")
        dashboard = self.get(f"/analytics/dashboard-summary?{query}")
        self.after_flow["orders_dashboard"] = orders_dash
        self.after_flow["finance"] = finance
        self.after_flow["dashboard_summary"] = dashboard

        self.check("dashboard_order_visibility", dec(orders_dash.get("orders_today")) - dec(self.baseline["orders_dashboard"].get("orders_today")) >= 1, f"orders_today={orders_dash.get('orders_today')}")
        self.check("dashboard_revenue_visibility", dec(orders_dash.get("revenue_today")) - dec(self.baseline["orders_dashboard"].get("revenue_today")) >= Decimal("1598.00"), f"revenue_today={orders_dash.get('revenue_today')}")
        self.check("dashboard_profit_visibility", dec(orders_dash.get("profit_today")) - dec(self.baseline["orders_dashboard"].get("profit_today")) >= Decimal("598.00"), f"profit_today={orders_dash.get('profit_today')}")
        self.check("finance_visibility", dec(finance.get("revenue")) - dec(self.baseline["finance"].get("revenue")) >= Decimal("1598.00") and dec(finance.get("net_profit")) - dec(self.baseline["finance"].get("net_profit")) >= Decimal("548.00"), f"finance revenue={finance.get('revenue')} profit={finance.get('net_profit')}")
        sales = dashboard.get("sales", {}) if isinstance(dashboard, dict) else {}
        self.check("main_dashboard_order_visibility", dec(sales.get("orders_count")) - dec(self.baseline["dashboard_summary"].get("sales", {}).get("orders_count")) >= 1, f"orders={sales.get('orders_count')}")
        self.check("main_dashboard_revenue_visibility", dec(sales.get("revenue")) - dec(self.baseline["dashboard_summary"].get("sales", {}).get("revenue")) >= Decimal("1598.00"), f"revenue={sales.get('revenue')}")
        self.check("main_dashboard_profit_visibility", dec(sales.get("net_profit")) - dec(self.baseline["dashboard_summary"].get("sales", {}).get("net_profit")) >= Decimal("598.00"), f"profit={sales.get('net_profit')}")
        self.check("revenue_profit_state_honest", dec(order["revenue"]) == Decimal("1598.00") and dec(order["net_profit"]) == Decimal("598.00") and dec(finance.get("revenue")) >= Decimal("1598.00"), "order and finance values are internally consistent")

    def cleanup(self) -> None:
        # Delete shipment first so order can be archived without a visible draft shipment.
        if self.created.get("shipment_id"):
            code, payload = self.req("DELETE", f"/shipments/{self.created['shipment_id']}")
            self.cleanup_actions.append({"entity": "shipment", "id": self.created["shipment_id"], "http": code})
        # Cancel order to release reservation, then archive it.
        if self.created.get("order_id"):
            code, payload = self.req("POST", f"/orders/{self.created['order_id']}/status", body={"status": "CANCELLED", "note": f"{self.marker} cleanup cancel"})
            self.cleanup_actions.append({"entity": "order_cancel", "id": self.created["order_id"], "http": code})
            code, payload = self.req("DELETE", f"/orders/{self.created['order_id']}")
            self.cleanup_actions.append({"entity": "order_archive", "id": self.created["order_id"], "http": code})
        # Reset stock to zero through public API before archiving variant/product.
        # InventoryTransactionCreate requires quantity > 0, so ADJUSTMENT to 0 is invalid.
        # After order cancellation reserved_quantity should be 0; remove remaining stock with STOCK_OUT.
        if self.inventory_id:
            try:
                inventory = self.get(f"/inventory/{self.inventory_id}")
                stock_quantity = int(inventory.get("stock_quantity") or 0)
                reserved_quantity = int(inventory.get("reserved_quantity") or 0)
                if reserved_quantity > 0:
                    code, payload = self.req("POST", f"/inventory/{self.inventory_id}/transactions", body={"transaction_type": "UNRESERVE", "quantity": reserved_quantity, "reason": f"{self.marker} cleanup unreserve"})
                    self.cleanup_actions.append({"entity": "inventory_unreserve", "id": self.inventory_id, "http": code})
                if stock_quantity > 0:
                    code, payload = self.req("POST", f"/inventory/{self.inventory_id}/transactions", body={"transaction_type": "STOCK_OUT", "quantity": stock_quantity, "reason": f"{self.marker} cleanup stock-out"})
                    self.cleanup_actions.append({"entity": "inventory_stock_out", "id": self.inventory_id, "http": code})
            except Exception as exc:
                self.cleanup_actions.append({"entity": "inventory_reset", "id": self.inventory_id, "http": 0, "error": exc.__class__.__name__})
        if self.created.get("variant_id"):
            code, payload = self.req("DELETE", f"/products/variants/{self.created['variant_id']}")
            self.cleanup_actions.append({"entity": "variant", "id": self.created["variant_id"], "http": code})
        if self.created.get("product_id"):
            code, payload = self.req("DELETE", f"/products/{self.created['product_id']}")
            self.cleanup_actions.append({"entity": "product", "id": self.created["product_id"], "http": code})
        if self.created.get("customer_id"):
            code, payload = self.req("DELETE", f"/customers/{self.created['customer_id']}")
            self.cleanup_actions.append({"entity": "customer", "id": self.created["customer_id"], "http": code})
        if self.created.get("lead_id"):
            code, payload = self.req("DELETE", f"/leads/{self.created['lead_id']}")
            self.cleanup_actions.append({"entity": "lead", "id": self.created["lead_id"], "http": code})

        try:
            self.final_state["counts"] = self.active_counts()
            self.check("cleanup_entities_archived", all(v == 0 for k, v in self.final_state["counts"].items() if k != "inventory"), f"final counts={self.final_state['counts']}", fatal=False)
            self.check("cleanup_inventory_reset", self.final_state["counts"].get("inventory", 0) == 0, f"final inventory={self.final_state['counts'].get('inventory')}", fatal=False)
        except Exception as exc:
            self.warnings.append({"code": "cleanup_verification_failed", "detail": exc.__class__.__name__})

    def run(self) -> int:
        error: str | None = None
        try:
            self.preflight()
            self.create_flow()
        except Exception as exc:
            error = f"{exc.__class__.__name__}: {exc}"
        finally:
            if self.token:
                try:
                    self.cleanup()
                except Exception as exc:
                    self.warnings.append({"code": "cleanup_exception", "detail": exc.__class__.__name__})
            self.write_artifacts(error)
        return 0 if error is None and self.decision() == "PASS" else 1

    def decision(self) -> str:
        required = [
            "controlled_write_flag", "runtime_revision", "frontend_available", "backend_health",
            "owner_login", "owner_auth_me", "qa_workspace_membership", "qa_owner_role",
            "qa_workspace_name", "workspace_id_exact", "workspace_active", "qa_workspace_empty",
            "qa_inventory_empty", "analyst_write_rejected", "lead_create", "lead_workspace",
            "lead_convert_customer", "customer_workspace", "product_create", "product_workspace",
            "variant_create", "variant_workspace", "inventory_auto_created", "stock_in",
            "stock_after_stock_in", "cross_workspace_context_rejected",
            "foreign_customer_reference_rejected", "order_create", "order_workspace",
            "order_number_created", "order_variant_exact", "order_quantity_exact",
            "order_revenue_profit_formula", "initial_status_history", "order_reservation",
            "payment_status_update", "payment_status_paid", "order_status_confirmed",
            "status_history_created", "shipment_draft_create", "shipment_workspace",
            "shipment_remains_draft", "nova_poshta_fields_absent", "nova_poshta_api_not_called",
            "dashboard_order_visibility", "dashboard_revenue_visibility", "dashboard_profit_visibility",
            "finance_visibility", "main_dashboard_order_visibility", "main_dashboard_revenue_visibility",
            "main_dashboard_profit_visibility", "revenue_profit_state_honest",
            "cleanup_entities_archived", "cleanup_inventory_reset",
        ]
        missing = [name for name in required if name not in self.checks]
        failed = [name for name in required if self.checks.get(name, {}).get("status") != "PASS"]
        if missing or failed:
            return "FAIL"
        if any("/nova-poshta/" in path for path in self.requested_paths):
            return "FAIL"
        return "PASS"

    def write_artifacts(self, error: str | None) -> None:
        ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "decision": self.decision(),
            "started_at": self.started_at,
            "finished_at": now(),
            "runtime_revision": self.runtime_revision,
            "expected_revision": self.expected_revision,
            "workspace_name": EXPECTED_QA_WORKSPACE_NAME,
            "marker_prefix": "QA-8A1-E2E",
            "checks": self.checks,
            "issues": self.issues,
            "warnings": self.warnings,
            "cleanup_actions": self.cleanup_actions,
            "safety": {
                "controlled_writes": self.allow_writes,
                "nova_poshta_routes_requested": [p for p in self.requested_paths if "/nova-poshta/" in p],
                "migrations_executed": False,
                "credentials_suppressed": True,
                "tokens_suppressed": True,
            },
            "baseline": self.baseline,
            "after_flow": self.after_flow,
            "final_state": self.final_state,
            "error": error,
        }
        ARTIFACT.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
        summary = {
            "decision": data["decision"],
            "passed_checks": sum(1 for item in self.checks.values() if item.get("status") == "PASS"),
            "failed_checks": sum(1 for item in self.checks.values() if item.get("status") == "FAIL"),
            "warnings": len(self.warnings),
            "cleanup_actions": len(self.cleanup_actions),
            "nova_poshta_routes_requested": 0 if not data["safety"]["nova_poshta_routes_requested"] else len(data["safety"]["nova_poshta_routes_requested"]),
            "error": error,
        }
        SUMMARY.write_text(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")


if __name__ == "__main__":
    sys.exit(Gate().run())
