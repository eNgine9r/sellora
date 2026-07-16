from __future__ import annotations

import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

API_ROOT = os.environ.get("STAGING_API_URL", "").rstrip("/") + "/api/v1"
WORKSPACE_ID = os.environ.get("QA8E_WORKSPACE_ID", "")
EXPECTED_RUNTIME_COMMIT = os.environ.get("EXPECTED_RUNTIME_COMMIT", "")
OUT = Path("artifacts/sprint-8e/orphan-cleanup.json")
TIMEOUT = httpx.Timeout(60.0, connect=60.0)

SHIPMENT_ID = "7fc2c169-5f3f-45a3-a527-5338775755d7"
ORDER_ID = "9b325619-22c8-48cc-8fa3-4431a9710611"
CUSTOMER_ID = "3a4587a0-5f1d-4437-a10d-c53e30d7c830"
PRODUCT_ID = "fe09ee85-b23a-477c-b94d-59a2ba0d3489"
VARIANT_ID = "26bce175-bb22-4a86-8e0a-8886ab3b36ef"
PREFIX = "QA8E-20260716071304"


def safe(value: Any) -> str:
    text = str(value or "")
    for secret_name in ("STAGING_OWNER_EMAIL", "STAGING_OWNER_PASSWORD"):
        secret = os.environ.get(secret_name)
        if secret:
            text = text.replace(secret, f"[{secret_name}]")
    return text[:500]


