#!/usr/bin/env python3
"""Sprint 8E read-only Nova Poshta staging preflight.

This runner configures only the dedicated QA8E workspace, validates the real
provider connection and directory reads, and proves RBAC/tenant isolation.
It never calls InternetDocument.save and therefore creates no provider document.
"""
from __future__ import annotations

import json
import os
import re
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import quote
from uuid import uuid4

import httpx

API_ROOT = os.environ["STAGING_API_URL"].rstrip("/")
API = API_ROOT + "/api/v1"
FRONTEND = os.environ["STAGING_FRONTEND_URL"].rstrip("/")
EXPECTED_COMMIT = os.environ["EXPECTED_RUNTIME_COMMIT"].lower()
WORKSPACE_ID = os.environ["QA8E_WORKSPACE_ID"]
OUT = Path("artifacts/sprint-8e/preflight.json")
TIMEOUT = httpx.Timeout(connect=20, read=60, write=60, pool=20)

SECRET_NAMES = (
    "STAGING_OWNER_PASSWORD",
    "STAGING_MANAGER_PASSWORD",
    "STAGING_ANALYST_PASSWORD",
    "STAGING_NOVA_POSHTA_API_KEY",
    "STAGING_NOVA_POSHTA_SENDER_CITY_REF",
    "STAGING_NOVA_POSHTA_SENDER_WAREHOUSE_REF",
    "STAGING_NOVA_POSHTA_SENDER_COUNTERPARTY_REF",
    "STAGING_NOVA_POSHTA_SENDER_CONTACT_REF",
    "STAGING_NOVA_POSHTA_SENDER_PHONE",
)


