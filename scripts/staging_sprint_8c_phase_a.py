#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable

import httpx


OUT = Path("artifacts/sprint-8c-phase-a.json")


def required(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required input: {name}")
    return value


def retry(operation: Callable[[], httpx.Response], attempts: int = 10) -> httpx.Response:
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            response = operation()
            if response.status_code < 500:
                return response
        except (httpx.TimeoutException, httpx.NetworkError) as exc:
            last_error = exc
        if attempt < attempts:
            time.sleep(min(attempt * 4, 20))
    if last_error:
        raise last_error
    return operation()


def safe_detail(response: httpx.Response) -> str:
    try:
        payload = response.json()
        value = payload.get("detail") if isinstance(payload, dict) else None
        return str(value or f"HTTP {response.status_code}")[:300]
    except Exception:
        return f"HTTP {response.status_code}"


def login(client: httpx.Client, api: str, email: str, password: str) -> str:
    response = retry(lambda: client.post(f"{api}/api/v1/auth/login", json={"email": email, "password": password}))
    if response.status_code != 200:
        raise RuntimeError("Synthetic role login failed")
    token = response.json().get("access_token")
    if not token:
        raise RuntimeError("Synthetic role login returned no access token")
    return token


def headers(token: str, workspace_id: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}", "X-Workspace-ID": workspace_id}


def check(result: dict[str, Any], name: str, condition: bool, detail: str = "") -> None:
    result["checks"].append({"name": name, "status": "PASS" if condition else "FAIL", "detail": detail[:300]})
    if not condition:
        raise RuntimeError(f"Gate failed: {name}")


def main() -> int:
    api = required("STAGING_API_URL").rstrip("/")
    workspace_a = required("STAGING_TEST_WORKSPACE_ID")
    expected_commit = required("EXPECTED_RUNTIME_COMMIT")
    credentials = {
        "OWNER": (required("STAGING_OWNER_EMAIL"), required("STAGING_OWNER_PASSWORD")),
        "MANAGER": (required("STAGING_MANAGER_EMAIL"), required("STAGING_MANAGER_PASSWORD")),
        "ANALYST": (required("STAGING_ANALYST_EMAIL"), required("STAGING_ANALYST_PASSWORD")),
    }
    result: dict[str, Any] = {
        "phase": "A",
        "decision": "FAIL",
        "checks": [],
        "baseline_health": {},
        "workspace_a": workspace_a,
        "workspace_b": None,
        "job_id": None,
        "entity_type": "customers",
        "sheet_name": "CSV",
        "mapping": {"name": "Name", "phone": "Phone", "instagram_username": "Instagram"},
        "options": {"duplicate_policy": "SKIP"},
        "safe_error": None,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)

    try:
        timeout = httpx.Timeout(connect=30.0, read=120.0, write=120.0, pool=30.0)
        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            health = retry(lambda: client.get(f"{api}/health"), attempts=15)
            health_data = health.json() if health.status_code == 200 else {}
            result["baseline_health"] = {
                "status": health_data.get("status"),
                "runtime_commit": health_data.get("runtime_commit"),
                "process_started_at": health_data.get("process_started_at"),
            }
            check(result, "backend health", health.status_code == 200 and health_data.get("status") == "ok")
            check(result, "runtime identity deployed", str(health_data.get("runtime_commit", "")).startswith(expected_commit[:12]))
            check(result, "runtime process marker present", bool(health_data.get("process_started_at")))

            tokens = {role: login(client, api, *values) for role, values in credentials.items()}
            check(result, "OWNER login", bool(tokens["OWNER"]))
            check(result, "MANAGER login", bool(tokens["MANAGER"]))
            check(result, "ANALYST login", bool(tokens["ANALYST"]))

            me = retry(lambda: client.get(f"{api}/api/v1/auth/me", headers={"Authorization": f"Bearer {tokens['OWNER']}"}))
            check(result, "/auth/me", me.status_code == 200)

            suffix = datetime.now(UTC).strftime("%m%d%H%M%S").lower()
            workspace_response = retry(
                lambda: client.post(
                    f"{api}/api/v1/workspaces",
                    headers={"Authorization": f"Bearer {tokens['OWNER']}"},
                    json={
                        "name": f"QA Sprint 8C Workspace B {suffix}",
                        "slug": f"qa-8c-b-{suffix}",
                        "currency_code": "UAH",
                        "timezone": "Europe/Kyiv",
                    },
                )
            )
            check(result, "Workspace B created", workspace_response.status_code == 201, safe_detail(workspace_response))
            workspace_b = str(workspace_response.json()["id"])
            result["workspace_b"] = workspace_b

            content = (
                "Name,Phone,Instagram\n"
                f"QA8C Restart Customer A,SYNTH-{suffix}-A,qa8c_restart_a_{suffix}\n"
                f"QA8C Restart Customer B,SYNTH-{suffix}-B,qa8c_restart_b_{suffix}\n"
            ).encode("utf-8")
            owner_a = headers(tokens["OWNER"], workspace_a)
            upload = retry(
                lambda: client.post(
                    f"{api}/api/v1/import/upload",
                    headers=owner_a,
                    files={"file": (f"qa8c-restart-{suffix}.csv", content, "text/csv")},
                )
            )
            check(result, "durable upload", upload.status_code == 201, safe_detail(upload))
            job_id = str(upload.json()["job_id"])
            result["job_id"] = job_id

            sheets = retry(lambda: client.get(f"{api}/api/v1/import/{job_id}/sheets", headers=owner_a))
            check(result, "sheet selection", sheets.status_code == 200 and sheets.json().get("sheets") == ["CSV"], safe_detail(sheets))

            preview = retry(
                lambda: client.post(
                    f"{api}/api/v1/import/{job_id}/preview",
                    headers=owner_a,
                    json={"sheet_name": "CSV", "limit": 20},
                )
            )
            check(result, "preview", preview.status_code == 200 and len(preview.json().get("rows", [])) == 2, safe_detail(preview))

            payload = {
                "entity_type": "customers",
                "sheet_name": "CSV",
                "column_mapping": result["mapping"],
                "options": result["options"],
            }
            validation = retry(lambda: client.post(f"{api}/api/v1/import/{job_id}/validate", headers=owner_a, json=payload))
            check(result, "validation", validation.status_code == 200 and validation.json().get("is_valid") is True, safe_detail(validation))

            dry_run = retry(lambda: client.post(f"{api}/api/v1/import/{job_id}/dry-run", headers=owner_a, json=payload))
            dry_data = dry_run.json() if dry_run.status_code == 200 else {}
            check(result, "persisted dry-run", dry_run.status_code == 200 and dry_data.get("error_rows") == 0, safe_detail(dry_run))
            check(result, "dry-run planned rows", dry_data.get("ready_to_import_rows") == 2)

            changed_payload = {
                "entity_type": "customers",
                "sheet_name": "CSV",
                "column_mapping": {"name": "Name", "instagram_username": "Instagram"},
                "mode": "create_only",
                "dry_run": False,
                "options": result["options"],
            }
            changed_execute = retry(lambda: client.post(f"{api}/api/v1/import/{job_id}/execute", headers=owner_a, json=changed_payload))
            check(result, "changed mapping rejected", changed_execute.status_code == 400 and "changed" in safe_detail(changed_execute).lower(), safe_detail(changed_execute))

            restore_dry_run = retry(lambda: client.post(f"{api}/api/v1/import/{job_id}/dry-run", headers=owner_a, json=payload))
            check(result, "approval restored for exact input", restore_dry_run.status_code == 200 and restore_dry_run.json().get("error_rows") == 0, safe_detail(restore_dry_run))

            exact_execute_payload = {**payload, "mode": "create_only", "dry_run": False}
            cross_workspace = retry(
                lambda: client.post(
                    f"{api}/api/v1/import/{job_id}/execute",
                    headers=headers(tokens["OWNER"], workspace_b),
                    json=exact_execute_payload,
                )
            )
            check(result, "Workspace B execute denied", cross_workspace.status_code in {400, 404}, safe_detail(cross_workspace))

            manager_upload = retry(
                lambda: client.post(
                    f"{api}/api/v1/import/upload",
                    headers=headers(tokens["MANAGER"], workspace_a),
                    files={"file": ("qa8c-manager-denied.csv", b"Name\nDenied\n", "text/csv")},
                )
            )
            check(result, "MANAGER upload denied", manager_upload.status_code == 403, safe_detail(manager_upload))
            manager_execute = retry(lambda: client.post(f"{api}/api/v1/import/{job_id}/execute", headers=headers(tokens["MANAGER"], workspace_a), json=exact_execute_payload))
            check(result, "MANAGER execute denied", manager_execute.status_code == 403, safe_detail(manager_execute))

            analyst_upload = retry(
                lambda: client.post(
                    f"{api}/api/v1/import/upload",
                    headers=headers(tokens["ANALYST"], workspace_a),
                    files={"file": ("qa8c-analyst-denied.csv", b"Name\nDenied\n", "text/csv")},
                )
            )
            check(result, "ANALYST upload denied", analyst_upload.status_code == 403, safe_detail(analyst_upload))
            analyst_execute = retry(lambda: client.post(f"{api}/api/v1/import/{job_id}/execute", headers=headers(tokens["ANALYST"], workspace_a), json=exact_execute_payload))
            check(result, "ANALYST execute denied", analyst_execute.status_code == 403, safe_detail(analyst_execute))

            result["decision"] = "PASS"
            return 0
    except Exception as exc:
        result["safe_error"] = str(exc)[:300]
        return 1
    finally:
        OUT.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
        print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    raise SystemExit(main())