class Cleanup:
    def __init__(self) -> None:
        self.token = ""
        self.checks: list[dict[str, Any]] = []
        self.network = {"requests": 0, "writes": 0, "http_5xx": 0}
        self.runtime: dict[str, Any] = {}
        self.safe_error: str | None = None

    def check(self, name: str, ok: bool, detail: Any | None = None) -> None:
        item: dict[str, Any] = {"name": name, "status": "PASS" if ok else "FAIL"}
        if detail is not None:
            item["detail"] = detail
        self.checks.append(item)
        if not ok:
            raise RuntimeError(name)

    def request(
        self,
        method: str,
        path: str,
        *,
        expected: tuple[int, ...],
        auth: bool = True,
        payload: dict[str, Any] | None = None,
    ) -> tuple[int, dict[str, Any]]:
        headers = {"Content-Type": "application/json"}
        if auth:
            headers.update({
                "Authorization": f"Bearer {self.token}",
                "X-Workspace-ID": WORKSPACE_ID,
            })
        url = f"{API_ROOT}{path}"
        with httpx.Client(timeout=TIMEOUT, follow_redirects=True, headers={"Connection": "close"}) as client:
            response = client.request(method, url, headers=headers, json=payload)
        self.network["requests"] += 1
        if method in {"POST", "PUT", "PATCH", "DELETE"}:
            self.network["writes"] += 1
        if response.status_code >= 500:
            self.network["http_5xx"] += 1
        try:
            body = response.json() if response.content else {}
        except Exception:
            body = {"message": response.text[:200]}
        print(f"HTTP {method} {path} -> {response.status_code}", flush=True)
        if response.status_code not in expected:
            raise RuntimeError(f"Unexpected HTTP {response.status_code} for {method} {path}: {safe(body)}")
        return response.status_code, body

    def preflight(self) -> None:
        required = [
            "STAGING_API_URL",
            "QA8E_WORKSPACE_ID",
            "EXPECTED_RUNTIME_COMMIT",
            "STAGING_OWNER_EMAIL",
            "STAGING_OWNER_PASSWORD",
        ]
        missing = [name for name in required if not os.environ.get(name)]
        self.check("protected cleanup inputs present", not missing, {"missing_names": missing})

        with httpx.Client(timeout=TIMEOUT, follow_redirects=True) as client:
            response = client.get(os.environ["STAGING_API_URL"].rstrip("/") + "/health")
        self.network["requests"] += 1
        response.raise_for_status()
        self.runtime = response.json()
        self.check(
            "runtime identity matches cleanup target",
            self.runtime.get("status") == "ok" and self.runtime.get("runtime_commit") == EXPECTED_RUNTIME_COMMIT,
            self.runtime,
        )

        _, tokens = self.request(
            "POST",
            "/auth/login",
            expected=(200,),
            auth=False,
            payload={
                "email": os.environ["STAGING_OWNER_EMAIL"],
                "password": os.environ["STAGING_OWNER_PASSWORD"],
            },
        )
        self.token = str(tokens.get("access_token") or "")
        self.check("OWNER login succeeded", bool(self.token))

    def verify_exact_orphan(self) -> None:
        _, shipment = self.request("GET", f"/shipments/{SHIPMENT_ID}", expected=(200,))
        self.check("orphan shipment identity", shipment.get("id") == SHIPMENT_ID and shipment.get("order_id") == ORDER_ID)
        self.check("orphan shipment has no TTN", not shipment.get("tracking_number"))
        self.check(
            "orphan shipment has no provider document",
            not shipment.get("nova_poshta_document_ref") and not shipment.get("nova_poshta_document_number"),
        )
        self.check(
            "orphan shipment is failed-safe only",
            shipment.get("nova_poshta_create_state") == "FAILED_SAFE"
            and shipment.get("nova_poshta_manual_reconciliation_required") is True,
            {
                "state": shipment.get("nova_poshta_create_state"),
                "manual_reconciliation_required": shipment.get("nova_poshta_manual_reconciliation_required"),
                "last_error_code": shipment.get("nova_poshta_last_error_code"),
            },
        )

        _, order = self.request("GET", f"/orders/{ORDER_ID}", expected=(200,))
        self.check(
            "orphan order exact synthetic prefix",
            str(order.get("notes") or "").startswith(PREFIX) and order.get("status") == "NEW",
            {"status": order.get("status"), "prefix_match": str(order.get("notes") or "").startswith(PREFIX)},
        )

        _, customer = self.request("GET", f"/customers/{CUSTOMER_ID}", expected=(200,))
        self.check("orphan customer exact synthetic prefix", str(customer.get("name") or "").startswith(PREFIX))

        _, product = self.request("GET", f"/products/{PRODUCT_ID}", expected=(200,))
        self.check("orphan product exact synthetic prefix", str(product.get("name") or "").startswith(PREFIX))

        _, variants = self.request("GET", f"/products/variants?product_id={PRODUCT_ID}", expected=(200,))
        matching = [item for item in variants if item.get("id") == VARIANT_ID]
        self.check("orphan variant exact identity", len(matching) == 1 and str(matching[0].get("sku") or "").startswith(PREFIX))

    def cleanup(self) -> None:
        self.request("DELETE", f"/shipments/{SHIPMENT_ID}", expected=(204,))
        self.request("DELETE", f"/orders/{ORDER_ID}", expected=(204,))
        self.request("DELETE", f"/products/variants/{VARIANT_ID}", expected=(204,))
        self.request("DELETE", f"/products/{PRODUCT_ID}", expected=(204,))
        self.request("DELETE", f"/customers/{CUSTOMER_ID}", expected=(204,))

        for label, path in (
            ("shipment", f"/shipments/{SHIPMENT_ID}"),
            ("order", f"/orders/{ORDER_ID}"),
            ("product", f"/products/{PRODUCT_ID}"),
            ("customer", f"/customers/{CUSTOMER_ID}"),
        ):
            code, _ = self.request("GET", path, expected=(404,))
            self.check(f"{label} no longer active", code == 404)

        _, variants = self.request("GET", f"/products/variants?product_id={PRODUCT_ID}", expected=(200,))
        self.check("variant no longer active", not any(item.get("id") == VARIANT_ID for item in variants))
        self.check("cleanup produced no HTTP 5xx", self.network["http_5xx"] == 0, self.network)

    def write_report(self) -> None:
        decision = "PASS" if self.safe_error is None and all(c["status"] == "PASS" for c in self.checks) else "FAIL"
        report = {
            "sprint": "8E",
            "phase": "failed-safe-orphan-cleanup",
            "decision": decision,
            "runtime": self.runtime,
            "checks": self.checks,
            "network": self.network,
            "target": {
                "shipment_id": SHIPMENT_ID,
                "order_id": ORDER_ID,
                "customer_id": CUSTOMER_ID,
                "product_id": PRODUCT_ID,
                "variant_id": VARIANT_ID,
                "prefix": PREFIX,
                "provider_document_expected": 0,
            },
            "safe_error": self.safe_error,
            "generated_at": datetime.now(UTC).isoformat(),
        }
        encoded = json.dumps(report, ensure_ascii=False, indent=2)
        for secret_name in ("STAGING_OWNER_EMAIL", "STAGING_OWNER_PASSWORD"):
            secret = os.environ.get(secret_name)
            if secret and secret in encoded:
                report["decision"] = "FAIL"
                report["safe_error"] = f"SANITIZATION_FAILED_{secret_name}"
                encoded = json.dumps(report, ensure_ascii=False, indent=2)
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(encoded, encoding="utf-8")
        print(json.dumps({"decision": report["decision"], "checks": len(self.checks), "artifact": str(OUT)}), flush=True)

    def run(self) -> int:
        try:
            self.preflight()
            self.verify_exact_orphan()
            self.cleanup()
        except Exception as exc:
            self.safe_error = safe(exc)
            print(f"SAFE_ERROR: {self.safe_error}", flush=True)
        finally:
            self.write_report()
        return 0 if self.safe_error is None and all(c["status"] == "PASS" for c in self.checks) else 1


if __name__ == "__main__":
    sys.exit(Cleanup().run())
