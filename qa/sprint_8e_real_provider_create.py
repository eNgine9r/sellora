#!/usr/bin/env python3
"""Sprint 8E controlled real-provider TTN creation evidence.

Safety properties:
- exits before fixture creation while provider writes are disabled;
- operates only in the dedicated QA8E workspace;
- creates one synthetic order and one local shipment;
- sends two concurrent create requests to prove durable idempotency;
- preserves the fixture for the mandatory Render restart boundary;
- never prints credentials, full phone numbers, full TTNs, or document refs.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import os
import re
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

import httpx

API_ROOT = os.environ["STAGING_API_URL"].rstrip("/")
API = API_ROOT + "/api/v1"
FRONTEND = os.environ["STAGING_FRONTEND_URL"].rstrip("/")
EXPECTED_COMMIT = os.environ["EXPECTED_RUNTIME_COMMIT"].lower()
WORKSPACE_ID = os.environ["QA8E_WORKSPACE_ID"]
OUT = Path("artifacts/sprint-8e/controlled-create.json")
RUN = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
PREFIX = f"QA8E-{RUN}"
TIMEOUT = httpx.Timeout(connect=20, read=90, write=90, pool=20)


class Closure:
    def __init__(self) -> None:
        self.checks: list[dict[str, Any]] = []
        self.sessions: dict[str, str] = {}
        self.runtime: dict[str, Any] = {}
        self.created: dict[str, str] = {}
        self.network = {
            "requests": 0,
            "create_ttn_requests": 0,
            "sync_requests": 0,
            "http_5xx": 0,
        }
        self.safe_error: str | None = None
        self.decision = "FAIL"
        self.tracking_hash: str | None = None
        self.tracking_suffix: str | None = None

    @staticmethod
    def redact_identifier(value: str | None) -> dict[str, Any] | None:
        if not value:
            return None
        return {
            "sha256_prefix": hashlib.sha256(value.encode("utf-8")).hexdigest()[:16],
            "suffix": value[-4:],
            "length": len(value),
        }

    @staticmethod
    def safe(value: Any) -> Any:
        blocked = {
            "access_token", "refresh_token", "authorization", "password", "api_key",
            "masked_api_key", "phone", "recipient_phone", "sender_phone",
            "tracking_number", "document_ref", "nova_poshta_document_ref",
            "nova_poshta_document_number", "external_ref",
        }
        if isinstance(value, dict):
            return {str(k): Closure.safe(v) for k, v in value.items() if str(k).lower() not in blocked}
        if isinstance(value, list):
            return [Closure.safe(v) for v in value[:30]]
        text = str(value)
        text = re.sub(r"Bearer\s+\S+", "Bearer [REDACTED]", text, flags=re.I)
        text = re.sub(r"\beyJ[A-Za-z0-9._-]{20,}\b", "[TOKEN]", text)
        text = re.sub(r"\b\d{11,14}\b", "[IDENTIFIER]", text)
        return text[:500]

    def check(self, gate: str, name: str, ok: bool, detail: Any = None) -> None:
        item: dict[str, Any] = {"gate": gate, "name": name, "status": "PASS" if ok else "FAIL"}
        if detail is not None:
            item["detail"] = self.safe(detail)
        self.checks.append(item)
        print(json.dumps(item, ensure_ascii=False), flush=True)

    def headers(self, role: str, workspace: str = WORKSPACE_ID) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.sessions[role]}",
            "X-Workspace-ID": workspace,
            "Cache-Control": "no-cache",
        }

    def request(
        self,
        method: str,
        path: str,
        *,
        role: str | None = None,
        workspace: str = WORKSPACE_ID,
        payload: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        expected: tuple[int, ...] = (200,),
    ) -> tuple[int, Any]:
        url = path if path.startswith("http") else API + path
        headers = self.headers(role, workspace) if role else {"Cache-Control": "no-cache"}
        self.network["requests"] += 1
        if "create-ttn" in url:
            self.network["create_ttn_requests"] += 1
        if "sync-status" in url:
            self.network["sync_requests"] += 1
        with httpx.Client(timeout=TIMEOUT, follow_redirects=True, headers={"Connection": "close"}) as client:
            response = client.request(method, url, headers=headers, json=payload, params=params)
        if response.status_code >= 500:
            self.network["http_5xx"] += 1
        try:
            body: Any = response.json()
        except Exception:
            body = response.text[:300]
        print(f"HTTP {method} {httpx.URL(url).path} -> {response.status_code}", flush=True)
        if response.status_code not in expected:
            raise RuntimeError(f"{method} {httpx.URL(url).path}: HTTP {response.status_code}")
        return response.status_code, body

    def login(self, role: str, email_env: str, password_env: str) -> None:
        _, body = self.request(
            "POST",
            "/auth/login",
            payload={"email": os.environ[email_env], "password": os.environ[password_env]},
            expected=(200,),
        )
        self.sessions[role] = str(body["access_token"])
        _, me = self.request("GET", "/auth/me", role=role, expected=(200,))
        membership = next((m for m in me.get("memberships", []) if str(m.get("workspace_id")) == WORKSPACE_ID), None)
        self.check("1", f"{role} QA8E membership", bool(membership), {"role": membership.get("role") if membership else None})
        if not membership:
            raise RuntimeError(f"{role} lacks QA8E membership")

    def environment(self) -> bool:
        _, health = self.request("GET", API_ROOT + "/health", expected=(200,))
        commit = str(health.get("runtime_commit", "")).lower()
        self.runtime = {
            "status": health.get("status"),
            "runtime_commit": commit,
            "process_started_at": health.get("process_started_at"),
        }
        runtime_ok = health.get("status") == "ok" and commit.startswith(EXPECTED_COMMIT[:12])
        self.check("1", "backend runtime identity", runtime_ok, self.runtime)
        if not runtime_ok:
            raise RuntimeError("Unexpected Render runtime")

        with httpx.Client(timeout=TIMEOUT, follow_redirects=True) as client:
            frontend = client.get(FRONTEND + "/login")
        self.check("1", "frontend staging reachable", frontend.status_code == 200, {"status": frontend.status_code})
        if frontend.status_code != 200:
            raise RuntimeError("Frontend staging unavailable")

        self.login("OWNER", "STAGING_OWNER_EMAIL", "STAGING_OWNER_PASSWORD")
        self.login("MANAGER", "STAGING_MANAGER_EMAIL", "STAGING_MANAGER_PASSWORD")
        self.login("ANALYST", "STAGING_ANALYST_EMAIL", "STAGING_ANALYST_PASSWORD")

        _, settings = self.request("GET", "/integrations/nova-poshta/settings", role="OWNER", expected=(200,))
        configured = settings.get("status") == "CONNECTED" and settings.get("sender_configured") is True
        writes = settings.get("provider_writes_enabled") is True
        self.check("1", "real provider connection and sender configured", configured)
        self.check("5", "provider writes explicitly enabled", writes)
        if not configured:
            raise RuntimeError("Nova Poshta connection or sender configuration is incomplete")
        if not writes:
            self.decision = "BLOCKED_WRITES_DISABLED"
            return False
        return True

    def inventory_for_variant(self, variant_id: str) -> dict[str, Any]:
        _, rows = self.request("GET", "/inventory", role="OWNER", expected=(200,))
        row = next((item for item in rows if str(item.get("product_variant_id")) == variant_id), None)
        if not row:
            raise RuntimeError("Inventory record not found")
        return row

    @staticmethod
    def inventory_state(row: dict[str, Any]) -> dict[str, int]:
        stock = int(row.get("stock_quantity", 0))
        reserved = int(row.get("reserved_quantity", 0))
        return {"stock": stock, "reserved": reserved, "available": stock - reserved}

    def create_fixtures(self) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
        phone = os.environ["STAGING_NOVA_POSHTA_SENDER_PHONE"]
        _, customer = self.request(
            "POST", "/customers", role="MANAGER", expected=(201,),
            payload={
                "name": f"{PREFIX} Controlled Recipient",
                "phone": phone,
                "instagram_username": f"qa8e_{RUN}",
                "city": "Synthetic QA",
                "region": "Synthetic QA",
            },
        )
        self.created["customer_id"] = str(customer["id"])

        _, product = self.request(
            "POST", "/products", role="MANAGER", expected=(201,),
            payload={
                "name": f"{PREFIX} Controlled Product",
                "sku": f"{PREFIX}-P",
                "description": "Synthetic Sprint 8E provider validation fixture",
                "category": "QA",
                "brand": "Sellora QA",
            },
        )
        self.created["product_id"] = str(product["id"])

        _, variant = self.request(
            "POST", "/products/variants", role="MANAGER", expected=(201,),
            payload={
                "product_id": product["id"],
                "sku": f"{PREFIX}-V",
                "color": "Synthetic",
                "size": "QA8E",
                "price": "100.00",
                "initial_stock_quantity": 5,
                "minimum_quantity": 1,
            },
        )
        self.created["variant_id"] = str(variant["id"])

        _, order = self.request(
            "POST", "/orders", role="MANAGER", expected=(201,),
            payload={
                "customer_id": customer["id"],
                "status": "NEW",
                "payment_status": "PENDING",
                "items": [{
                    "product_variant_id": variant["id"],
                    "quantity": 1,
                    "unit_price": "100.00",
                    "unit_cost": "40.00",
                }],
                "notes": f"{PREFIX} controlled real-provider validation",
            },
        )
        self.created["order_id"] = str(order["id"])

        _, shipment = self.request(
            "POST", "/shipments", role="MANAGER", expected=(201,),
            payload={
                "order_id": order["id"],
                "customer_id": customer["id"],
                "carrier": "NOVA_POSHTA",
                "status": "DRAFT",
                "recipient_name": "Sellora QA",
                "recipient_phone": phone,
                "city": "QA recipient city",
                "warehouse": "QA recipient warehouse",
                "declared_value": "100.00",
                "cod_amount": "0.00",
                "notes": f"{PREFIX} one controlled provider document; no physical shipment",
                "nova_poshta_city_ref": os.environ["STAGING_NOVA_POSHTA_SENDER_CITY_REF"],
                "nova_poshta_warehouse_ref": os.environ["STAGING_NOVA_POSHTA_SENDER_WAREHOUSE_REF"],
            },
        )
        self.created["shipment_id"] = str(shipment["id"])

        inventory = self.inventory_for_variant(str(variant["id"]))
        self.check("5", "synthetic fixture created in QA8E workspace", True, {
            "customer_id": customer["id"],
            "product_id": product["id"],
            "variant_id": variant["id"],
            "order_id": order["id"],
            "shipment_id": shipment["id"],
        })
        self.check("5", "order reservation before provider call", self.inventory_state(inventory) == {"stock": 5, "reserved": 1, "available": 4}, self.inventory_state(inventory))
        return order, shipment, inventory

    async def concurrent_create(self, shipment_id: str) -> list[tuple[int, dict[str, Any]]]:
        url = API + f"/shipments/{shipment_id}/nova-poshta/create-ttn"
        headers = self.headers("MANAGER")

        async def call() -> tuple[int, dict[str, Any]]:
            async with httpx.AsyncClient(timeout=TIMEOUT, follow_redirects=True, headers={"Connection": "close"}) as client:
                response = await client.post(url, headers=headers)
            self.network["requests"] += 1
            self.network["create_ttn_requests"] += 1
            if response.status_code >= 500:
                self.network["http_5xx"] += 1
            try:
                body = response.json()
            except Exception:
                body = {"message": response.text[:300]}
            print(f"HTTP POST {httpx.URL(url).path} -> {response.status_code}", flush=True)
            return response.status_code, body

        return list(await asyncio.gather(call(), call()))

    def provider_flow(self, order_before: dict[str, Any], inventory_before: dict[str, Any]) -> None:
        shipment_id = self.created["shipment_id"]
        results = asyncio.run(self.concurrent_create(shipment_id))
        status_ok = all(code == 200 for code, _ in results)
        tracking_values = {
            str(body.get("tracking_number"))
            for code, body in results
            if code == 200 and body.get("tracking_number")
        }
        document_values = {
            str(body.get("document_ref"))
            for code, body in results
            if code == 200 and body.get("document_ref")
        }
        self.check("6", "two concurrent create requests completed safely", status_ok, {"statuses": [code for code, _ in results]})
        self.check("6", "concurrent responses resolve to one TTN", len(tracking_values) == 1, {"unique_tracking_count": len(tracking_values)})
        self.check("6", "concurrent responses resolve to one provider document ref", len(document_values) == 1, {"unique_document_ref_count": len(document_values)})
        if len(tracking_values) != 1 or len(document_values) != 1:
            raise RuntimeError("Controlled TTN creation did not return one durable provider result")

        tracking = next(iter(tracking_values))
        document_ref = next(iter(document_values))
        self.tracking_hash = hashlib.sha256(tracking.encode("utf-8")).hexdigest()[:16]
        self.tracking_suffix = tracking[-4:]

        _, shipment = self.request("GET", f"/shipments/{shipment_id}", role="OWNER", expected=(200,))
        stored_tracking = str(shipment.get("tracking_number") or shipment.get("nova_poshta_document_number") or "")
        stored_ref = str(shipment.get("nova_poshta_document_ref") or "")
        self.check("5", "Sellora stores exactly one TTN and external ref", stored_tracking == tracking and stored_ref == document_ref, {
            "tracking": self.redact_identifier(stored_tracking),
            "document_ref": self.redact_identifier(stored_ref),
            "shipment_status": shipment.get("status"),
            "operation_state": shipment.get("nova_poshta_create_state"),
        })

        _, repeated = self.request(
            "POST", f"/shipments/{shipment_id}/nova-poshta/create-ttn",
            role="MANAGER", expected=(200,),
        )
        repeated_tracking = str(repeated.get("tracking_number") or "")
        self.check("6", "completed request returns existing result", repeated.get("success") is True and repeated.get("reused_existing_result") is True and repeated_tracking == tracking, {
            "reused_existing_result": repeated.get("reused_existing_result"),
            "operation_state": repeated.get("operation_state"),
            "tracking": self.redact_identifier(repeated_tracking),
        })

        code, _ = self.request(
            "POST", f"/shipments/{shipment_id}/nova-poshta/create-ttn",
            role="ANALYST", expected=(403,),
        )
        self.check("10", "ANALYST TTN creation denied", code == 403)
        code, _ = self.request(
            "POST", f"/shipments/{shipment_id}/nova-poshta/create-ttn",
            role="MANAGER", workspace=str(uuid4()), expected=(403,),
        )
        self.check("11", "foreign-workspace TTN creation denied", code == 403)

        code, _ = self.request(
            "POST", "/shipments", role="MANAGER", expected=(400,),
            payload={
                "order_id": self.created["order_id"],
                "customer_id": self.created["customer_id"],
                "carrier": "NOVA_POSHTA",
                "status": "DRAFT",
                "recipient_name": "Sellora QA duplicate",
                "recipient_phone": os.environ["STAGING_NOVA_POSHTA_SENDER_PHONE"],
                "city": "QA",
                "warehouse": "QA",
                "declared_value": "100.00",
                "nova_poshta_city_ref": os.environ["STAGING_NOVA_POSHTA_SENDER_CITY_REF"],
                "nova_poshta_warehouse_ref": os.environ["STAGING_NOVA_POSHTA_SENDER_WAREHOUSE_REF"],
            },
        )
        self.check("5", "second active local shipment rejected", code == 400)

        code, _ = self.request(
            "POST", f"/shipments/{shipment_id}/cancel",
            role="MANAGER", expected=(409,),
        )
        self.check("13", "provider-backed local cancellation truthfully blocked", code == 409)

        _, order_after = self.request("GET", f"/orders/{self.created['order_id']}", role="OWNER", expected=(200,))
        inventory_after = self.inventory_for_variant(self.created["variant_id"])
        order_core_before = {
            "status": order_before.get("status"),
            "payment_status": order_before.get("payment_status"),
            "revenue": order_before.get("revenue"),
            "items": [(str(i.get("product_variant_id")), int(i.get("quantity", 0))) for i in order_before.get("items", [])],
        }
        order_core_after = {
            "status": order_after.get("status"),
            "payment_status": order_after.get("payment_status"),
            "revenue": order_after.get("revenue"),
            "items": [(str(i.get("product_variant_id")), int(i.get("quantity", 0))) for i in order_after.get("items", [])],
        }
        self.check("5", "TTN creation leaves order unchanged", order_core_after == order_core_before, order_core_after)
        self.check("5", "TTN creation leaves inventory unchanged", self.inventory_state(inventory_after) == self.inventory_state(inventory_before), self.inventory_state(inventory_after))

        _, sync_one = self.request(
            "POST", f"/shipments/{shipment_id}/nova-poshta/sync-status",
            role="MANAGER", expected=(200,),
        )
        _, sync_two = self.request(
            "POST", f"/shipments/{shipment_id}/nova-poshta/sync-status",
            role="MANAGER", expected=(200,),
        )
        self.check("8", "manual tracking sync receives provider status", sync_one.get("success") is True and bool(sync_one.get("raw_status")), {
            "success": sync_one.get("success"),
            "normalized_status": sync_one.get("normalized_status"),
            "manual_review_required": sync_one.get("manual_review_required"),
            "synced_at_present": bool(sync_one.get("synced_at")),
        })
        self.check("8", "repeated tracking sync remains side-effect safe", sync_two.get("success") is True, {
            "normalized_status": sync_two.get("normalized_status"),
            "manual_review_required": sync_two.get("manual_review_required"),
        })

        _, order_after_sync = self.request("GET", f"/orders/{self.created['order_id']}", role="OWNER", expected=(200,))
        inventory_after_sync = self.inventory_for_variant(self.created["variant_id"])
        sync_order_core = {
            "status": order_after_sync.get("status"),
            "payment_status": order_after_sync.get("payment_status"),
            "revenue": order_after_sync.get("revenue"),
            "items": [(str(i.get("product_variant_id")), int(i.get("quantity", 0))) for i in order_after_sync.get("items", [])],
        }
        self.check("8", "tracking sync leaves order/payment unchanged", sync_order_core == order_core_before, sync_order_core)
        self.check("8", "tracking sync leaves stock/reservation unchanged", self.inventory_state(inventory_after_sync) == self.inventory_state(inventory_before), self.inventory_state(inventory_after_sync))
        self.check("5", "unexpected HTTP 5xx", self.network["http_5xx"] == 0, self.network)

    def write_report(self) -> None:
        OUT.parent.mkdir(parents=True, exist_ok=True)
        if self.decision not in {"BLOCKED_WRITES_DISABLED"}:
            self.decision = "PASS_PENDING_RESTART_AND_CLEANUP" if self.safe_error is None and all(c["status"] == "PASS" for c in self.checks) else "FAIL"
        report = {
            "sprint": "8E",
            "phase": "controlled-real-provider-create",
            "decision": self.decision,
            "prefix": PREFIX,
            "runtime": self.runtime,
            "checks": self.checks,
            "created": self.created,
            "tracking_evidence": {
                "sha256_prefix": self.tracking_hash,
                "suffix": self.tracking_suffix,
            } if self.tracking_hash else None,
            "network": self.network,
            "provider_document_expected": 1 if self.tracking_hash else 0,
            "cleanup_required": bool(self.tracking_hash),
            "restart_required": bool(self.tracking_hash),
            "safe_error": self.safe_error,
            "generated_at": datetime.now(UTC).isoformat(),
        }
        encoded = json.dumps(report, ensure_ascii=False, indent=2)
        secret_values = [
            os.environ.get("STAGING_OWNER_PASSWORD"),
            os.environ.get("STAGING_MANAGER_PASSWORD"),
            os.environ.get("STAGING_ANALYST_PASSWORD"),
            os.environ.get("STAGING_NOVA_POSHTA_SENDER_PHONE"),
        ]
        if any(value and value in encoded for value in secret_values):
            report["decision"] = "FAIL"
            report["safe_error"] = "SANITIZATION_FAILED"
            encoded = json.dumps(report, ensure_ascii=False, indent=2)
        OUT.write_text(encoded, encoding="utf-8")
        print(json.dumps({"decision": report["decision"], "checks": len(report["checks"]), "artifact": str(OUT)}), flush=True)

    def run(self) -> int:
        try:
            if not self.environment():
                return 2
            order, _shipment, inventory = self.create_fixtures()
            self.provider_flow(order, inventory)
        except Exception as exc:
            self.safe_error = self.safe(exc)
            print(f"SAFE_ERROR: {self.safe_error}", flush=True)
        finally:
            self.write_report()
        return 0 if self.decision == "PASS_PENDING_RESTART_AND_CLEANUP" else 2 if self.decision == "BLOCKED_WRITES_DISABLED" else 1


if __name__ == "__main__":
    sys.exit(Closure().run())