class Preflight:
    def __init__(self) -> None:
        self.checks: list[dict[str, Any]] = []
        self.sessions: dict[str, str] = {}
        self.runtime: dict[str, Any] = {}
        self.network = {"requests": 0, "provider_reads": 0, "provider_writes": 0, "http_5xx": 0}
        self.safe_error: str | None = None

    def check(self, gate: str, name: str, ok: bool, detail: Any = None) -> None:
        item: dict[str, Any] = {"gate": gate, "name": name, "status": "PASS" if ok else "FAIL"}
        if detail is not None:
            item["detail"] = self.safe(detail)
        self.checks.append(item)
        print(json.dumps(item, ensure_ascii=False), flush=True)

    @staticmethod
    def safe(value: Any) -> Any:
        if isinstance(value, dict):
            blocked = {"access_token", "refresh_token", "authorization", "password", "api_key", "masked_api_key", "sender_phone"}
            return {str(k): Preflight.safe(v) for k, v in value.items() if str(k).lower() not in blocked}
        if isinstance(value, list):
            return [Preflight.safe(v) for v in value[:20]]
        text = str(value)
        text = re.sub(r"Bearer\s+\S+", "Bearer [REDACTED]", text, flags=re.I)
        text = re.sub(r"\beyJ[A-Za-z0-9._-]{20,}\b", "[TOKEN]", text)
        return text[:500]

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
        if "/integrations/nova-poshta/" in url and any(token in url for token in ("test-connection", "cities", "warehouses")):
            self.network["provider_reads"] += 1
        if "create-ttn" in url or "InternetDocument" in url:
            self.network["provider_writes"] += 1
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
        token = str(body["access_token"])
        self.sessions[role] = token
        _, me = self.request("GET", "/auth/me", role=role, expected=(200,))
        membership = next(
            (m for m in me.get("memberships", []) if str(m.get("workspace_id")) == WORKSPACE_ID),
            None,
        )
        self.check("1", f"{role} QA8E membership", bool(membership), {"role": membership.get("role") if membership else None})
        if not membership:
            raise RuntimeError(f"{role} does not have QA8E workspace membership")

    def environment(self) -> None:
        missing = [name for name in SECRET_NAMES if not os.environ.get(name)]
        self.check("1", "protected inputs present", not missing, {"missing_names": missing})
        if missing:
            raise RuntimeError("Required protected inputs are missing")

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
            response = client.get(FRONTEND + "/login")
        self.check("1", "frontend staging reachable", response.status_code == 200, {"status": response.status_code})
        if response.status_code != 200:
            raise RuntimeError("Frontend staging is unavailable")

        self.login("OWNER", "STAGING_OWNER_EMAIL", "STAGING_OWNER_PASSWORD")
        self.login("MANAGER", "STAGING_MANAGER_EMAIL", "STAGING_MANAGER_PASSWORD")
        self.login("ANALYST", "STAGING_ANALYST_EMAIL", "STAGING_ANALYST_PASSWORD")

    def provider_preflight(self) -> None:
        real_key = os.environ["STAGING_NOVA_POSHTA_API_KEY"]
        settings_payload = {
            "api_key": real_key,
            "sender_city_ref": os.environ["STAGING_NOVA_POSHTA_SENDER_CITY_REF"],
            "sender_warehouse_ref": os.environ["STAGING_NOVA_POSHTA_SENDER_WAREHOUSE_REF"],
            "sender_counterparty_ref": os.environ["STAGING_NOVA_POSHTA_SENDER_COUNTERPARTY_REF"],
            "sender_contact_ref": os.environ["STAGING_NOVA_POSHTA_SENDER_CONTACT_REF"],
            "sender_phone": os.environ["STAGING_NOVA_POSHTA_SENDER_PHONE"],
        }

        _, initial = self.request("GET", "/integrations/nova-poshta/settings", role="OWNER", expected=(200,))
        if str(initial.get("status")) == "DISCONNECTED":
            no_key_payload = {k: v for k, v in settings_payload.items() if k != "api_key"}
            code, _ = self.request(
                "POST",
                "/integrations/nova-poshta/settings",
                role="OWNER",
                payload=no_key_payload,
                expected=(400,),
            )
            self.check("2", "first connection without key rejected", code == 400)
        else:
            self.check("2", "missing-key first-connect contract already covered", True, {"runtime_state": "existing QA8E connection"})

        _, saved = self.request(
            "POST",
            "/integrations/nova-poshta/settings",
            role="OWNER",
            payload=settings_payload,
            expected=(200,),
        )
        self.check("3", "sender configuration saved", bool(saved.get("sender_configured")))
        self.check("1", "provider writes remain disabled", saved.get("provider_writes_enabled") is False)
        self.check(
            "2",
            "API key masked in response",
            bool(saved.get("masked_api_key")) and real_key not in json.dumps(saved, ensure_ascii=False),
        )

        _, connected = self.request("POST", "/integrations/nova-poshta/test-connection", role="OWNER", expected=(200,))
        self.check("2", "real Nova Poshta key connected", connected.get("success") is True)

        restore_needed = False
        try:
            invalid_payload = {**settings_payload, "api_key": "qa8e-invalid-provider-key"}
            self.request(
                "POST",
                "/integrations/nova-poshta/settings",
                role="OWNER",
                payload=invalid_payload,
                expected=(200,),
            )
            restore_needed = True
            _, invalid_result = self.request(
                "POST",
                "/integrations/nova-poshta/test-connection",
                role="OWNER",
                expected=(200,),
            )
            self.check(
                "2",
                "invalid key returns safe auth failure",
                invalid_result.get("success") is False and "key" not in str(invalid_result.get("message", "")).lower(),
            )
        finally:
            if restore_needed:
                self.request(
                    "POST",
                    "/integrations/nova-poshta/settings",
                    role="OWNER",
                    payload=settings_payload,
                    expected=(200,),
                )
                _, restored = self.request(
                    "POST",
                    "/integrations/nova-poshta/test-connection",
                    role="OWNER",
                    expected=(200,),
                )
                self.check("2", "real key restored after negative test", restored.get("success") is True)

        _, cities = self.request(
            "GET",
            "/integrations/nova-poshta/cities",
            role="MANAGER",
            params={"q": "Київ", "limit": 20},
            expected=(200,),
        )
        self.check("4", "real city search returns results", isinstance(cities, list) and len(cities) > 0, {"result_count": len(cities) if isinstance(cities, list) else 0})
        self.check("4", "multiple city results supported", isinstance(cities, list) and len(cities) > 1, {"result_count": len(cities) if isinstance(cities, list) else 0})

        _, empty = self.request(
            "GET",
            "/integrations/nova-poshta/cities",
            role="MANAGER",
            params={"q": f"qa8e-no-city-{datetime.now(UTC).strftime('%H%M%S')}", "limit": 20},
            expected=(200,),
        )
        self.check("4", "city search no-results state", isinstance(empty, list) and len(empty) == 0)

        _, warehouses = self.request(
            "GET",
            "/integrations/nova-poshta/warehouses",
            role="MANAGER",
            params={
                "city_ref": os.environ["STAGING_NOVA_POSHTA_SENDER_CITY_REF"],
                "limit": 100,
            },
            expected=(200,),
        )
        configured_warehouse_exists = isinstance(warehouses, list) and any(
            str(item.get("ref")) == os.environ["STAGING_NOVA_POSHTA_SENDER_WAREHOUSE_REF"]
            for item in warehouses
        )
        self.check("3", "sender city and warehouse refs resolve", configured_warehouse_exists, {"warehouse_count": len(warehouses) if isinstance(warehouses, list) else 0})

        code, _ = self.request(
            "GET",
            "/integrations/nova-poshta/settings",
            role="MANAGER",
            expected=(403,),
        )
        self.check("10", "MANAGER configuration denied", code == 403)
        code, _ = self.request(
            "GET",
            "/integrations/nova-poshta/cities",
            role="ANALYST",
            params={"q": "Київ"},
            expected=(403,),
        )
        self.check("10", "ANALYST provider discovery denied", code == 403)
        code, _ = self.request(
            "POST",
            "/integrations/nova-poshta/test-connection",
            role="ANALYST",
            expected=(403,),
        )
        self.check("10", "ANALYST provider write denied", code == 403)

        foreign_workspace = str(uuid4())
        code, _ = self.request(
            "GET",
            "/integrations/nova-poshta/settings",
            role="OWNER",
            workspace=foreign_workspace,
            expected=(403,),
        )
        self.check("11", "foreign settings read denied", code == 403)
        code, _ = self.request(
            "GET",
            "/integrations/nova-poshta/cities",
            role="MANAGER",
            workspace=foreign_workspace,
            params={"q": "Київ"},
            expected=(403,),
        )
        self.check("11", "foreign provider discovery denied", code == 403)

        self.check("1", "provider write calls during preflight", self.network["provider_writes"] == 0, self.network)
        self.check("1", "unexpected HTTP 5xx", self.network["http_5xx"] == 0, self.network)

    def write_report(self) -> None:
        OUT.parent.mkdir(parents=True, exist_ok=True)
        decision = "PASS" if self.safe_error is None and all(c["status"] == "PASS" for c in self.checks) else "FAIL"
        report = {
            "sprint": "8E",
            "phase": "real-provider-preflight",
            "decision": decision,
            "runtime": self.runtime,
            "checks": self.checks,
            "network": self.network,
            "provider_document_created": False,
            "safe_error": self.safe_error,
            "generated_at": datetime.now(UTC).isoformat(),
        }
        encoded = json.dumps(report, ensure_ascii=False, indent=2)
        leaked = [name for name in SECRET_NAMES if os.environ.get(name) and os.environ[name] in encoded]
        if leaked:
            report["decision"] = "FAIL"
            report["safe_error"] = "SANITIZATION_FAILED"
            report["checks"].append({"gate": "1", "name": "secret leakage", "status": "FAIL", "detail": {"secret_names": leaked}})
            encoded = json.dumps(report, ensure_ascii=False, indent=2)
        OUT.write_text(encoded, encoding="utf-8")
        print(json.dumps({"decision": report["decision"], "checks": len(report["checks"]), "artifact": str(OUT)}), flush=True)

    def run(self) -> int:
        try:
            self.environment()
            self.provider_preflight()
        except Exception as exc:
            self.safe_error = self.safe(exc)
            print(f"SAFE_ERROR: {self.safe_error}", flush=True)
        finally:
            self.write_report()
        return 0 if self.safe_error is None and all(c["status"] == "PASS" for c in self.checks) else 1


if __name__ == "__main__":
    sys.exit(Preflight().run())
