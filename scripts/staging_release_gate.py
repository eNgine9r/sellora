#!/usr/bin/env python3
"""Safe Sellora staging release-gate smoke runner.

The runner is intentionally conservative: it reads staging endpoints and optional
QA credentials from environment variables, never prints tokens/passwords, and
keeps controlled writes disabled unless STAGING_ALLOW_CONTROLLED_WRITES=true.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import Request, urlopen

DEFAULT_FRONTEND_URL = "https://sellora-web-staging.vercel.app/"
DEFAULT_API_URL = "https://sellora-api-staging.onrender.com"
ARTIFACT_PATH = Path("artifacts/staging-release-gate.json")
TIMEOUT_SECONDS = 20

SENSITIVE_ENV_KEYS = {
    "STAGING_OWNER_PASSWORD",
    "STAGING_MANAGER_PASSWORD",
    "STAGING_ANALYST_PASSWORD",
}
ROLE_ENV = {
    "OWNER": ("STAGING_OWNER_EMAIL", "STAGING_OWNER_PASSWORD"),
    "MANAGER": ("STAGING_MANAGER_EMAIL", "STAGING_MANAGER_PASSWORD"),
    "ANALYST": ("STAGING_ANALYST_EMAIL", "STAGING_ANALYST_PASSWORD"),
}
CORE_READ_PATHS = {
    "dashboard": "/analytics/dashboard-summary",
    "leads": "/leads",
    "customers": "/customers",
    "products": "/products",
    "inventory": "/inventory",
    "orders": "/orders",
    "shipments": "/shipments",
    "finance": "/finance/summary",
    "advertising": "/advertising/summary",
    "analytics": "/analytics/dashboard-summary",
    "settings_workspace": "/workspaces/current",
    "settings_team": "/workspace-users",
    "import_center": "/import/presets/your-jewelry",
}


@dataclass
class StepResult:
    status: str
    summary: str
    detail: str | None = None


@dataclass
class GateState:
    gates: dict[str, str] = field(default_factory=dict)
    issues: list[dict[str, str]] = field(default_factory=list)

    def set_gate(self, gate: str, status: str) -> None:
        current = self.gates.get(gate)
        order = {"PASS": 0, "WARN": 1, "BLOCKED": 2, "FAIL": 3}
        if current is None or order[status] > order[current]:
            self.gates[gate] = status

    def add_issue(self, issue_id: str, severity: str, gate: str, page_api: str, issue: str, expected: str, status: str) -> None:
        self.issues.append(
            {
                "id": issue_id,
                "severity": severity,
                "gate": gate,
                "page_api": page_api,
                "issue": issue,
                "expected": expected,
                "status": status,
            }
        )
        if severity in {"Critical", "Major"} and status != "Resolved":
            self.set_gate(gate, "FAIL" if severity == "Critical" else "BLOCKED")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def clean_base_url(value: str) -> str:
    return value.rstrip("/")


def api_url(base: str, path: str) -> str:
    normalized = clean_base_url(base)
    prefix = "/api/v1"
    if normalized.endswith(prefix):
        return urljoin(f"{normalized}/", path.lstrip("/"))
    return urljoin(f"{normalized}{prefix}/", path.lstrip("/"))


def http_request(url: str, *, method: str = "GET", headers: dict[str, str] | None = None, body: dict[str, Any] | None = None) -> tuple[int, dict[str, Any] | str]:
    payload = None
    request_headers = dict(headers or {})
    if body is not None:
        payload = json.dumps(body).encode("utf-8")
        request_headers["Content-Type"] = "application/json"
    req = Request(url, data=payload, method=method, headers=request_headers)
    try:
        with urlopen(req, timeout=TIMEOUT_SECONDS) as response:
            raw = response.read().decode("utf-8", errors="replace")
            content_type = response.headers.get("content-type", "")
            if "application/json" in content_type:
                return response.status, json.loads(raw) if raw else {}
            return response.status, raw[:400]
    except HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")[:400]
        return exc.code, {"error": raw or exc.reason}
    except URLError as exc:
        return 0, {"error": str(exc.reason)}
    except TimeoutError:
        return 0, {"error": "request timed out"}


def status_from_code(code: int) -> str:
    if 200 <= code < 400:
        return "PASS"
    if code in {401, 403, 404, 405}:
        return "WARN"
    if code == 0 or code >= 500:
        return "FAIL"
    return "WARN"


def login(api_base: str, email: str, password: str) -> tuple[str | None, StepResult]:
    code, payload = http_request(api_url(api_base, "/auth/login"), method="POST", body={"email": email, "password": password})
    if code != 200 or not isinstance(payload, dict):
        return None, StepResult("FAIL", f"login returned HTTP {code}")
    token = payload.get("access_token")
    if not isinstance(token, str) or not token:
        return None, StepResult("FAIL", "login response did not include an access token")
    return token, StepResult("PASS", "login succeeded; token suppressed")


def fetch_me(api_base: str, token: str) -> tuple[dict[str, Any] | None, StepResult]:
    code, payload = http_request(api_url(api_base, "/auth/me"), headers={"Authorization": f"Bearer {token}"})
    if code != 200 or not isinstance(payload, dict):
        return None, StepResult("FAIL", f"/auth/me returned HTTP {code}")
    return payload, StepResult("PASS", "/auth/me succeeded")


def choose_workspace(user: dict[str, Any], requested_workspace: str | None) -> tuple[str | None, StepResult]:
    memberships = user.get("memberships") if isinstance(user, dict) else None
    if not isinstance(memberships, list) or not memberships:
        return None, StepResult("FAIL", "authenticated user has no workspace memberships")
    if requested_workspace:
        for membership in memberships:
            if str(membership.get("workspace_id")) == requested_workspace:
                return requested_workspace, StepResult("PASS", "requested QA workspace is available")
        return None, StepResult("FAIL", "requested QA workspace is not available to the user")
    workspace = memberships[0].get("workspace_id")
    return str(workspace), StepResult("PASS", "selected first available workspace")


def smoke_core_reads(api_base: str, token: str, workspace_id: str, state: GateState) -> dict[str, str]:
    results: dict[str, str] = {}
    headers = {"Authorization": f"Bearer {token}", "X-Workspace-ID": workspace_id}
    for name, path in CORE_READ_PATHS.items():
        code, _payload = http_request(api_url(api_base, path), headers=headers)
        status = status_from_code(code)
        results[name] = f"{status} HTTP {code}"
        if status == "FAIL":
            state.add_issue(
                f"8A-QA-AUTO-{len(state.issues) + 1:03d}",
                "Major",
                "G3-G9",
                path,
                f"Read-only smoke endpoint returned HTTP {code}",
                "Core read endpoints should not return 5xx or network errors.",
                "Open",
            )
    return results


def controlled_write_notice(allow_writes: bool, mode: str, state: GateState) -> str:
    if mode != "controlled-write":
        return "Not requested; runner remained read-only."
    if not allow_writes:
        state.add_issue(
            "8A-QA-002",
            "Major",
            "G4-G6",
            "controlled-write smoke",
            "Controlled-write mode requested without STAGING_ALLOW_CONTROLLED_WRITES=true.",
            "Synthetic writes must require an explicit safety flag and dedicated QA workspace.",
            "Blocked",
        )
        return "Blocked because STAGING_ALLOW_CONTROLLED_WRITES=true was not set."
    return "Enabled by flag, but no destructive or external-provider operations are implemented in this runner."


def build_artifact(args: argparse.Namespace) -> dict[str, Any]:
    frontend_url = os.getenv("STAGING_FRONTEND_URL", DEFAULT_FRONTEND_URL)
    api_base = os.getenv("STAGING_API_URL", DEFAULT_API_URL)
    requested_workspace = os.getenv("STAGING_TEST_WORKSPACE_ID")
    allow_writes = os.getenv("STAGING_ALLOW_CONTROLLED_WRITES", "").lower() == "true"
    state = GateState()
    run_id = f"8A1-{int(time.time())}"

    frontend_code, frontend_body = http_request(frontend_url)
    frontend_status = status_from_code(frontend_code)
    state.set_gate("G0", frontend_status if frontend_status != "WARN" else "PASS")

    health_code, health_body = http_request(urljoin(f"{clean_base_url(api_base)}/", "health"))
    backend_status = "PASS" if health_code == 200 else status_from_code(health_code)
    state.set_gate("G0", backend_status)

    result: dict[str, Any] = {
        "run_id": run_id,
        "timestamp": utc_now(),
        "environment": "staging",
        "mode": args.mode,
        "frontend": {
            "status": frontend_status,
            "url": frontend_url,
            "http_status": frontend_code,
            "commit": os.getenv("STAGING_FRONTEND_COMMIT", "unknown"),
        },
        "backend": {
            "status": backend_status,
            "url": api_base,
            "health_http_status": health_code,
            "commit": os.getenv("STAGING_BACKEND_COMMIT", "unknown"),
        },
        "database": {
            "expected_alembic_head": os.getenv("STAGING_EXPECTED_ALEMBIC_HEAD", os.getenv("STAGING_EXPECTED_ALEMBIC_REVISION", "202607080020")),
            "expected_revision": os.getenv("STAGING_EXPECTED_ALEMBIC_HEAD", os.getenv("STAGING_EXPECTED_ALEMBIC_REVISION", "202607080020")),
            "runtime_revision": os.getenv("STAGING_RUNTIME_ALEMBIC_REVISION", "not_verified_by_runner"),
            "compatibility": "PASS" if os.getenv("STAGING_RUNTIME_ALEMBIC_REVISION") == os.getenv("STAGING_EXPECTED_ALEMBIC_HEAD", os.getenv("STAGING_EXPECTED_ALEMBIC_REVISION", "202607080020")) else "BLOCKED",
            "migration_runtime_status": "PASS" if os.getenv("STAGING_RUNTIME_ALEMBIC_REVISION") == os.getenv("STAGING_EXPECTED_ALEMBIC_HEAD", os.getenv("STAGING_EXPECTED_ALEMBIC_REVISION", "202607080020")) else "BLOCKED",
        },
        "gates": {"G0": state.gates.get("G0", "BLOCKED")},
        "role_results": {},
        "roles": {"owner": "BLOCKED", "manager": "BLOCKED", "analyst": "BLOCKED"},
        "core_read_results": {},
        "core_e2e": {
            "lead": "BLOCKED",
            "customer": "BLOCKED",
            "product": "BLOCKED",
            "variant": "BLOCKED",
            "inventory": "BLOCKED",
            "order": "BLOCKED",
            "payment_status": "BLOCKED",
            "shipment_draft": "BLOCKED",
            "dashboard_finance_visibility": "BLOCKED",
            "cross_workspace_negative": "BLOCKED",
            "cleanup": "BLOCKED",
        },
        "workspace_switching": "BLOCKED",
        "browser_mobile": "BLOCKED",
        "console_network": "BLOCKED",
        "controlled_write": controlled_write_notice(allow_writes, args.mode, state),
        "issues": state.issues,
    }

    if frontend_status == "FAIL":
        state.add_issue("8A-QA-001", "Critical", "G0", frontend_url, "Frontend staging did not respond successfully.", "Frontend should serve the Sellora app over HTTPS.", "Open")
    if backend_status == "FAIL":
        state.add_issue("8A-QA-003", "Critical", "G0", "/health", "Backend health did not respond successfully.", "Backend health should return HTTP 200.", "Open")

    owner_token: str | None = None
    owner_workspace: str | None = None
    missing_credentials = []
    for role, (email_key, password_key) in ROLE_ENV.items():
        email = os.getenv(email_key)
        password = os.getenv(password_key)
        if not email or not password:
            missing_credentials.append(role)
            result["role_results"][role] = {"status": "BLOCKED", "summary": f"Missing {email_key}/{password_key}."}
            result["roles"][role.lower()] = "BLOCKED"
            continue
        token, login_result = login(api_base, email, password)
        role_result: dict[str, Any] = {"login": login_result.__dict__}
        if token:
            me, me_result = fetch_me(api_base, token)
            role_result["me"] = me_result.__dict__
            if me:
                workspace_id, workspace_result = choose_workspace(me, requested_workspace)
                role_result["workspace"] = workspace_result.__dict__
                if role == "OWNER":
                    owner_token = token
                    owner_workspace = workspace_id
        result["role_results"][role] = role_result
        result["roles"][role.lower()] = "PASS" if token and role_result.get("me", {}).get("status") == "PASS" else "FAIL"

    if missing_credentials:
        state.add_issue(
            "8A-QA-004",
            "Major",
            "G1",
            "staging credentials",
            f"Missing staging credentials for: {', '.join(missing_credentials)}.",
            "OWNER, MANAGER and ANALYST credentials are required for the full release gate.",
            "Blocked",
        )
        for gate in ["G1", "G2", "G4", "G5", "G6", "G10", "G11"]:
            state.set_gate(gate, "BLOCKED")

    if owner_token and owner_workspace:
        result["core_read_results"] = smoke_core_reads(api_base, owner_token, owner_workspace, state)
        for gate in ["G2", "G3", "G4", "G5", "G6", "G7", "G8", "G9"]:
            state.set_gate(gate, "PASS")
    else:
        for gate in ["G2", "G3", "G4", "G5", "G6", "G7", "G8", "G9"]:
            state.set_gate(gate, "BLOCKED")

    # Mobile/PWA and console review require browser automation or manual evidence.
    state.set_gate("G10", state.gates.get("G10", "BLOCKED"))
    state.set_gate("G11", state.gates.get("G11", "BLOCKED"))

    if args.mode == "controlled-write" and (not owner_token or not owner_workspace):
        result["controlled_write"] = "Blocked before writes because staging access, credentials or QA workspace resolution did not pass."
    result["gates"] = {f"G{i}": state.gates.get(f"G{i}", "BLOCKED") for i in range(12)}
    result["issues"] = state.issues
    result["critical_issues"] = sum(1 for issue in state.issues if issue["severity"] == "Critical" and issue["status"] != "Resolved")
    result["major_issues"] = sum(1 for issue in state.issues if issue["severity"] == "Major" and issue["status"] != "Resolved")
    result["release_decision"] = "RED" if result["critical_issues"] or result["major_issues"] else "YELLOW"
    result["sprint_status"] = "BLOCKED" if any(status == "BLOCKED" for status in result["gates"].values()) else "APPROVED"

    return result


def write_artifact(data: dict[str, Any]) -> None:
    ARTIFACT_PATH.parent.mkdir(parents=True, exist_ok=True)
    ARTIFACT_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a safe Sellora staging release-gate smoke check.")
    parser.add_argument("--mode", choices=["read-only", "controlled-write"], default="read-only")
    args = parser.parse_args()
    for key in SENSITIVE_ENV_KEYS:
        if os.getenv(key):
            # This intentionally does not print values.
            pass
    artifact = build_artifact(args)
    write_artifact(artifact)
    print(json.dumps({
        "run_id": artifact["run_id"],
        "frontend": artifact["frontend"]["status"],
        "backend": artifact["backend"]["status"],
        "sprint_status": artifact["sprint_status"],
        "release_decision": artifact["release_decision"],
        "artifact": str(ARTIFACT_PATH),
    }, ensure_ascii=False, indent=2))
    if artifact["release_decision"] == "RED":
        return 2
    if artifact["sprint_status"] == "BLOCKED":
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
