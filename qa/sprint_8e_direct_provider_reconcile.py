#!/usr/bin/env python3
"""One-shot Sprint 8E provider-success/reconciliation proof.

This runner performs at most one Nova Poshta InternetDocument/save request. It
uses the durable marker of the existing FAILED_SAFE operation, then asks Sellora
to recover the provider result through the production reconciliation endpoint.
It creates no new Sellora fixtures and never prints credentials, phones, full
TTNs or provider refs.
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
EXPECTED_RUNTIME_COMMIT = os.environ["EXPECTED_RUNTIME_COMMIT"].lower()
WORKSPACE_ID = os.environ["QA8E_WORKSPACE_ID"]
NP_API_URL = os.environ.get("NOVA_POSHTA_API_URL", "https://api.novaposhta.ua/v2.0/json/")
OUT = Path("artifacts/sprint-8e/direct-provider-reconcile.json")
TIMEOUT = httpx.Timeout(connect=30, read=120, write=120, pool=30)

PRIMARY = {
    "prefix": "QA8E-20260716103246",
    "shipment_id": "15e3f667-e4f1-4d69-be43-91aaaf9fd517",
    "order_id": "cdd31ee4-5a6f-4a4b-8869-607795572984",
    "customer_id": "9d492272-0341-4186-890b-7bb7228274ae",
    "product_id": "bf2e9c1c-2ece-4536-926f-83db215f475e",
    "variant_id": "3e40960c-6eaa-41ad-8cd1-6f3ace0796ec",
    "provider_marker": "SELLORA:220ca354-f68b-4f82-a9ce-04001c87435a",
}
AMBIGUOUS = {
    "prefix": "QA8E-20260716103855",
    "shipment_id": "a6950499-5311-419a-aaee-2c223de3fc92",
    "order_id": "86eb8d8c-2fd4-4841-ab7e-6d65c136f728",
    "customer_id": "af67fa6c-aaa5-41c1-ada4-ca9a23d33a0f",
    "product_id": "3d31bdd1-936e-47cc-aab2-382893ecb093",
    "variant_id": "35f0d944-418a-444f-a39b-b00b1241a860",
}


class Proof:
    def __init__(self) -> None:
        self.sessions: dict[str, str] = {}
        self.runtime: dict[str, Any] = {}
        self.checks: list[dict[str, Any]] = []
        self.network = {
            "requests": 0,
            "provider_directory_requests": 0,
            "provider_save_requests": 0,
            "reconcile_requests": 0,
            "create_ttn_requests": 0,
            "sync_requests": 0,
            "http_5xx": 0,
        }
        self.safe_error: str | None = None
        self.decision = "FAIL"
        self.tracking_hash: str | None = None
        self.tracking_suffix: str | None = None
        self.provider_ref_hash: str | None = None
        self.provider_validation_errors: list[str] = []

    @staticmethod
    def safe(value: Any) -> Any:
        blocked_keys = {
            "access_token", "refresh_token", "authorization", "password", "api_key", "apikey",
            "phone", "recipient_phone", "sender_phone", "tracking_number", "document_ref",
            "nova_poshta_document_ref", "nova_poshta_document_number", "external_ref",
            "city_description", "warehouse_description",
        }
        if isinstance(value, dict):
            return {
                str(key): Proof.safe(item)
                for key, item in value.items()
                if str(key).lower() not in blocked_keys
            }
        if isinstance(value, list):
            return [Proof.safe(item) for item in value[:30]]
        text = str(value or "")
        for env_name in (
            "STAGING_OWNER_EMAIL", "STAGING_OWNER_PASSWORD",
            "STAGING_MANAGER_EMAIL", "STAGING_MANAGER_PASSWORD",
            "STAGING_ANALYST_EMAIL", "STAGING_ANALYST_PASSWORD",
            "STAGING_NOVA_POSHTA_API_KEY", "STAGING_NOVA_POSHTA_SENDER_PHONE",
            "STAGING_NOVA_POSHTA_SENDER_CITY_REF", "STAGING_NOVA_POSHTA_SENDER_WAREHOUSE_REF",
            "STAGING_NOVA_POSHTA_SENDER_COUNTERPARTY_REF", "STAGING_NOVA_POSHTA_SENDER_CONTACT_REF",
        ):
            secret = os.environ.get(env_name)
            if secret:
                text = text.replace(secret, f"[{env_name}]")
        text = re.sub(r"Bearer\s+\S+", "Bearer [REDACTED]", text, flags=re.I)
        text = re.sub(r"\beyJ[A-Za-z0-9._-]{20,}\b", "[TOKEN]", text)
        text = re.sub(r"\b[0-9a-fA-F]{8}-[0-9a-fA-F-]{27,}\b", "[VALUE]", text)
        text = re.sub(r"\b\d{7,}\b", "[VALUE]", text)
        return text[:500]

    @staticmethod
    def evidence(value: str | None) -> dict[str, Any] | None:
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
        if "reconcile-ttn" in url:
            self.network["reconcile_requests"] += 1
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

    def provider_call(self, model: str, method: str, properties: dict[str, Any], *, save: bool = False) -> dict[str, Any]:
        payload = {
            "apiKey": os.environ["STAGING_NOVA_POSHTA_API_KEY"],
            "modelName": model,
            "calledMethod": method,
            "methodProperties": properties,
        }
        with httpx.Client(timeout=TIMEOUT, follow_redirects=True, headers={"Connection": "close"}) as client:
            response = client.post(NP_API_URL, json=payload)
        self.network["requests"] += 1
        if save:
            self.network["provider_save_requests"] += 1
        else:
            self.network["provider_directory_requests"] += 1
        if response.status_code >= 500:
            self.network["http_5xx"] += 1
        response.raise_for_status()
        return response.json()

    def login(self, role: str, email_env: str, password_env: str) -> None:
        _, tokens = self.request(
            "POST", "/auth/login", expected=(200,),
            payload={"email": os.environ[email_env], "password": os.environ[password_env]},
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

    def preflight(self) -> None:
        _, health = self.request("GET", API_ROOT + "/health", expected=(200,))
        commit = str(health.get("runtime_commit") or "").lower()
        self.runtime = {
            "status": health.get("status"),
            "runtime_commit": commit,
            "process_started_at": health.get("process_started_at"),
        }
        self.check(
            "1", "durable reconciliation runtime identity",
            health.get("status") == "ok" and commit.startswith(EXPECTED_RUNTIME_COMMIT[:12]),
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
        self.check("5", "Nova Poshta connected and writes enabled", settings.get("status") == "CONNECTED" and settings.get("sender_configured") is True and settings.get("provider_writes_enabled") is True, {
            "status": settings.get("status"),
            "sender_configured": settings.get("sender_configured"),
            "provider_writes_enabled": settings.get("provider_writes_enabled"),
        })
        required = [
            "STAGING_NOVA_POSHTA_API_KEY",
            "STAGING_NOVA_POSHTA_SENDER_CITY_REF",
            "STAGING_NOVA_POSHTA_SENDER_WAREHOUSE_REF",
            "STAGING_NOVA_POSHTA_SENDER_COUNTERPARTY_REF",
            "STAGING_NOVA_POSHTA_SENDER_CONTACT_REF",
            "STAGING_NOVA_POSHTA_SENDER_PHONE",
        ]
        missing = [name for name in required if not os.environ.get(name)]
        self.check("5", "direct provider inputs present", not missing, {"missing_names": missing})

    @staticmethod
    def inventory_state(row: dict[str, Any]) -> dict[str, int]:
        stock = int(row.get("stock_quantity", 0))
        reserved = int(row.get("reserved_quantity", 0))
        return {"stock": stock, "reserved": reserved, "available": stock - reserved}

    def inventory_for_variant(self, variant_id: str) -> dict[str, Any] | None:
        _, rows = self.request("GET", "/inventory", role="OWNER", expected=(200,))
        return next((item for item in rows if str(item.get("product_variant_id")) == variant_id), None)

    def cleanup_ambiguous(self) -> None:
        code, shipment = self.request(
            "GET", f"/shipments/{AMBIGUOUS['shipment_id']}", role="OWNER", expected=(200, 404)
        )
        if code == 404:
            self.check("5", "ambiguous fixture already cleaned", True)
            return
        self.check(
            "5", "exact ambiguous fixture identity",
            str(shipment.get("id")) == AMBIGUOUS["shipment_id"]
            and str(shipment.get("order_id")) == AMBIGUOUS["order_id"]
            and str(shipment.get("customer_id")) == AMBIGUOUS["customer_id"],
        )
        _, order = self.request("GET", f"/orders/{AMBIGUOUS['order_id']}", role="OWNER", expected=(200,))
        self.check("5", "ambiguous fixture synthetic prefix", str(order.get("notes") or "").startswith(AMBIGUOUS["prefix"]))
        _, reconciled = self.request(
            "POST", f"/shipments/{AMBIGUOUS['shipment_id']}/nova-poshta/reconcile-ttn",
            role="MANAGER", expected=(200,),
        )
        _, verified = self.request(
            "GET", f"/shipments/{AMBIGUOUS['shipment_id']}", role="OWNER", expected=(200,)
        )
        has_result = bool(
            verified.get("tracking_number")
            or verified.get("nova_poshta_document_ref")
            or verified.get("nova_poshta_document_number")
        )
        self.check(
            "5", "ambiguous reconciliation confirms no provider document",
            reconciled.get("success") is not True and not has_result,
            {
                "success": reconciled.get("success"),
                "operation_state": reconciled.get("operation_state"),
                "errors": reconciled.get("errors"),
            },
        )
        self.request("DELETE", f"/shipments/{AMBIGUOUS['shipment_id']}", role="MANAGER", expected=(204,))
        self.request("DELETE", f"/orders/{AMBIGUOUS['order_id']}", role="MANAGER", expected=(204,))
        self.request("DELETE", f"/products/variants/{AMBIGUOUS['variant_id']}", role="MANAGER", expected=(204,))
        self.request("DELETE", f"/products/{AMBIGUOUS['product_id']}", role="MANAGER", expected=(204,))
        self.request("DELETE", f"/customers/{AMBIGUOUS['customer_id']}", role="MANAGER", expected=(204,))
        self.check("5", "ambiguous no-document fixture archived", True, {"provider_document_count": 0})

    def prepare_primary(self) -> tuple[dict[str, Any], dict[str, Any], str, str]:
        _, shipment = self.request("GET", f"/shipments/{PRIMARY['shipment_id']}", role="OWNER", expected=(200,))
        self.check(
            "5", "exact primary fixture identity",
            str(shipment.get("id")) == PRIMARY["shipment_id"]
            and str(shipment.get("order_id")) == PRIMARY["order_id"]
            and str(shipment.get("customer_id")) == PRIMARY["customer_id"],
        )
        self.check(
            "5", "primary fixture has no provider result before proof",
            not shipment.get("tracking_number")
            and not shipment.get("nova_poshta_document_ref")
            and not shipment.get("nova_poshta_document_number"),
            {
                "operation_state": shipment.get("nova_poshta_create_state"),
                "last_error_code": shipment.get("nova_poshta_last_error_code"),
            },
        )
        _, order = self.request("GET", f"/orders/{PRIMARY['order_id']}", role="OWNER", expected=(200,))
        self.check(
            "5", "primary order identity and state",
            str(order.get("notes") or "").startswith(PRIMARY["prefix"])
            and order.get("status") == "NEW",
            {"status": order.get("status"), "prefix_match": str(order.get("notes") or "").startswith(PRIMARY["prefix"])},
        )
        inventory = self.inventory_for_variant(PRIMARY["variant_id"])
        self.check(
            "5", "primary reservation intact",
            inventory is not None and self.inventory_state(inventory) == {"stock": 5, "reserved": 1, "available": 4},
            self.inventory_state(inventory or {}),
        )

        city_ref = os.environ["STAGING_NOVA_POSHTA_SENDER_CITY_REF"]
        warehouse_ref = os.environ["STAGING_NOVA_POSHTA_SENDER_WAREHOUSE_REF"]
        city_body = self.provider_call("Address", "getCities", {"Ref": city_ref, "Limit": "1"})
        city_rows = [item for item in city_body.get("data", []) if str(item.get("Ref")) == city_ref]
        self.check("5", "recipient city ref resolves", city_body.get("success") is True and len(city_rows) == 1, {
            "success": city_body.get("success"), "matching_count": len(city_rows),
        })
        city_name = str(city_rows[0].get("Description") or "").strip()
        self.check("5", "recipient city description present", bool(city_name), {"description_length": len(city_name)})

        warehouse_body = self.provider_call(
            "Address", "getWarehouses", {"Ref": warehouse_ref, "CityRef": city_ref, "Limit": "1"}
        )
        warehouse_rows = [item for item in warehouse_body.get("data", []) if str(item.get("Ref")) == warehouse_ref]
        self.check("5", "recipient warehouse ref resolves", warehouse_body.get("success") is True and len(warehouse_rows) == 1, {
            "success": warehouse_body.get("success"), "matching_count": len(warehouse_rows),
        })
        warehouse_number = str(warehouse_rows[0].get("Number") or "").strip()
        self.check("5", "recipient warehouse number present", bool(warehouse_number), {
            "number_present": bool(warehouse_number), "number_length": len(warehouse_number),
        })

        _, repaired = self.request(
            "PUT", f"/shipments/{PRIMARY['shipment_id']}", role="MANAGER", expected=(200,),
            payload={
                "recipient_name": "Тестовий Клієнт Отримувач",
                "city": city_name,
                "warehouse": warehouse_number,
                "nova_poshta_city_ref": city_ref,
                "nova_poshta_warehouse_ref": warehouse_ref,
            },
        )
        self.check("5", "primary recipient repaired with provider directory values", bool(repaired.get("city")) and repaired.get("warehouse") == warehouse_number, {
            "city_present": bool(repaired.get("city")),
            "warehouse_number_present": repaired.get("warehouse") == warehouse_number,
        })
        return order, inventory or {}, city_name, warehouse_number

    def save_provider_document_once(self, city_name: str, warehouse_number: str) -> tuple[str, str]:
        payload = {
            "PayerType": "Sender",
            "PaymentMethod": "Cash",
            "DateTime": datetime.now(UTC).strftime("%d.%m.%Y"),
            "CargoType": "Parcel",
            "VolumeGeneral": "0.001",
            "Weight": "0.5",
            "ServiceType": "WarehouseWarehouse",
            "SeatsAmount": "1",
            "Description": PRIMARY["provider_marker"],
            "Cost": "100.00",
            "CitySender": os.environ["STAGING_NOVA_POSHTA_SENDER_CITY_REF"],
            "Sender": os.environ["STAGING_NOVA_POSHTA_SENDER_COUNTERPARTY_REF"],
            "SenderAddress": os.environ["STAGING_NOVA_POSHTA_SENDER_WAREHOUSE_REF"],
            "ContactSender": os.environ["STAGING_NOVA_POSHTA_SENDER_CONTACT_REF"],
            "SendersPhone": os.environ["STAGING_NOVA_POSHTA_SENDER_PHONE"],
            "NewAddress": "1",
            "RecipientType": "PrivatePerson",
            "RecipientName": "Тестовий Клієнт Отримувач",
            "RecipientCityName": city_name,
            "RecipientAddressName": warehouse_number,
            "RecipientPhone": os.environ["STAGING_NOVA_POSHTA_SENDER_PHONE"],
        }
        self.check("5", "provider save budget unused before call", self.network["provider_save_requests"] == 0)
        body = self.provider_call("InternetDocument", "save", payload, save=True)
        errors = [str(item) for item in body.get("errors", [])]
        warnings = [str(item) for item in body.get("warnings", [])]
        self.provider_validation_errors = [str(self.safe(item)) for item in errors[:10]]
        self.check(
            "5", "single direct provider save accepted",
            body.get("success") is True,
            {
                "success": body.get("success"),
                "errors": errors,
                "warnings": warnings,
                "provider_save_requests": self.network["provider_save_requests"],
            },
        )
        data = body.get("data", [])
        item = data[0] if data else {}
        tracking = str(item.get("IntDocNumber") or "")
        document_ref = str(item.get("Ref") or "")
        self.check("5", "provider returned one TTN and document ref", bool(tracking) and bool(document_ref), {
            "tracking": self.evidence(tracking),
            "provider_ref": self.evidence(document_ref),
            "data_count": len(data),
        })
        self.tracking_hash = hashlib.sha256(tracking.encode("utf-8")).hexdigest()[:16]
        self.tracking_suffix = tracking[-4:]
        self.provider_ref_hash = hashlib.sha256(document_ref.encode("utf-8")).hexdigest()[:16]
        return tracking, document_ref

    async def concurrent_reuse(self) -> list[tuple[int, dict[str, Any]]]:
        url = API + f"/shipments/{PRIMARY['shipment_id']}/nova-poshta/create-ttn"
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
            return response.status_code, body

        return list(await asyncio.gather(call(), call()))

    def reconcile_and_prove(self, tracking: str, document_ref: str, order_before: dict[str, Any], inventory_before: dict[str, Any]) -> None:
        _, reconciled = self.request(
            "POST", f"/shipments/{PRIMARY['shipment_id']}/nova-poshta/reconcile-ttn",
            role="MANAGER", expected=(200,),
        )
        self.check("6", "Sellora reconciliation recovered provider result", reconciled.get("success") is True and reconciled.get("reconciliation_attempted") is True, {
            "success": reconciled.get("success"),
            "operation_state": reconciled.get("operation_state"),
            "reused_existing_result": reconciled.get("reused_existing_result"),
            "reconciliation_attempted": reconciled.get("reconciliation_attempted"),
            "errors": reconciled.get("errors"),
        })
        _, shipment = self.request("GET", f"/shipments/{PRIMARY['shipment_id']}", role="OWNER", expected=(200,))
        stored_tracking = str(shipment.get("tracking_number") or shipment.get("nova_poshta_document_number") or "")
        stored_ref = str(shipment.get("nova_poshta_document_ref") or "")
        self.check("6", "Sellora persisted the exact reconciled provider result", stored_tracking == tracking and stored_ref == document_ref, {
            "tracking": self.evidence(stored_tracking),
            "provider_ref": self.evidence(stored_ref),
            "shipment_status": shipment.get("status"),
            "operation_state": shipment.get("nova_poshta_create_state"),
        })

        results = asyncio.run(self.concurrent_reuse())
        self.check("6", "concurrent post-reconcile create calls return HTTP 200", all(code == 200 for code, _ in results), {
            "statuses": [code for code, _ in results],
        })
        self.check("6", "concurrent post-reconcile calls reuse one durable result", all(
            body.get("success") is True
            and body.get("reused_existing_result") is True
            and str(body.get("tracking_number") or "") == tracking
            for _, body in results
        ), {
            "responses": [
                {
                    "success": body.get("success"),
                    "reused_existing_result": body.get("reused_existing_result"),
                    "operation_state": body.get("operation_state"),
                    "tracking": self.evidence(str(body.get("tracking_number") or "")),
                }
                for _, body in results
            ],
        })
        self.check("6", "provider save count remains exactly one", self.network["provider_save_requests"] == 1, self.network)

        code, _ = self.request(
            "POST", f"/shipments/{PRIMARY['shipment_id']}/nova-poshta/create-ttn",
            role="ANALYST", expected=(403,),
        )
        self.check("10", "ANALYST create denied", code == 403)
        code, _ = self.request(
            "POST", f"/shipments/{PRIMARY['shipment_id']}/nova-poshta/create-ttn",
            role="MANAGER", workspace=str(uuid4()), expected=(403,),
        )
        self.check("11", "foreign workspace create denied", code == 403)
        code, _ = self.request(
            "POST", f"/shipments/{PRIMARY['shipment_id']}/cancel",
            role="MANAGER", expected=(409,),
        )
        self.check("13", "provider-backed local cancellation blocked", code == 409)

        _, order_after = self.request("GET", f"/orders/{PRIMARY['order_id']}", role="OWNER", expected=(200,))
        inventory_after = self.inventory_for_variant(PRIMARY["variant_id"])
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
        self.check("5", "reconciliation leaves order unchanged", order_core_after == order_core_before, order_core_after)
        self.check("5", "reconciliation leaves inventory unchanged", inventory_after is not None and self.inventory_state(inventory_after) == self.inventory_state(inventory_before), self.inventory_state(inventory_after or {}))

        _, sync_one = self.request(
            "POST", f"/shipments/{PRIMARY['shipment_id']}/nova-poshta/sync-status",
            role="MANAGER", expected=(200,),
        )
        _, sync_two = self.request(
            "POST", f"/shipments/{PRIMARY['shipment_id']}/nova-poshta/sync-status",
            role="MANAGER", expected=(200,),
        )
        self.check("8", "tracking sync receives provider status", sync_one.get("success") is True and bool(sync_one.get("raw_status")), {
            "success": sync_one.get("success"),
            "normalized_status": sync_one.get("normalized_status"),
            "manual_review_required": sync_one.get("manual_review_required"),
            "synced_at_present": bool(sync_one.get("synced_at")),
        })
        self.check("8", "repeated tracking sync remains safe", sync_two.get("success") is True, {
            "normalized_status": sync_two.get("normalized_status"),
            "manual_review_required": sync_two.get("manual_review_required"),
        })
        self.check("5", "proof produced no HTTP 5xx", self.network["http_5xx"] == 0, self.network)

    def write_report(self) -> None:
        if self.safe_error is None and all(item["status"] == "PASS" for item in self.checks):
            self.decision = "PASS_PENDING_RESTART_AND_CLEANUP"
        report = {
            "sprint": "8E",
            "phase": "direct-provider-reconciliation-proof",
            "decision": self.decision,
            "runtime": self.runtime,
            "checks": self.checks,
            "primary_target": {key: value for key, value in PRIMARY.items() if key != "provider_marker"},
            "ambiguous_target": AMBIGUOUS,
            "tracking_evidence": {
                "sha256_prefix": self.tracking_hash,
                "suffix": self.tracking_suffix,
            } if self.tracking_hash else None,
            "provider_ref_sha256_prefix": self.provider_ref_hash,
            "provider_validation_errors": self.provider_validation_errors,
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
            "STAGING_NOVA_POSHTA_SENDER_CITY_REF", "STAGING_NOVA_POSHTA_SENDER_WAREHOUSE_REF",
            "STAGING_NOVA_POSHTA_SENDER_COUNTERPARTY_REF", "STAGING_NOVA_POSHTA_SENDER_CONTACT_REF",
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
            "network": report["network"],
            "artifact": str(OUT),
        }), flush=True)

    def run(self) -> int:
        try:
            self.preflight()
            self.cleanup_ambiguous()
            order, inventory, city_name, warehouse_number = self.prepare_primary()
            tracking, document_ref = self.save_provider_document_once(city_name, warehouse_number)
            self.reconcile_and_prove(tracking, document_ref, order, inventory)
        except Exception as exc:
            self.safe_error = str(self.safe(exc))
            print(f"SAFE_ERROR: {self.safe_error}", flush=True)
        finally:
            self.write_report()
        return 0 if self.decision == "PASS_PENDING_RESTART_AND_CLEANUP" else 1


if __name__ == "__main__":
    sys.exit(Proof().run())
