#!/usr/bin/env python3
"""Delete the single Sprint 8E provider document, then archive local fixtures.

Safety order:
1. Confirm exact post-restart runtime and exact stored provider-result hashes.
2. Resolve exactly one provider document by the durable marker.
3. Perform at most one InternetDocument.delete request.
4. Confirm the marker is absent from the provider document list.
5. Archive only the exact synthetic shipment/order/catalog/customer via Sellora APIs.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import httpx

API_ROOT = os.environ["STAGING_API_URL"].rstrip("/")
API = API_ROOT + "/api/v1"
EXPECTED_RUNTIME_COMMIT = os.environ["EXPECTED_RUNTIME_COMMIT"].lower()
WORKSPACE_ID = os.environ["QA8E_WORKSPACE_ID"]
NP_API_URL = os.environ.get("NOVA_POSHTA_API_URL", "https://api.novaposhta.ua/v2.0/json/")
OUT = Path("artifacts/sprint-8e/provider-local-cleanup.json")
TIMEOUT = httpx.Timeout(connect=30, read=120, write=120, pool=30)

SHIPMENT_ID = "15e3f667-e4f1-4d69-be43-91aaaf9fd517"
ORDER_ID = "cdd31ee4-5a6f-4a4b-8869-607795572984"
CUSTOMER_ID = "9d492272-0341-4186-890b-7bb7228274ae"
PRODUCT_ID = "bf2e9c1c-2ece-4536-926f-83db215f475e"
VARIANT_ID = "3e40960c-6eaa-41ad-8cd1-6f3ace0796ec"
PREFIX = "QA8E-20260716103246"
PROVIDER_MARKER = "SELLORA:220ca354-f68b-4f82-a9ce-04001c87435a"
TRACKING_HASH = "44cf65a42ffe3682"
DOCUMENT_REF_HASH = "1de58913b2bb2bda"


def digest(value: Any) -> str | None:
    text = str(value or "").strip()
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16] if text else None


class Cleanup:
    def __init__(self) -> None:
        self.sessions: dict[str, str] = {}
        self.runtime: dict[str, Any] = {}
        self.checks: list[dict[str, Any]] = []
        self.network = {
            "requests": 0,
            "provider_list_requests": 0,
            "provider_delete_requests": 0,
            "local_delete_requests": 0,
            "http_5xx": 0,
        }
        self.safe_error: str | None = None
        self.decision = "FAIL"
        self.provider_delete_errors: list[str] = []

    @staticmethod
    def safe(value: Any) -> Any:
        blocked = {
            "access_token", "refresh_token", "authorization", "password", "api_key", "apikey",
            "phone", "recipient_phone", "sender_phone", "tracking_number", "document_ref",
            "nova_poshta_document_ref", "nova_poshta_document_number", "external_ref", "ref",
        }
        if isinstance(value, dict):
            return {
                str(key): Cleanup.safe(item)
                for key, item in value.items()
                if str(key).lower() not in blocked
            }
        if isinstance(value, list):
            return [Cleanup.safe(item) for item in value[:30]]
        text = str(value or "")
        for name in (
            "STAGING_OWNER_EMAIL", "STAGING_OWNER_PASSWORD",
            "STAGING_MANAGER_EMAIL", "STAGING_MANAGER_PASSWORD",
            "STAGING_NOVA_POSHTA_API_KEY",
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
    def evidence(value: str | None) -> dict[str, Any] | None:
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

    def headers(self, role: str) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.sessions[role]}",
            "X-Workspace-ID": WORKSPACE_ID,
            "Cache-Control": "no-cache",
        }

    def request(
        self,
        method: str,
        path: str,
        *,
        role: str | None = None,
        expected: tuple[int, ...] = (200,),
        payload: dict[str, Any] | None = None,
    ) -> tuple[int, Any]:
        url = path if path.startswith("http") else API + path
        headers = self.headers(role) if role else {"Cache-Control": "no-cache"}
        self.network["requests"] += 1
        if method == "DELETE":
            self.network["local_delete_requests"] += 1
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

    def provider_call(self, method: str, properties: dict[str, Any], *, delete: bool = False) -> dict[str, Any]:
        payload = {
            "apiKey": os.environ["STAGING_NOVA_POSHTA_API_KEY"],
            "modelName": "InternetDocument",
            "calledMethod": method,
            "methodProperties": properties,
        }
        with httpx.Client(timeout=TIMEOUT, follow_redirects=True, headers={"Connection": "close"}) as client:
            response = client.post(NP_API_URL, json=payload)
        self.network["requests"] += 1
        if delete:
            self.network["provider_delete_requests"] += 1
        else:
            self.network["provider_list_requests"] += 1
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
        self.check("6", f"{role} login succeeded for cleanup", bool(self.sessions[role]))

    def preflight(self) -> str:
        _, health = self.request("GET", API_ROOT + "/health", expected=(200,))
        commit = str(health.get("runtime_commit") or "").lower()
        self.runtime = {
            "status": health.get("status"),
            "runtime_commit": commit,
            "process_started_at": health.get("process_started_at"),
        }
        self.check(
            "6", "cleanup runs on exact post-restart runtime",
            health.get("status") == "ok" and commit.startswith(EXPECTED_RUNTIME_COMMIT[:12]),
            self.runtime,
        )
        self.login("OWNER", "STAGING_OWNER_EMAIL", "STAGING_OWNER_PASSWORD")
        self.login("MANAGER", "STAGING_MANAGER_EMAIL", "STAGING_MANAGER_PASSWORD")
        _, settings = self.request("GET", "/integrations/nova-poshta/settings", role="OWNER", expected=(200,))
        self.check(
            "6", "provider connection remains available for cleanup",
            settings.get("status") == "CONNECTED" and settings.get("provider_writes_enabled") is True,
            {
                "status": settings.get("status"),
                "provider_writes_enabled": settings.get("provider_writes_enabled"),
            },
        )
        _, shipment = self.request("GET", f"/shipments/{SHIPMENT_ID}", role="OWNER", expected=(200,))
        tracking = str(shipment.get("tracking_number") or shipment.get("nova_poshta_document_number") or "")
        document_ref = str(shipment.get("nova_poshta_document_ref") or "")
        self.check(
            "6", "exact provider-backed synthetic shipment selected",
            digest(tracking) == TRACKING_HASH
            and digest(document_ref) == DOCUMENT_REF_HASH
            and shipment.get("nova_poshta_create_state") == "COMPLETED"
            and shipment.get("deleted_at") is None,
            {
                "tracking": self.evidence(tracking),
                "document_ref_sha256_prefix": digest(document_ref),
                "operation_state": shipment.get("nova_poshta_create_state"),
                "shipment_status": shipment.get("status"),
            },
        )
        _, order = self.request("GET", f"/orders/{ORDER_ID}", role="OWNER", expected=(200,))
        self.check(
            "6", "exact synthetic order selected",
            order.get("status") == "NEW" and str(order.get("notes") or "").startswith(PREFIX),
            {"status": order.get("status")},
        )
        return document_ref

    @staticmethod
    def matching_documents(body: dict[str, Any]) -> list[dict[str, Any]]:
        matches = []
        for item in body.get("data", []):
            searchable = " ".join(
                str(item.get(key) or "")
                for key in (
                    "Description",
                    "AdditionalInformation",
                    "AdditionalInformationEW",
                    "InfoRegClientBarcodes",
                )
            )
            if PROVIDER_MARKER in searchable:
                matches.append(item)
        return matches

    def provider_cleanup(self, document_ref: str) -> None:
        date_from = (datetime.now(UTC) - timedelta(days=1)).strftime("%d.%m.%Y")
        date_to = (datetime.now(UTC) + timedelta(days=1)).strftime("%d.%m.%Y")
        list_properties = {
            "DateTimeFrom": date_from,
            "DateTimeTo": date_to,
            "GetFullList": "1",
        }
        before = self.provider_call("getDocumentList", list_properties)
        before_matches = self.matching_documents(before)
        self.check(
            "6", "durable marker resolves to exactly one provider document before delete",
            before.get("success") is True
            and len(before_matches) == 1
            and digest(before_matches[0].get("Ref")) == DOCUMENT_REF_HASH,
            {
                "matching_count": len(before_matches),
                "matched_ref_sha256_prefix": digest(before_matches[0].get("Ref")) if before_matches else None,
            },
        )
        self.check("6", "provider delete budget unused", self.network["provider_delete_requests"] == 0)
        deleted = self.provider_call("delete", {"DocumentRefs": document_ref}, delete=True)
        self.provider_delete_errors = [str(self.safe(item)) for item in deleted.get("errors", [])]
        self.check(
            "6", "Nova Poshta accepted exact document delete",
            deleted.get("success") is True,
            {
                "success": deleted.get("success"),
                "errors": deleted.get("errors", []),
                "warnings": deleted.get("warnings", []),
                "provider_delete_requests": self.network["provider_delete_requests"],
            },
        )
        after = self.provider_call("getDocumentList", list_properties)
        after_matches = self.matching_documents(after)
        self.check(
            "6", "durable marker absent from provider list after delete",
            after.get("success") is True and len(after_matches) == 0,
            {"matching_count": len(after_matches)},
        )
        self.check("6", "exactly one provider delete request occurred", self.network["provider_delete_requests"] == 1, self.network)

    def local_cleanup(self) -> None:
        self.request("DELETE", f"/shipments/{SHIPMENT_ID}", role="MANAGER", expected=(204,))
        self.request("DELETE", f"/orders/{ORDER_ID}", role="MANAGER", expected=(204,))
        self.request("DELETE", f"/products/variants/{VARIANT_ID}", role="MANAGER", expected=(204,))
        self.request("DELETE", f"/products/{PRODUCT_ID}", role="MANAGER", expected=(204,))
        self.request("DELETE", f"/customers/{CUSTOMER_ID}", role="MANAGER", expected=(204,))
        for label, path in (
            ("shipment", f"/shipments/{SHIPMENT_ID}"),
            ("order", f"/orders/{ORDER_ID}"),
            ("product", f"/products/{PRODUCT_ID}"),
            ("customer", f"/customers/{CUSTOMER_ID}"),
        ):
            code, _ = self.request("GET", path, role="OWNER", expected=(404,))
            self.check("6", f"synthetic {label} archived", code == 404)
        _, variants = self.request(
            "GET", f"/products/variants?product_id={PRODUCT_ID}", role="OWNER", expected=(200,)
        )
        self.check(
            "6", "synthetic variant archived",
            not any(str(item.get("id")) == VARIANT_ID for item in variants),
        )
        self.check("6", "provider/local cleanup produced no HTTP 5xx", self.network["http_5xx"] == 0, self.network)

    def write_report(self) -> None:
        if self.safe_error is None and all(item["status"] == "PASS" for item in self.checks):
            self.decision = "PASS_PENDING_PROVIDER_WRITES_DISABLE"
        report = {
            "sprint": "8E",
            "phase": "provider-and-local-cleanup",
            "decision": self.decision,
            "runtime": self.runtime,
            "checks": self.checks,
            "provider_delete_errors": self.provider_delete_errors,
            "network": self.network,
            "provider_document_deleted": self.decision == "PASS_PENDING_PROVIDER_WRITES_DISABLE",
            "local_fixtures_archived": self.decision == "PASS_PENDING_PROVIDER_WRITES_DISABLE",
            "provider_writes_disable_required": True,
            "safe_error": self.safe_error,
            "generated_at": datetime.now(UTC).isoformat(),
        }
        encoded = json.dumps(report, ensure_ascii=False, indent=2)
        for name in (
            "STAGING_OWNER_EMAIL", "STAGING_OWNER_PASSWORD",
            "STAGING_MANAGER_EMAIL", "STAGING_MANAGER_PASSWORD",
            "STAGING_NOVA_POSHTA_API_KEY",
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
            "provider_document_deleted": report["provider_document_deleted"],
            "local_fixtures_archived": report["local_fixtures_archived"],
            "network": report["network"],
            "artifact": str(OUT),
        }), flush=True)

    def run(self) -> int:
        try:
            document_ref = self.preflight()
            self.provider_cleanup(document_ref)
            self.local_cleanup()
        except Exception as exc:
            self.safe_error = str(self.safe(exc))
        finally:
            self.write_report()
        return 0 if self.decision == "PASS_PENDING_PROVIDER_WRITES_DISABLE" else 1


if __name__ == "__main__":
    sys.exit(Cleanup().run())
