#!/usr/bin/env python3
"""Recover the exact Sprint 8E FAILED_SAFE fixture without creating another order.

Safety properties:
- resolves recipient city/warehouse descriptions through Nova Poshta directory reads;
- targets one exact synthetic fixture in the dedicated QA8E workspace;
- refuses to run if a TTN/provider ref already exists or the fixture identity differs;
- performs the durable concurrent create proof once;
- preserves the successful fixture for the mandatory Render restart boundary;
- writes only sanitized evidence (no API keys, credentials, phones, full TTNs or refs).
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
NP_API_URL = os.environ.get("NOVA_POSHTA_API_URL", "https://api.novaposhta.ua/v2.0/json/")
OUT = Path("artifacts/sprint-8e/failed-safe-recovery.json")
TIMEOUT = httpx.Timeout(connect=30, read=90, write=90, pool=30)

PREFIX = "QA8E-20260716103246"
SHIPMENT_ID = "15e3f667-e4f1-4d69-be43-91aaaf9fd517"
ORDER_ID = "cdd31ee4-5a6f-4a4b-8869-607795572984"
CUSTOMER_ID = "9d492272-0341-4186-890b-7bb7228274ae"
PRODUCT_ID = "bf2e9c1c-2ece-4536-926f-83db215f475e"
VARIANT_ID = "3e40960c-6eaa-41ad-8cd1-6f3ace0796ec"


class Recovery:
    def __init__(self) -> None:
        self.sessions: dict[str, str] = {}
        self.runtime: dict[str, Any] = {}
        self.checks: list[dict[str, Any]] = []
        self.network = {
            "requests": 0,
            "directory_requests": 0,
            "create_ttn_requests": 0,
            "sync_requests": 0,
            "http_5xx": 0,
        }
        self.safe_error: str | None = None
        self.decision = "FAIL"
        self.tracking_hash: str | None = None
        self.tracking_suffix: str | None = None

    @staticmethod
    def safe(value: Any) -> Any:
        blocked_keys = {
            "access_token", "refresh_token", "authorization", "password", "api_key",
            "apikey", "phone", "recipient_phone", "sender_phone", "tracking_number",
            "document_ref", "nova_poshta_document_ref", "nova_poshta_document_number",
            "external_ref", "city_description", "warehouse_description",
        }
        if isinstance(value, dict):
            return {
                str(key): Recovery.safe(item)
                for key, item in value.items()
                if str(key).lower() not in blocked_keys
            }
        if isinstance(value, list):
            return [Recovery.safe(item) for item in value[:30]]
        text = str(value or "")
        for env_name in (
            "STAGING_OWNER_EMAIL", "STAGING_OWNER_PASSWORD",
            "STAGING_MANAGER_EMAIL", "STAGING_MANAGER_PASSWORD",
            "STAGING_ANALYST_EMAIL", "STAGING_ANALYST_PASSWORD",
            "STAGING_NOVA_POSHTA_API_KEY", "STAGING_NOVA_POSHTA_SENDER_PHONE",
        ):
            secret = os.environ.get(env_name)
            if secret:
                text = text.replace(secret, f"[{env_name}]")
        text = re.sub(r"Bearer\s+\S+", "Bearer [REDACTED]", text, flags=re.I)
        text = re.sub(r"\beyJ[A-Za-z0-9._-]{20,}\b", "[TOKEN]", text)
        text = re.sub(r"\b\d{11,14}\b", "[IDENTIFIER]", text)
        return text[:500]

    @staticmethod
    def redact_identifier(value: str | None) -> dict[str, Any] | None:
        if not value:
            return None
        return {
            "sha256_prefix": hashlib.sha256(value.encode("utf-8")).hexdigest()[:16],
            "suffix": value[-4:],
            "length": len(value),
        }

    def check(self, gate: str, name: str, ok: bool, detail: Any | None = None) -> None:
        item: dict[str, Any] = {"gate": gate, "name": name, "status": "PASS" if ok else "FAIL"}
        if detail is not None:
            item["detail"] = self.safe(detail)
        self.checks.append(item)
        print(json.dumps(item, ensure_ascii=False), flush=True)
        if not ok:
            raise RuntimeError(name)

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
            response = client.request(method, url, headers=headers, json=payload)
        if response.status_code >= 500:
            self.network["http_5xx"] += 1
        try:
            body: Any = response.json() if response.content else {}
        except Exception:
            body = {"message": response.text[:300]}
        print(f"HTTP {method} {httpx.URL(url).path} -> {response.status_code}", flush=True)
        if response.status_code not in expected:
            raise RuntimeError(
                f"Unexpected HTTP {response.status_code} for {method} {httpx.URL(url).path}: {self.safe(body)}"
            )
        return response.status_code, body

    def provider_directory_call(self, method: str, properties: dict[str, Any]) -> dict[str, Any]:
        payload = {
            "apiKey": os.environ["STAGING_NOVA_POSHTA_API_KEY"],
            "modelName": "Address",
            "calledMethod": method,
            "methodProperties": properties,
        }
        with httpx.Client(timeout=TIMEOUT, follow_redirects=True, headers={"Connection": "close"}) as client:
            response = client.post(NP_API_URL, json=payload)
        self.network["requests"] += 1
        self.network["directory_requests"] += 1
        if response.status_code >= 500:
            self.network["http_5xx"] += 1
        response.raise_for_status()
        body = response.json()
        if body.get("success") is not True:
            raise RuntimeError(
                f"Nova Poshta directory {method} failed: {self.safe({'errors': body.get('errors', [])})}"
            )
        return body

    def resolve_recipient_labels(self) -> tuple[str, str]:
        city_ref = os.environ["STAGING_NOVA_POSHTA_SENDER_CITY_REF"]
        warehouse_ref = os.environ["STAGING_NOVA_POSHTA_SENDER_WAREHOUSE_REF"]

        city_body = self.provider_directory_call("getCities", {"Ref": city_ref, "Limit": "1"})
        city_rows = [item for item in city_body.get("data", []) if str(item.get("Ref")) == city_ref]
        self.check("5", "recipient city ref resolves through provider directory", len(city_rows) == 1, {
            "matching_count": len(city_rows),
        })
        city_description = str(city_rows[0].get("Description") or "").strip()
        self.check("5", "recipient city description is present", bool(city_description), {
            "description_present": bool(city_description),
            "description_length": len(city_description),
        })

        warehouse_body = self.provider_directory_call(
            "getWarehouses",
            {"Ref": warehouse_ref, "CityRef": city_ref, "Limit": "1"},
        )
        warehouse_rows = [
            item for item in warehouse_body.get("data", []) if str(item.get("Ref")) == warehouse_ref
        ]
        self.check("5", "recipient warehouse ref resolves through provider directory", len(warehouse_rows) == 1, {
            "matching_count": len(warehouse_rows),
        })
        warehouse_description = str(warehouse_rows[0].get("Description") or "").strip()
        self.check("5", "recipient warehouse description is present", bool(warehouse_description), {
            "description_present": bool(warehouse_description),
            "description_length": len(warehouse_description),
        })
        return city_description, warehouse_description

    def login(self, role: str, email_env: str, password_env: str) -> None:
        _, tokens = self.request(
            "POST",
            "/auth/login",
            payload={"email": os.environ[email_env], "password": os.environ[password_env]},
            expected=(200,),
        )
        self.sessions[role] = str(tokens.get("access_token") or "")
        self.check("1", f"{role} login succeeded", bool(self.sessions[role]))
        _, me = self.request("GET", "/auth/me", role=role, expected=(200,))
        membership = next(
            (item for item in me.get("memberships", []) if str(item.get("workspace_id")) == WORKSPACE_ID),
            None,
        )
        self.check("1", f"{role} QA8E membership", bool(membership), {
            "role": membership.get("role") if membership else None,
        })

    def environment(self) -> None:
        _, health = self.request("GET", API_ROOT + "/health", expected=(200,))
        commit = str(health.get("runtime_commit") or "").lower()
        self.runtime = {
            "status": health.get("status"),
            "runtime_commit": commit,
            "process_started_at": health.get("process_started_at"),
        }
        self.check(
            "1",
            "backend runtime identity",
            health.get("status") == "ok" and commit.startswith(EXPECTED_COMMIT[:12]),
            self.runtime,
        )
        with httpx.Client(timeout=TIMEOUT, follow_redirects=True) as client:
            frontend = client.get(FRONTEND + "/login")
        self.check("1", "frontend staging reachable", frontend.status_code == 200, {
            "status": frontend.status_code,
        })
        self.login("OWNER", "STAGING_OWNER_EMAIL", "STAGING_OWNER_PASSWORD")
        self.login("MANAGER", "STAGING_MANAGER_EMAIL", "STAGING_MANAGER_PASSWORD")
        self.login("ANALYST", "STAGING_ANALYST_EMAIL", "STAGING_ANALYST_PASSWORD")
        _, settings = self.request("GET", "/integrations/nova-poshta/settings", role="OWNER", expected=(200,))
        self.check(
            "5",
            "provider writes remain explicitly enabled",
            settings.get("provider_writes_enabled") is True,
            {"provider_writes_enabled": settings.get("provider_writes_enabled")},
        )

    @staticmethod
    def inventory_state(row: dict[str, Any]) -> dict[str, int]:
        stock = int(row.get("stock_quantity", 0))
        reserved = int(row.get("reserved_quantity", 0))
        return {"stock": stock, "reserved": reserved, "available": stock - reserved}

    def inventory_for_variant(self) -> dict[str, Any]:
        _, rows = self.request("GET", "/inventory", role="OWNER", expected=(200,))
        row = next((item for item in rows if str(item.get("product_variant_id")) == VARIANT_ID), None)
        if row is None:
            raise RuntimeError("Exact recovery inventory record not found")
        return row

    def verify_and_repair_fixture(self) -> tuple[dict[str, Any], dict[str, Any]]:
        _, shipment = self.request("GET", f"/shipments/{SHIPMENT_ID}", role="OWNER", expected=(200,))
        self.check(
            "5",
            "exact failed-safe shipment identity",
            str(shipment.get("id")) == SHIPMENT_ID
            and str(shipment.get("order_id")) == ORDER_ID
            and str(shipment.get("customer_id")) == CUSTOMER_ID,
        )
        self.check(
            "5",
            "failed-safe shipment has no provider result",
            shipment.get("nova_poshta_create_state") == "FAILED_SAFE"
            and not shipment.get("tracking_number")
            and not shipment.get("nova_poshta_document_ref")
            and not shipment.get("nova_poshta_document_number"),
            {
                "operation_state": shipment.get("nova_poshta_create_state"),
                "last_error_code": shipment.get("nova_poshta_last_error_code"),
            },
        )

        _, order = self.request("GET", f"/orders/{ORDER_ID}", role="OWNER", expected=(200,))
        self.check(
            "5",
            "exact synthetic order identity",
            str(order.get("notes") or "").startswith(PREFIX)
            and order.get("status") == "NEW"
            and str(order.get("customer_id")) == CUSTOMER_ID,
            {"status": order.get("status"), "prefix_match": str(order.get("notes") or "").startswith(PREFIX)},
        )
        inventory = self.inventory_for_variant()
        self.check(
            "5",
            "recovery fixture reservation is intact",
            self.inventory_state(inventory) == {"stock": 5, "reserved": 1, "available": 4},
            self.inventory_state(inventory),
        )

        city_description, warehouse_description = self.resolve_recipient_labels()
        _, repaired = self.request(
            "PUT",
            f"/shipments/{SHIPMENT_ID}",
            role="MANAGER",
            expected=(200,),
            payload={
                "city": city_description,
                "warehouse": warehouse_description,
                "nova_poshta_city_ref": os.environ["STAGING_NOVA_POSHTA_SENDER_CITY_REF"],
                "nova_poshta_warehouse_ref": os.environ["STAGING_NOVA_POSHTA_SENDER_WAREHOUSE_REF"],
            },
        )
        self.check(
            "5",
            "recipient labels repaired without provider result",
            bool(repaired.get("city"))
            and bool(repaired.get("warehouse"))
            and not repaired.get("tracking_number")
            and not repaired.get("nova_poshta_document_ref"),
            {
                "city_present": bool(repaired.get("city")),
                "warehouse_present": bool(repaired.get("warehouse")),
                "operation_state": repaired.get("nova_poshta_create_state"),
            },
        )
        return order, inventory

    async def concurrent_create(self) -> list[tuple[int, dict[str, Any]]]:
        url = API + f"/shipments/{SHIPMENT_ID}/nova-poshta/create-ttn"
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
        results = asyncio.run(self.concurrent_create())
        self.check("6", "two recovery create requests returned HTTP 200", all(code == 200 for code, _ in results), {
            "statuses": [code for code, _ in results],
        })
        self.check("6", "two recovery responses report success", all(body.get("success") is True for _, body in results), {
            "success_flags": [body.get("success") for _, body in results],
            "operation_states": [body.get("operation_state") for _, body in results],
            "errors": [body.get("errors") for _, body in results],
        })
        tracking_values = {
            str(body.get("tracking_number"))
            for _, body in results
            if body.get("success") is True and body.get("tracking_number")
        }
        document_values = {
            str(body.get("document_ref"))
            for _, body in results
            if body.get("success") is True and body.get("document_ref")
        }
        self.check("6", "concurrent recovery resolves to one TTN", len(tracking_values) == 1, {
            "unique_tracking_count": len(tracking_values),
        })
        self.check("6", "concurrent recovery resolves to one provider ref", len(document_values) == 1, {
            "unique_document_ref_count": len(document_values),
        })
        tracking = next(iter(tracking_values))
        document_ref = next(iter(document_values))
        self.tracking_hash = hashlib.sha256(tracking.encode("utf-8")).hexdigest()[:16]
        self.tracking_suffix = tracking[-4:]

        _, shipment = self.request("GET", f"/shipments/{SHIPMENT_ID}", role="OWNER", expected=(200,))
        stored_tracking = str(shipment.get("tracking_number") or shipment.get("nova_poshta_document_number") or "")
        stored_ref = str(shipment.get("nova_poshta_document_ref") or "")
        self.check(
            "5",
            "Sellora stores the single provider result",
            stored_tracking == tracking and stored_ref == document_ref,
            {
                "tracking": self.redact_identifier(stored_tracking),
                "provider_ref": self.redact_identifier(stored_ref),
                "shipment_status": shipment.get("status"),
                "operation_state": shipment.get("nova_poshta_create_state"),
            },
        )

        _, repeated = self.request(
            "POST",
            f"/shipments/{SHIPMENT_ID}/nova-poshta/create-ttn",
            role="MANAGER",
            expected=(200,),
        )
        self.check(
            "6",
            "completed recovery returns existing result",
            repeated.get("success") is True
            and repeated.get("reused_existing_result") is True
            and str(repeated.get("tracking_number") or "") == tracking,
            {
                "reused_existing_result": repeated.get("reused_existing_result"),
                "operation_state": repeated.get("operation_state"),
                "tracking": self.redact_identifier(str(repeated.get("tracking_number") or "")),
            },
        )

        code, _ = self.request(
            "POST",
            f"/shipments/{SHIPMENT_ID}/nova-poshta/create-ttn",
            role="ANALYST",
            expected=(403,),
        )
        self.check("10", "ANALYST recovery create denied", code == 403)
        code, _ = self.request(
            "POST",
            f"/shipments/{SHIPMENT_ID}/nova-poshta/create-ttn",
            role="MANAGER",
            workspace=str(uuid4()),
            expected=(403,),
        )
        self.check("11", "foreign-workspace recovery create denied", code == 403)
        code, _ = self.request(
            "POST",
            f"/shipments/{SHIPMENT_ID}/cancel",
            role="MANAGER",
            expected=(409,),
        )
        self.check("13", "provider-backed local cancellation remains blocked", code == 409)

        _, order_after = self.request("GET", f"/orders/{ORDER_ID}", role="OWNER", expected=(200,))
        inventory_after = self.inventory_for_variant()
        order_core_before = {
            "status": order_before.get("status"),
            "payment_status": order_before.get("payment_status"),
            "revenue": order_before.get("revenue"),
            "items": [(str(item.get("product_variant_id")), int(item.get("quantity", 0))) for item in order_before.get("items", [])],
        }
        order_core_after = {
            "status": order_after.get("status"),
            "payment_status": order_after.get("payment_status"),
            "revenue": order_after.get("revenue"),
            "items": [(str(item.get("product_variant_id")), int(item.get("quantity", 0))) for item in order_after.get("items", [])],
        }
        self.check("5", "TTN recovery leaves order unchanged", order_core_after == order_core_before, order_core_after)
        self.check(
            "5",
            "TTN recovery leaves inventory unchanged",
            self.inventory_state(inventory_after) == self.inventory_state(inventory_before),
            self.inventory_state(inventory_after),
        )

        _, sync_one = self.request(
            "POST", f"/shipments/{SHIPMENT_ID}/nova-poshta/sync-status", role="MANAGER", expected=(200,)
        )
        _, sync_two = self.request(
            "POST", f"/shipments/{SHIPMENT_ID}/nova-poshta/sync-status", role="MANAGER", expected=(200,)
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
        _, order_after_sync = self.request("GET", f"/orders/{ORDER_ID}", role="OWNER", expected=(200,))
        inventory_after_sync = self.inventory_for_variant()
        sync_order_core = {
            "status": order_after_sync.get("status"),
            "payment_status": order_after_sync.get("payment_status"),
            "revenue": order_after_sync.get("revenue"),
            "items": [(str(item.get("product_variant_id")), int(item.get("quantity", 0))) for item in order_after_sync.get("items", [])],
        }
        self.check("8", "tracking sync leaves order/payment unchanged", sync_order_core == order_core_before, sync_order_core)
        self.check(
            "8",
            "tracking sync leaves stock/reservation unchanged",
            self.inventory_state(inventory_after_sync) == self.inventory_state(inventory_before),
            self.inventory_state(inventory_after_sync),
        )
        self.check("5", "recovery produced no HTTP 5xx", self.network["http_5xx"] == 0, self.network)

    def write_report(self) -> None:
        if self.safe_error is None and all(item["status"] == "PASS" for item in self.checks):
            self.decision = "PASS_PENDING_RESTART_AND_CLEANUP"
        report = {
            "sprint": "8E",
            "phase": "failed-safe-recovery",
            "decision": self.decision,
            "prefix": PREFIX,
            "runtime": self.runtime,
            "checks": self.checks,
            "target": {
                "shipment_id": SHIPMENT_ID,
                "order_id": ORDER_ID,
                "customer_id": CUSTOMER_ID,
                "product_id": PRODUCT_ID,
                "variant_id": VARIANT_ID,
            },
            "tracking_evidence": {
                "sha256_prefix": self.tracking_hash,
                "suffix": self.tracking_suffix,
            } if self.tracking_hash else None,
            "network": self.network,
            "provider_document_expected": 1 if self.tracking_hash else 0,
            "restart_required": bool(self.tracking_hash),
            "cleanup_required": bool(self.tracking_hash),
            "safe_error": self.safe_error,
            "generated_at": datetime.now(UTC).isoformat(),
        }
        encoded = json.dumps(report, ensure_ascii=False, indent=2)
        for env_name in (
            "STAGING_OWNER_EMAIL", "STAGING_OWNER_PASSWORD",
            "STAGING_MANAGER_EMAIL", "STAGING_MANAGER_PASSWORD",
            "STAGING_ANALYST_EMAIL", "STAGING_ANALYST_PASSWORD",
            "STAGING_NOVA_POSHTA_API_KEY", "STAGING_NOVA_POSHTA_SENDER_PHONE",
        ):
            secret = os.environ.get(env_name)
            if secret and secret in encoded:
                report["decision"] = "FAIL"
                report["safe_error"] = f"SANITIZATION_FAILED_{env_name}"
                encoded = json.dumps(report, ensure_ascii=False, indent=2)
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(encoded, encoding="utf-8")
        print(json.dumps({
            "decision": report["decision"],
            "checks": len(report["checks"]),
            "provider_document_expected": report["provider_document_expected"],
            "artifact": str(OUT),
        }), flush=True)

    def run(self) -> int:
        try:
            self.environment()
            order, inventory = self.verify_and_repair_fixture()
            self.provider_flow(order, inventory)
        except Exception as exc:
            self.safe_error = str(self.safe(exc))
            print(f"SAFE_ERROR: {self.safe_error}", flush=True)
        finally:
            self.write_report()
        return 0 if self.decision == "PASS_PENDING_RESTART_AND_CLEANUP" else 1


if __name__ == "__main__":
    sys.exit(Recovery().run())
