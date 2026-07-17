#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Callable
from uuid import uuid4

import httpx

OUT = Path("artifacts/sprint-8c-restart-prepare.json")


def required(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required input: {name}")
    return value


def request_with_retry(operation: Callable[[], httpx.Response], attempts: int = 8) -> httpx.Response:
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            response = operation()
            if response.status_code < 500:
                return response
        except (httpx.TimeoutException, httpx.NetworkError) as exc:
            last_error = exc
        if attempt < attempts:
            time.sleep(min(5 * attempt, 20))
    if last_error is not None:
        raise last_error
    return operation()


def main() -> int:
    api = required("STAGING_API_URL").rstrip("/")
    email = required("STAGING_OWNER_EMAIL")
    password = required("STAGING_OWNER_PASSWORD")
    workspace_id = required("STAGING_TEST_WORKSPACE_ID")
    run_id = os.environ.get("GITHUB_RUN_ID", str(uuid4()))
    unique = str(uuid4())[:8]
    file_name = f"qa-8c-restart-boundary-{run_id}-{unique}.csv"
    customer_name = f"QA 8C Restart Boundary {run_id} {unique}"
    customer_phone = f"+3800009{unique[:6]}"
    mapping = {"name": "Name", "phone": "Phone"}
    dry_run_payload = {
        "entity_type": "customers",
        "sheet_name": "CSV",
        "column_mapping": mapping,
        "options": {"qa_marker": "sprint-8c-restart-boundary", "run_id": run_id},
    }
    result: dict[str, object] = {
        "phase": "prepare",
        "health": "FAIL",
        "login": "FAIL",
        "upload": "FAIL",
        "sheets": "FAIL",
        "dry_run": "FAIL",
        "job_id": None,
        "file_name": file_name,
        "entity_type": "customers",
        "sheet_name": "CSV",
        "column_mapping": mapping,
        "options": dry_run_payload["options"],
        "expected_customer_name": customer_name,
        "safe_error": None,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)

    try:
        timeout = httpx.Timeout(connect=30.0, read=90.0, write=90.0, pool=30.0)
        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            health = request_with_retry(lambda: client.get(f"{api}/health"))
            result["health_http"] = health.status_code
            if health.status_code != 200:
                result["safe_error"] = "Backend health check failed"
                return 1
            result["health"] = "PASS"

            login = request_with_retry(lambda: client.post(f"{api}/api/v1/auth/login", json={"email": email, "password": password}))
            result["login_http"] = login.status_code
            if login.status_code != 200:
                result["safe_error"] = "Owner login failed"
                return 1
            token = login.json().get("access_token")
            if not token:
                result["safe_error"] = "Owner login returned no access token"
                return 1
            result["login"] = "PASS"

            headers = {"Authorization": f"Bearer {token}", "X-Workspace-ID": workspace_id}
            content = f"Name,Phone\n{customer_name},{customer_phone}\n".encode("utf-8")
            upload = request_with_retry(
                lambda: client.post(
                    f"{api}/api/v1/import/upload",
                    headers=headers,
                    files={"file": (file_name, content, "text/csv")},
                ),
                attempts=3,
            )
            result["upload_http"] = upload.status_code
            if upload.status_code != 201:
                detail = upload.json().get("detail") if upload.headers.get("content-type", "").startswith("application/json") else None
                result["safe_error"] = str(detail or "Import upload failed")[:300]
                return 1
            job_id = upload.json().get("job_id")
            result["job_id"] = job_id
            result["upload"] = "PASS"

            sheets = request_with_retry(lambda: client.get(f"{api}/api/v1/import/{job_id}/sheets", headers=headers), attempts=3)
            result["sheets_http"] = sheets.status_code
            if sheets.status_code != 200:
                detail = sheets.json().get("detail") if sheets.headers.get("content-type", "").startswith("application/json") else None
                result["safe_error"] = str(detail or "Sheet listing failed")[:300]
                return 1
            result["sheets"] = "PASS"
            result["sheet_names"] = sheets.json().get("sheets", [])

            dry_run = request_with_retry(lambda: client.post(f"{api}/api/v1/import/{job_id}/dry-run", headers=headers, json=dry_run_payload), attempts=3)
            result["dry_run_http"] = dry_run.status_code
            if dry_run.status_code != 200:
                detail = dry_run.json().get("detail") if dry_run.headers.get("content-type", "").startswith("application/json") else None
                result["safe_error"] = str(detail or "Dry-run failed")[:300]
                return 1
            dry_payload = dry_run.json()
            result["dry_run"] = "PASS"
            result["total_rows"] = dry_payload.get("total_rows")
            result["error_rows"] = dry_payload.get("error_rows")
            result["ready_to_import_rows"] = dry_payload.get("ready_to_import_rows")
            if dry_payload.get("error_rows") not in (0, None):
                result["safe_error"] = "Dry-run returned error rows"
                return 1
            return 0
    except Exception as exc:
        result["safe_error"] = f"{exc.__class__.__name__} during restart-boundary prepare"
        return 1
    finally:
        OUT.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
        print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    raise SystemExit(main())
