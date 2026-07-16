#!/usr/bin/env python3
"""Final Sprint 8E real-provider proof through the Sellora production API.

No fixture or integration setting is created. The runner targets one exact
synthetic shipment whose sender and recipient configuration were already
validated. It issues two concurrent create requests, allows durable
reconciliation to settle the race, and preserves the single provider result for
the mandatory process restart boundary.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import os
import re
import sys
import time
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
OUT = Path("artifacts/sprint-8e/backend-provider-retry.json")
TIMEOUT = httpx.Timeout(connect=30, read=120, write=120, pool=30)

SHIPMENT_ID = "15e3f667-e4f1-4d69-be43-91aaaf9fd517"
ORDER_ID = "cdd31ee4-5a6f-4a4b-8869-607795572984"
CUSTOMER_ID = "9d492272-0341-4186-890b-7bb7228274ae"
VARIANT_ID = "3e40960c-6eaa-41ad-8cd1-6f3ace0796ec"
PREFIX = "QA8E-20260716103246"
AMBIGUOUS_SHIPMENT_ID = "a6950499-5311-419a-aaee-2c223de3fc92"
EXPECTED_COUNTERPARTY_HASH = "25aa4b435a1e2a3c"
EXPECTED_CONTACT_HASH = "7aa33fcd4a79e783"


def digest(value: Any) -> str | None:
    text = str(value or "").strip()
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16] if text else None


class Proof:
    def __init__(self) -> None:
        self.sessions: dict[str, str] = {}
        self.runtime: dict[str, Any] = {}
        self.checks: list[dict[str, Any]] = []
        self.network = {
            "requests": 0,
            "create_ttn_requests": 0,
            "reconcile_requests": 0,
            "sync_requests": 0,
            "http_5xx": 0,
        }
        self.safe_error: str | None = None
        self.decision = "FAIL"
        self.tracking_hash: str | None = None
        self.tracking_suffix: str | None = None
        self.document_ref_hash: str | None = None

    @staticmethod
    def safe(value: Any) -> Any:
        blocked = {
            "access_token", "refresh_token", "authorization", "password", "phone",
            "recipient_phone", "sender_phone", "tracking_number", "document_ref",
            "nova_poshta_document_ref", "nova_poshta_document_number", "external_ref",
            "sender_counterparty_ref", "sender_contact_ref", "sender_warehouse_ref",
            "sender_city_ref", "nova_poshta_city_ref", "nova_poshta_warehouse_ref",
        }
        if isinstance(value, dict):
            return {
                str(key): Proof.safe(item)
                for key, item in value.items()
                if str(key).lower() not in blocked
            }
        if isinstance(value, list):
            return [Proof.safe(item) for item in value[:30]]
        text = str(value or "")
        for name in (
            "STAGING_OWNER_EMAIL", "STAGING_OWNER_PASSWORD",
            "STAGING_MANAGER_EMAIL", "STAGING_MANAGER_PASSWORD",
            "STAGING_ANALYST_EMAIL", "STAGING_ANALYST_PASSWORD",
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
        if "create-ttn" in path:
            self.network["create_ttn_requests"] += 1
        if "reconcile-ttn" in path:
            self.network["reconcile_requests"] += 1
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

    def preflight(self) -> tuple[dict[str, Any], dict[str, Any]]:
        _, health = self.request("GET", API_ROOT + "/health", expected=(200,))
        commit = str(health.get("runtime_commit") or "").lower()
        self.runtime = {
            "status": health.get("status"),
            "runtime_commit": commit,
            "process_started_at": health.get("process_started_at"),
        }
        self.check(
            "1", "exact production runtime",
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
        self.check(
            "5", "discovered sender tuple remains active",
            settings.get("status") == "CONNECTED"
            and settings.get("provider_writes_enabled") is True
            and settings.get("sender_configured") is True
            and digest(settings.get("sender_counterparty_ref")) == EXPECTED_COUNTERPARTY_HASH
            and digest(settings.get("sender_contact_ref")) == EXPECTED_CONTACT_HASH,
            {
                "status": settings.get("status"),
                "provider_writes_enabled": settings.get("provider_writes_enabled"),
                "sender_configured": settings.get("sender_configured"),
                "counterparty_ref_sha256_prefix": digest(settings.get("sender_counterparty_ref")),
                "contact_ref_sha256_prefix": digest(settings.get("sender_contact_ref")),
            },
        )
        code, _ = self.request(
            "GET", f"/shipments/{AMBIGUOUS_SHIPMENT_ID}", role="OWNER", expected=(404,)
        )
        self.check("5", "ambiguous fixture remains archived", code == 404)

        _, shipment = self.request("GET", f"/shipments/{SHIPMENT_ID}", role="OWNER", expected=(200,))
        self.check(
            "5", "exact primary fixture identity",
            str(shipment.get("id")) == SHIPMENT_ID
            and str(shipment.get("order_id")) == ORDER_ID
            and str(shipment.get("customer_id")) == CUSTOMER_ID,
        )
        self.check(
            "5", "primary has no provider result before final call",
            not shipment.get("tracking_number")
            and not shipment.get("nova_poshta_document_ref")
            and not shipment.get("nova_poshta_document_number"),
            {
                "operation_state": shipment.get("nova_poshta_create_state"),
                "last_error_code": shipment.get("nova_poshta_last_error_code"),
                "recipient_name_present": bool(shipment.get("recipient_name")),
                "recipient_phone_present": bool(shipment.get("recipient_phone")),
                "city_present": bool(shipment.get("city")),
                "warehouse_present": bool(shipment.get("warehouse")),
                "recipient_city_ref_present": bool(shipment.get("nova_poshta_city_ref")),
                "recipient_warehouse_ref_present": bool(shipment.get("nova_poshta_warehouse_ref")),
            },
        )
        self.check(
            "5", "primary recipient fields are complete",
            all(
                bool(shipment.get(field))
                for field in (
                    "recipient_name",
                    "recipient_phone",
                    "city",
                    "warehouse",
                    "nova_poshta_city_ref",
                    "nova_poshta_warehouse_ref",
                )
            ),
        )
        _, order = self.request("GET", f"/orders/{ORDER_ID}", role="OWNER", expected=(200,))
        self.check(
            "5", "primary order and prefix intact",
            order.get("status") == "NEW"
            and str(order.get("notes") or "").startswith(PREFIX),
            {"status": order.get("status")},
        )
        _, rows = self.request("GET", "/inventory", role="OWNER", expected=(200,))
        inventory = next(
            (item for item in rows if str(item.get("product_variant_id")) == VARIANT_ID),
            None,
        )
        state = self.inventory_state(inventory or {})
        self.check(
            "5", "primary reservation intact",
            inventory is not None and state == {"stock": 5, "reserved": 1, "available": 4},
            state,
        )
        return order, inventory or {}

    @staticmethod
    def inventory_state(row: dict[str, Any]) -> dict[str, int]:
        stock = int(row.get("stock_quantity", 0))
        reserved = int(row.get("reserved_quantity", 0))
        return {"stock": stock, "reserved": reserved, "available": stock - reserved}

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
            return response.status_code, body

        return list(await asyncio.gather(call(), call()))

    def settle_provider_result(self) -> tuple[str, str, list[tuple[int, dict[str, Any]]]]:
        results = asyncio.run(self.concurrent_create())
        self.check(
            "6", "two concurrent production create requests completed without HTTP 5xx",
            all(code == 200 for code, _ in results),
            {
                "statuses": [code for code, _ in results],
                "responses": [
                    {
                        "success": body.get("success"),
                        "operation_state": body.get("operation_state"),
                        "reused_existing_result": body.get("reused_existing_result"),
                        "reconciliation_attempted": body.get("reconciliation_attempted"),
                        "manual_reconciliation_required": body.get("manual_reconciliation_required"),
                        "errors": body.get("errors"),
                    }
                    for _, body in results
                ],
            },
        )

        shipment = None
        for attempt in range(1, 8):
            _, shipment = self.request(
                "GET", f"/shipments/{SHIPMENT_ID}", role="OWNER", expected=(200,)
            )
            tracking = str(
                shipment.get("tracking_number")
                or shipment.get("nova_poshta_document_number")
                or ""
            )
            document_ref = str(shipment.get("nova_poshta_document_ref") or "")
            if tracking and document_ref:
                break
            _, reconciliation = self.request(
                "POST", f"/shipments/{SHIPMENT_ID}/nova-poshta/reconcile-ttn",
                role="MANAGER", expected=(200,),
            )
            print(json.dumps({
                "reconcile_attempt": attempt,
                "success": reconciliation.get("success"),
                "operation_state": reconciliation.get("operation_state"),
                "manual_reconciliation_required": reconciliation.get("manual_reconciliation_required"),
                "errors": self.safe(reconciliation.get("errors")),
            }), flush=True)
            time.sleep(5)
        tracking = str(
            shipment.get("tracking_number")
            or shipment.get("nova_poshta_document_number")
            or ""
        )
        document_ref = str(shipment.get("nova_poshta_document_ref") or "")
        self.check(
            "6", "durable operation settled to one stored provider result",
            bool(tracking) and bool(document_ref),
            {
                "tracking": self.identifier_evidence(tracking),
                "document_ref": self.identifier_evidence(document_ref),
                "operation_state": shipment.get("nova_poshta_create_state"),
                "last_error_code": shipment.get("nova_poshta_last_error_code"),
            },
        )
        self.tracking_hash = digest(tracking)
        self.tracking_suffix = tracking[-4:]
        self.document_ref_hash = digest(document_ref)
        return tracking, document_ref, results

    def post_create_checks(
        self,
        tracking: str,
        document_ref: str,
        initial_results: list[tuple[int, dict[str, Any]]],
        order_before: dict[str, Any],
        inventory_before: dict[str, Any],
    ) -> None:
        response_trackings = {
            str(body.get("tracking_number"))
            for _, body in initial_results
            if body.get("tracking_number")
        }
        response_refs = {
            str(body.get("document_ref"))
            for _, body in initial_results
            if body.get("document_ref")
        }
        self.check(
            "6", "concurrent responses do not expose conflicting provider results",
            len(response_trackings) <= 1
            and len(response_refs) <= 1
            and (not response_trackings or response_trackings == {tracking})
            and (not response_refs or response_refs == {document_ref}),
            {
                "unique_tracking_count": len(response_trackings),
                "unique_document_ref_count": len(response_refs),
            },
        )
        _, repeated = self.request(
            "POST", f"/shipments/{SHIPMENT_ID}/nova-poshta/create-ttn",
            role="MANAGER", expected=(200,),
        )
        self.check(
            "6", "completed operation returns existing result",
            repeated.get("success") is True
            and repeated.get("reused_existing_result") is True
            and str(repeated.get("tracking_number") or "") == tracking
            and str(repeated.get("document_ref") or "") == document_ref,
            {
                "success": repeated.get("success"),
                "reused_existing_result": repeated.get("reused_existing_result"),
                "operation_state": repeated.get("operation_state"),
                "tracking": self.identifier_evidence(str(repeated.get("tracking_number") or "")),
            },
        )
        code, _ = self.request(
            "POST", f"/shipments/{SHIPMENT_ID}/nova-poshta/create-ttn",
            role="ANALYST", expected=(403,),
        )
        self.check("10", "ANALYST TTN create denied", code == 403)
        code, _ = self.request(
            "POST", f"/shipments/{SHIPMENT_ID}/nova-poshta/create-ttn",
            role="MANAGER", workspace=str(uuid4()), expected=(403,),
        )
        self.check("11", "foreign workspace TTN create denied", code == 403)
        code, _ = self.request(
            "POST", f"/shipments/{SHIPMENT_ID}/cancel",
            role="MANAGER", expected=(409,),
        )
        self.check("13", "provider-backed local cancellation blocked", code == 409)

        _, order_after = self.request(
            "GET", f"/orders/{ORDER_ID}", role="OWNER", expected=(200,)
        )
        _, rows = self.request("GET", "/inventory", role="OWNER", expected=(200,))
        inventory_after = next(
            (item for item in rows if str(item.get("product_variant_id")) == VARIANT_ID),
            None,
        )
        before_core = {
            "status": order_before.get("status"),
            "payment_status": order_before.get("payment_status"),
            "revenue": order_before.get("revenue"),
            "items": [
                (str(item.get("product_variant_id")), int(item.get("quantity", 0)))
                for item in order_before.get("items", [])
            ],
        }
        after_core = {
            "status": order_after.get("status"),
            "payment_status": order_after.get("payment_status"),
            "revenue": order_after.get("revenue"),
            "items": [
                (str(item.get("product_variant_id")), int(item.get("quantity", 0)))
                for item in order_after.get("items", [])
            ],
        }
        self.check("5", "TTN create leaves order unchanged", after_core == before_core, after_core)
        self.check(
            "5", "TTN create leaves stock/reservation unchanged",
            inventory_after is not None
            and self.inventory_state(inventory_after) == self.inventory_state(inventory_before),
            self.inventory_state(inventory_after or {}),
        )

        _, sync_one = self.request(
            "POST", f"/shipments/{SHIPMENT_ID}/nova-poshta/sync-status",
            role="MANAGER", expected=(200,),
        )
        _, sync_two = self.request(
            "POST", f"/shipments/{SHIPMENT_ID}/nova-poshta/sync-status",
            role="MANAGER", expected=(200,),
        )
        self.check(
            "8", "tracking sync receives provider status",
            sync_one.get("success") is True and bool(sync_one.get("raw_status")),
            {
                "success": sync_one.get("success"),
                "normalized_status": sync_one.get("normalized_status"),
                "manual_review_required": sync_one.get("manual_review_required"),
                "synced_at_present": bool(sync_one.get("synced_at")),
            },
        )
        self.check(
            "8", "repeated tracking sync remains safe",
            sync_two.get("success") is True,
            {
                "normalized_status": sync_two.get("normalized_status"),
                "manual_review_required": sync_two.get("manual_review_required"),
            },
        )
        self.check("5", "provider proof produced no HTTP 5xx", self.network["http_5xx"] == 0, self.network)

    def write_report(self) -> None:
        if self.safe_error is None and all(item["status"] == "PASS" for item in self.checks):
            self.decision = "PASS_PENDING_RESTART_AND_CLEANUP"
        report = {
            "sprint": "8E",
            "phase": "production-backend-provider-retry",
            "decision": self.decision,
            "runtime": self.runtime,
            "checks": self.checks,
            "tracking_evidence": {
                "sha256_prefix": self.tracking_hash,
                "suffix": self.tracking_suffix,
            } if self.tracking_hash else None,
            "document_ref_sha256_prefix": self.document_ref_hash,
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
        }), flush=True)

    def run(self) -> int:
        try:
            order, inventory = self.preflight()
            tracking, document_ref, results = self.settle_provider_result()
            self.post_create_checks(
                tracking,
                document_ref,
                results,
                order,
                inventory,
            )
        except Exception as exc:
            self.safe_error = str(self.safe(exc))
        finally:
            self.write_report()
        return 0 if self.decision == "PASS_PENDING_RESTART_AND_CLEANUP" else 1


if __name__ == "__main__":
    sys.exit(Proof().run())
