#!/usr/bin/env python3
"""Recover the Sprint 8E sender configuration and prove one real TTN flow.

The runner discovers the sender counterparty/contact owned by the configured API
key, updates only the dedicated QA8E workspace settings, and performs at most one
Nova Poshta InternetDocument/save request. A successful provider result is
recovered through Sellora's production reconciliation endpoint and preserved for
the restart boundary.
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
OUT = Path("artifacts/sprint-8e/sender-recovery.json")
TIMEOUT = httpx.Timeout(connect=30, read=120, write=120, pool=30)

PRIMARY = {
    "prefix": "QA8E-20260716103246",
    "shipment_id": "15e3f667-e4f1-4d69-be43-91aaaf9fd517",
    "order_id": "cdd31ee4-5a6f-4a4b-8869-607795572984",
    "customer_id": "9d492272-0341-4186-890b-7bb7228274ae",
    "variant_id": "3e40960c-6eaa-41ad-8cd1-6f3ace0796ec",
    "provider_marker": "SELLORA:220ca354-f68b-4f82-a9ce-04001c87435a",
}
AMBIGUOUS_SHIPMENT_ID = "a6950499-5311-419a-aaee-2c223de3fc92"


def digest(value: Any) -> str | None:
    text = str(value or "").strip()
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16] if text else None


def normalize_phone(value: Any) -> str:
    digits = re.sub(r"\D", "", str(value or ""))
    if len(digits) == 10 and digits.startswith("0"):
        digits = "38" + digits
    return digits


class Recovery:
    def __init__(self) -> None:
        self.sessions: dict[str, str] = {}
        self.runtime: dict[str, Any] = {}
        self.checks: list[dict[str, Any]] = []
        self.network = {
            "requests": 0,
            "provider_read_requests": 0,
            "provider_save_requests": 0,
            "settings_writes": 0,
            "reconcile_requests": 0,
            "create_ttn_requests": 0,
            "sync_requests": 0,
            "http_5xx": 0,
        }
        self.safe_error: str | None = None
        self.decision = "FAIL"
        self.provider_errors: list[str] = []
        self.tracking_hash: str | None = None
        self.tracking_suffix: str | None = None
        self.document_ref_hash: str | None = None
        self.sender_evidence: dict[str, Any] = {}
        self.recipient_evidence: dict[str, Any] = {}

    @staticmethod
    def safe(value: Any) -> Any:
        blocked_keys = {
            "access_token", "refresh_token", "authorization", "password", "api_key", "apikey",
            "phone", "phones", "recipient_phone", "sender_phone", "tracking_number", "document_ref",
            "nova_poshta_document_ref", "nova_poshta_document_number", "external_ref", "ref",
            "sender_counterparty_ref", "sender_contact_ref", "sender_warehouse_ref", "sender_city_ref",
            "nova_poshta_city_ref", "nova_poshta_warehouse_ref",
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
        for name in (
            "STAGING_OWNER_EMAIL", "STAGING_OWNER_PASSWORD",
            "STAGING_MANAGER_EMAIL", "STAGING_MANAGER_PASSWORD",
            "STAGING_ANALYST_EMAIL", "STAGING_ANALYST_PASSWORD",
            "STAGING_NOVA_POSHTA_API_KEY", "STAGING_NOVA_POSHTA_SENDER_CITY_REF",
            "STAGING_NOVA_POSHTA_SENDER_WAREHOUSE_REF",
        ):
            secret = os.environ.get(name)
            if secret:
                text = text.replace(secret, f"[{name}]")
        text = re.sub(r"Bearer\s+\S+", "Bearer [REDACTED]", text, flags=re.I)
        text = re.sub(r"\beyJ[A-Za-z0-9._-]{20,}\b", "[TOKEN]", text)
        text = re.sub(r"\b[0-9a-fA-F]{8}-[0-9a-fA-F-]{24,}\b", "[VALUE]", text)
        text = re.sub(r"\b\d{7,}\b", "[VALUE]", text)
        return text[:500]

    @staticmethod
    def identifier_evidence(value: str | None) -> dict[str, Any] | None:
        if not value:
            return None
        return {
            "sha256_prefix": digest(value),
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
        if path == "/integrations/nova-poshta/settings" and method == "POST":
            self.network["settings_writes"] += 1
        if "reconcile-ttn" in path:
            self.network["reconcile_requests"] += 1
        if "create-ttn" in path:
            self.network["create_ttn_requests"] += 1
        if "sync-status" in path:
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
            self.network["provider_read_requests"] += 1
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
            "1", "diagnostic runtime identity",
            health.get("status") == "ok" and commit.startswith(EXPECTED_RUNTIME_COMMIT[:12]),
            self.runtime,
        )
        with httpx.Client(timeout=TIMEOUT, follow_redirects=True) as client:
            frontend = client.get(FRONTEND + "/login")
        self.check("1", "frontend staging reachable", frontend.status_code == 200, {"status": frontend.status_code})
        self.login("OWNER", "STAGING_OWNER_EMAIL", "STAGING_OWNER_PASSWORD")
        self.login("MANAGER", "STAGING_MANAGER_EMAIL", "STAGING_MANAGER_PASSWORD")
        self.login("ANALYST", "STAGING_ANALYST_EMAIL", "STAGING_ANALYST_PASSWORD")
        _, settings = self.request("GET", "/integrations/nova-poshta/settings", role="OWNER", expected=(200,))
        self.check("5", "Nova Poshta connected and writes enabled", settings.get("status") == "CONNECTED" and settings.get("provider_writes_enabled") is True, {
            "status": settings.get("status"),
            "provider_writes_enabled": settings.get("provider_writes_enabled"),
        })
        code, _ = self.request(
            "GET", f"/shipments/{AMBIGUOUS_SHIPMENT_ID}", role="OWNER", expected=(404,)
        )
        self.check("5", "ambiguous no-document fixture already archived", code == 404)

    def discover_sender(self) -> tuple[str, str, str, str, str]:
        counterparties_body = self.provider_call(
            "Counterparty", "getCounterparties", {"CounterpartyProperty": "Sender", "Page": "1"}
        )
        counterparties = [item for item in counterparties_body.get("data", []) if item.get("Ref")]
        self.check("5", "one or more provider sender counterparties discovered", counterparties_body.get("success") is True and bool(counterparties), {
            "counterparty_count": len(counterparties),
        })

        selected = None
        for counterparty in counterparties[:20]:
            counterparty_ref = str(counterparty.get("Ref"))
            contacts_body = self.provider_call(
                "Counterparty", "getCounterpartyContactPersons", {"Ref": counterparty_ref, "Page": "1"}
            )
            contacts = [item for item in contacts_body.get("data", []) if item.get("Ref")]
            contact = next(
                (
                    item
                    for item in contacts
                    if len(normalize_phone(item.get("Phones") or item.get("Phone"))) >= 10
                ),
                None,
            )
            if contact is not None:
                selected = (counterparty, contact)
                break
        self.check("5", "provider sender counterparty has usable contact", selected is not None)
        counterparty, contact = selected
        counterparty_ref = str(counterparty.get("Ref"))
        contact_ref = str(contact.get("Ref"))
        sender_phone = normalize_phone(contact.get("Phones") or contact.get("Phone"))
        self.check("5", "provider sender contact phone normalized", len(sender_phone) in (10, 12), {
            "phone_length": len(sender_phone),
        })

        sender_city_ref = os.environ["STAGING_NOVA_POSHTA_SENDER_CITY_REF"]
        sender_warehouse_ref = os.environ["STAGING_NOVA_POSHTA_SENDER_WAREHOUSE_REF"]
        city_body = self.provider_call("Address", "getCities", {"Ref": sender_city_ref, "Limit": "1"})
        city_rows = [item for item in city_body.get("data", []) if str(item.get("Ref")) == sender_city_ref]
        warehouse_body = self.provider_call(
            "Address", "getWarehouses", {"Ref": sender_warehouse_ref, "CityRef": sender_city_ref, "Limit": "1"}
        )
        warehouse_rows = [
            item for item in warehouse_body.get("data", []) if str(item.get("Ref")) == sender_warehouse_ref
        ]
        self.check("5", "configured sender city directory ref resolves", len(city_rows) == 1)
        self.check("5", "configured sender warehouse directory ref resolves", len(warehouse_rows) == 1)

        self.sender_evidence = {
            "counterparty_ref_sha256_prefix": digest(counterparty_ref),
            "contact_ref_sha256_prefix": digest(contact_ref),
            "phone_length": len(sender_phone),
            "city_ref_sha256_prefix": digest(sender_city_ref),
            "warehouse_ref_sha256_prefix": digest(sender_warehouse_ref),
            "counterparty_count": len(counterparties),
        }
        return counterparty_ref, contact_ref, sender_phone, sender_city_ref, sender_warehouse_ref

    def save_sender_settings(
        self,
        counterparty_ref: str,
        contact_ref: str,
        sender_phone: str,
        sender_city_ref: str,
        sender_warehouse_ref: str,
    ) -> None:
        _, saved = self.request(
            "POST", "/integrations/nova-poshta/settings", role="OWNER", expected=(200,),
            payload={
                "sender_city_ref": sender_city_ref,
                "sender_warehouse_ref": sender_warehouse_ref,
                "sender_counterparty_ref": counterparty_ref,
                "sender_contact_ref": contact_ref,
                "sender_phone": sender_phone,
            },
        )
        self.check("5", "Sellora persisted discovered sender tuple", saved.get("sender_counterparty_ref") == counterparty_ref and saved.get("sender_contact_ref") == contact_ref and saved.get("sender_phone") == sender_phone, {
            "status": saved.get("status"),
            "sender_configured": saved.get("sender_configured"),
            "counterparty_ref_sha256_prefix": digest(saved.get("sender_counterparty_ref")),
            "contact_ref_sha256_prefix": digest(saved.get("sender_contact_ref")),
            "phone_length": len(normalize_phone(saved.get("sender_phone"))),
        })
        _, tested = self.request(
            "POST", "/integrations/nova-poshta/test-connection", role="OWNER", expected=(200,)
        )
        self.check("5", "Nova Poshta connection remains valid after sender update", tested.get("success") is True, {
            "success": tested.get("success"), "status": tested.get("status"),
        })

    def resolve_recipient(self, sender_city_ref: str) -> tuple[str, str, str, str]:
        search_body = self.provider_call(
            "Address", "searchSettlements", {"CityName": "Київ", "Limit": "10"}
        )
        addresses = search_body.get("data", [{}])[0].get("Addresses", []) if search_body.get("data") else []
        recipient = next(
            (
                item
                for item in addresses
                if item.get("DeliveryCity") and str(item.get("DeliveryCity")) != sender_city_ref
            ),
            None,
        )
        self.check("5", "recipient city different from sender discovered", recipient is not None, {
            "candidate_count": len(addresses),
        })
        city_ref = str(recipient.get("DeliveryCity"))
        city_body = self.provider_call("Address", "getCities", {"Ref": city_ref, "Limit": "1"})
        cities = [item for item in city_body.get("data", []) if str(item.get("Ref")) == city_ref]
        self.check("5", "recipient city ref resolves", len(cities) == 1)
        city_name = str(cities[0].get("Description") or "").strip()

        warehouses_body = self.provider_call(
            "Address", "getWarehouses", {"CityRef": city_ref, "Limit": "100"}
        )
        warehouses = [
            item
            for item in warehouses_body.get("data", [])
            if item.get("Ref")
            and item.get("Number")
            and "поштомат" not in str(item.get("Description") or "").lower()
        ]
        self.check("5", "recipient warehouse discovered", bool(warehouses), {
            "warehouse_count": len(warehouses),
        })
        warehouse = warehouses[0]
        warehouse_ref = str(warehouse.get("Ref"))
        warehouse_number = str(warehouse.get("Number"))
        self.recipient_evidence = {
            "city_ref_sha256_prefix": digest(city_ref),
            "warehouse_ref_sha256_prefix": digest(warehouse_ref),
            "warehouse_number_length": len(warehouse_number),
            "different_city": city_ref != sender_city_ref,
        }
        return city_ref, city_name, warehouse_ref, warehouse_number

    @staticmethod
    def inventory_state(row: dict[str, Any]) -> dict[str, int]:
        stock = int(row.get("stock_quantity", 0))
        reserved = int(row.get("reserved_quantity", 0))
        return {"stock": stock, "reserved": reserved, "available": stock - reserved}

    def inventory_for_variant(self) -> dict[str, Any] | None:
        _, rows = self.request("GET", "/inventory", role="OWNER", expected=(200,))
        return next(
            (item for item in rows if str(item.get("product_variant_id")) == PRIMARY["variant_id"]),
            None,
        )

    def prepare_primary(
        self,
        recipient_city_ref: str,
        recipient_city_name: str,
        recipient_warehouse_ref: str,
        recipient_warehouse_number: str,
        recipient_phone: str,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        _, shipment = self.request("GET", f"/shipments/{PRIMARY['shipment_id']}", role="OWNER", expected=(200,))
        self.check("5", "exact primary fixture identity", str(shipment.get("id")) == PRIMARY["shipment_id"] and str(shipment.get("order_id")) == PRIMARY["order_id"] and str(shipment.get("customer_id")) == PRIMARY["customer_id"])
        self.check("5", "primary has no provider result before recovery", not shipment.get("tracking_number") and not shipment.get("nova_poshta_document_ref") and not shipment.get("nova_poshta_document_number"), {
            "operation_state": shipment.get("nova_poshta_create_state"),
            "last_error_code": shipment.get("nova_poshta_last_error_code"),
        })
        _, order = self.request("GET", f"/orders/{PRIMARY['order_id']}", role="OWNER", expected=(200,))
        self.check("5", "primary order and synthetic prefix intact", order.get("status") == "NEW" and str(order.get("notes") or "").startswith(PRIMARY["prefix"]), {
            "status": order.get("status"),
        })
        inventory = self.inventory_for_variant()
        self.check("5", "primary inventory reservation intact", inventory is not None and self.inventory_state(inventory) == {"stock": 5, "reserved": 1, "available": 4}, self.inventory_state(inventory or {}))
        _, repaired = self.request(
            "PUT", f"/shipments/{PRIMARY['shipment_id']}", role="MANAGER", expected=(200,),
            payload={
                "recipient_name": "Тестовий Клієнт Отримувач",
                "recipient_phone": recipient_phone,
                "city": recipient_city_name,
                "warehouse": recipient_warehouse_number,
                "nova_poshta_city_ref": recipient_city_ref,
                "nova_poshta_warehouse_ref": recipient_warehouse_ref,
            },
        )
        self.check("5", "primary recipient updated to valid different-city warehouse", repaired.get("warehouse") == recipient_warehouse_number and repaired.get("nova_poshta_city_ref") == recipient_city_ref and repaired.get("nova_poshta_warehouse_ref") == recipient_warehouse_ref, {
            "recipient_city_ref_sha256_prefix": digest(repaired.get("nova_poshta_city_ref")),
            "recipient_warehouse_ref_sha256_prefix": digest(repaired.get("nova_poshta_warehouse_ref")),
        })
        return order, inventory or {}

    def provider_save_once(
        self,
        counterparty_ref: str,
        contact_ref: str,
        sender_phone: str,
        sender_city_ref: str,
        sender_warehouse_ref: str,
        recipient_city_name: str,
        recipient_warehouse_number: str,
    ) -> tuple[str, str]:
        self.check("5", "provider save budget unused", self.network["provider_save_requests"] == 0)
        body = self.provider_call(
            "InternetDocument",
            "save",
            {
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
                "CitySender": sender_city_ref,
                "Sender": counterparty_ref,
                "SenderAddress": sender_warehouse_ref,
                "ContactSender": contact_ref,
                "SendersPhone": sender_phone,
                "NewAddress": "1",
                "RecipientType": "PrivatePerson",
                "RecipientName": "Тестовий Клієнт Отримувач",
                "RecipientCityName": recipient_city_name,
                "RecipientAddressName": recipient_warehouse_number,
                "RecipientPhone": sender_phone,
            },
            save=True,
        )
        errors = [str(self.safe(item)) for item in body.get("errors", [])]
        warnings = [str(self.safe(item)) for item in body.get("warnings", [])]
        self.provider_errors = errors
        self.check("5", "single provider save accepted", body.get("success") is True, {
            "success": body.get("success"),
            "errors": errors,
            "warnings": warnings,
            "provider_save_requests": self.network["provider_save_requests"],
        })
        rows = body.get("data", [])
        item = rows[0] if rows else {}
        tracking = str(item.get("IntDocNumber") or "")
        document_ref = str(item.get("Ref") or "")
        self.check("5", "provider returned one TTN and document ref", bool(tracking) and bool(document_ref) and len(rows) == 1, {
            "tracking": self.identifier_evidence(tracking),
            "document_ref": self.identifier_evidence(document_ref),
            "row_count": len(rows),
        })
        self.tracking_hash = digest(tracking)
        self.tracking_suffix = tracking[-4:]
        self.document_ref_hash = digest(document_ref)
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

    def reconcile_and_verify(self, tracking: str, document_ref: str, order_before: dict[str, Any], inventory_before: dict[str, Any]) -> None:
        _, reconciled = self.request(
            "POST", f"/shipments/{PRIMARY['shipment_id']}/nova-poshta/reconcile-ttn",
            role="MANAGER", expected=(200,),
        )
        self.check("6", "Sellora reconciliation recovered direct provider result", reconciled.get("success") is True and reconciled.get("reconciliation_attempted") is True, {
            "success": reconciled.get("success"),
            "operation_state": reconciled.get("operation_state"),
            "reused_existing_result": reconciled.get("reused_existing_result"),
            "reconciliation_attempted": reconciled.get("reconciliation_attempted"),
            "errors": reconciled.get("errors"),
        })
        _, shipment = self.request("GET", f"/shipments/{PRIMARY['shipment_id']}", role="OWNER", expected=(200,))
        stored_tracking = str(shipment.get("tracking_number") or shipment.get("nova_poshta_document_number") or "")
        stored_ref = str(shipment.get("nova_poshta_document_ref") or "")
        self.check("6", "Sellora persisted exact provider result", stored_tracking == tracking and stored_ref == document_ref, {
            "tracking": self.identifier_evidence(stored_tracking),
            "document_ref": self.identifier_evidence(stored_ref),
            "operation_state": shipment.get("nova_poshta_create_state"),
            "shipment_status": shipment.get("status"),
        })
        results = asyncio.run(self.concurrent_reuse())
        self.check("6", "concurrent post-reconcile create calls return safely", all(code == 200 for code, _ in results), {
            "statuses": [code for code, _ in results],
        })
        self.check("6", "concurrent calls reuse one durable result", all(body.get("success") is True and body.get("reused_existing_result") is True and str(body.get("tracking_number") or "") == tracking for _, body in results), {
            "responses": [
                {
                    "success": body.get("success"),
                    "reused_existing_result": body.get("reused_existing_result"),
                    "operation_state": body.get("operation_state"),
                    "tracking": self.identifier_evidence(str(body.get("tracking_number") or "")),
                }
                for _, body in results
            ],
        })
        self.check("6", "exactly one provider save request occurred", self.network["provider_save_requests"] == 1, self.network)
        code, _ = self.request("POST", f"/shipments/{PRIMARY['shipment_id']}/nova-poshta/create-ttn", role="ANALYST", expected=(403,))
        self.check("10", "ANALYST provider create denied", code == 403)
        code, _ = self.request("POST", f"/shipments/{PRIMARY['shipment_id']}/nova-poshta/create-ttn", role="MANAGER", workspace=str(uuid4()), expected=(403,))
        self.check("11", "foreign workspace provider create denied", code == 403)
        code, _ = self.request("POST", f"/shipments/{PRIMARY['shipment_id']}/cancel", role="MANAGER", expected=(409,))
        self.check("13", "provider-backed local cancellation blocked", code == 409)

        _, order_after = self.request("GET", f"/orders/{PRIMARY['order_id']}", role="OWNER", expected=(200,))
        inventory_after = self.inventory_for_variant()
        before_core = {
            "status": order_before.get("status"),
            "payment_status": order_before.get("payment_status"),
            "revenue": order_before.get("revenue"),
            "items": [(str(item.get("product_variant_id")), int(item.get("quantity", 0))) for item in order_before.get("items", [])],
        }
        after_core = {
            "status": order_after.get("status"),
            "payment_status": order_after.get("payment_status"),
            "revenue": order_after.get("revenue"),
            "items": [(str(item.get("product_variant_id")), int(item.get("quantity", 0))) for item in order_after.get("items", [])],
        }
        self.check("5", "provider reconciliation leaves order unchanged", after_core == before_core, after_core)
        self.check("5", "provider reconciliation leaves inventory unchanged", inventory_after is not None and self.inventory_state(inventory_after) == self.inventory_state(inventory_before), self.inventory_state(inventory_after or {}))

        _, sync_one = self.request("POST", f"/shipments/{PRIMARY['shipment_id']}/nova-poshta/sync-status", role="MANAGER", expected=(200,))
        _, sync_two = self.request("POST", f"/shipments/{PRIMARY['shipment_id']}/nova-poshta/sync-status", role="MANAGER", expected=(200,))
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
        self.check("5", "sender recovery flow produced no HTTP 5xx", self.network["http_5xx"] == 0, self.network)

    def write_report(self) -> None:
        if self.safe_error is None and all(item["status"] == "PASS" for item in self.checks):
            self.decision = "PASS_PENDING_RESTART_AND_CLEANUP"
        report = {
            "sprint": "8E",
            "phase": "sender-recovery-and-provider-reconciliation",
            "decision": self.decision,
            "runtime": self.runtime,
            "checks": self.checks,
            "sender_evidence": self.sender_evidence,
            "recipient_evidence": self.recipient_evidence,
            "tracking_evidence": {
                "sha256_prefix": self.tracking_hash,
                "suffix": self.tracking_suffix,
            } if self.tracking_hash else None,
            "document_ref_sha256_prefix": self.document_ref_hash,
            "provider_errors": self.provider_errors,
            "network": self.network,
            "provider_document_expected": 1 if self.tracking_hash else 0,
            "restart_required": bool(self.tracking_hash),
            "cleanup_required": bool(self.tracking_hash),
            "safe_error": self.safe_error,
            "generated_at": datetime.now(UTC).isoformat(),
        }
        encoded = json.dumps(report, ensure_ascii=False, indent=2)
        for name in (
            "STAGING_OWNER_EMAIL", "STAGING_OWNER_PASSWORD",
            "STAGING_MANAGER_EMAIL", "STAGING_MANAGER_PASSWORD",
            "STAGING_ANALYST_EMAIL", "STAGING_ANALYST_PASSWORD",
            "STAGING_NOVA_POSHTA_API_KEY", "STAGING_NOVA_POSHTA_SENDER_CITY_REF",
            "STAGING_NOVA_POSHTA_SENDER_WAREHOUSE_REF",
        ):
            secret = os.environ.get(name)
            if secret and secret in encoded:
                report["decision"] = "FAIL"
                report["safe_error"] = f"SANITIZATION_FAILED_{name}"
                encoded = json.dumps(report, ensure_ascii=False, indent=2)
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(encoded, encoding="utf-8")
        print(json.dumps({
            "decision": report["decision"],
            "checks": len(report["checks"]),
            "provider_document_expected": report["provider_document_expected"],
            "network": report["network"],
            "artifact": str(OUT),
        }))

    def run(self) -> int:
        try:
            self.preflight()
            counterparty_ref, contact_ref, sender_phone, sender_city_ref, sender_warehouse_ref = self.discover_sender()
            self.save_sender_settings(counterparty_ref, contact_ref, sender_phone, sender_city_ref, sender_warehouse_ref)
            recipient_city_ref, recipient_city_name, recipient_warehouse_ref, recipient_warehouse_number = self.resolve_recipient(sender_city_ref)
            order, inventory = self.prepare_primary(recipient_city_ref, recipient_city_name, recipient_warehouse_ref, recipient_warehouse_number, sender_phone)
            tracking, document_ref = self.provider_save_once(counterparty_ref, contact_ref, sender_phone, sender_city_ref, sender_warehouse_ref, recipient_city_name, recipient_warehouse_number)
            self.reconcile_and_verify(tracking, document_ref, order, inventory)
        except Exception as exc:
            self.safe_error = str(self.safe(exc))
        finally:
            self.write_report()
        return 0 if self.decision == "PASS_PENDING_RESTART_AND_CLEANUP" else 1


if __name__ == "__main__":
    sys.exit(Recovery().run())
