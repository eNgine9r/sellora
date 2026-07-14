#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Callable

import httpx


OUT = Path("artifacts/sprint-8c-storage-readiness.json")


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
    result: dict[str, object] = {
        "health": "FAIL",
        "login": "FAIL",
        "upload": "FAIL",
        "sheets": "FAIL",
        "job_id": None,
        "safe_error": None,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)

    try:
        timeout = httpx.Timeout(connect=30.0, read=90.0, write=90.0, pool=30.0)
        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            health = request_with_retry(lambda: client.get(f"{api}/health"))
            result["health_http"] = health.status_code
            result["health"] = "PASS" if health.status_code == 200 else "FAIL"
            if health.status_code != 200:
                result["safe_error"] = "Backend health check failed"
                return 1

            login = request_with_retry(
                lambda: client.post(
                    f"{api}/api/v1/auth/login",
                    json={"email": email, "password": password},
                )
            )
            result["login_http"] = login.status_code
            if login.status_code != 200:
                result["safe_error"] = "Owner login failed"
                return 1
            token = login.json().get("access_token")
            if not token:
                result["safe_error"] = "Owner login returned no access token"
                return 1
            result["login"] = "PASS"

            headers = {
                "Authorization": f"Bearer {token}",
                "X-Workspace-ID": workspace_id,
            }
            content = b"Name,Phone\nQA Storage Probe,+380000000991\n"
            upload = request_with_retry(
                lambda: client.post(
                    f"{api}/api/v1/import/upload",
                    headers=headers,
                    files={"file": ("qa-storage-probe.csv", content, "text/csv")},
                ),
                attempts=3,
            )
            result["upload_http"] = upload.status_code
            if upload.status_code != 201:
                detail = upload.json().get("detail") if upload.headers.get("content-type", "").startswith("application/json") else None
                result["safe_error"] = str(detail or "Import upload failed")[:300]
                return 1
            payload = upload.json()
            job_id = payload.get("job_id")
            result["job_id"] = job_id
            result["upload"] = "PASS"

            sheets = request_with_retry(
                lambda: client.get(
                    f"{api}/api/v1/import/{job_id}/sheets",
                    headers=headers,
                ),
                attempts=3,
            )
            result["sheets_http"] = sheets.status_code
            if sheets.status_code != 200:
                detail = sheets.json().get("detail") if sheets.headers.get("content-type", "").startswith("application/json") else None
                result["safe_error"] = str(detail or "Sheet listing failed")[:300]
                return 1
            result["sheets"] = "PASS"
            result["sheet_names"] = sheets.json().get("sheets", [])
            return 0
    except Exception as exc:
        result["safe_error"] = f"{exc.__class__.__name__} during staging storage probe"
        return 1
    finally:
        OUT.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
        print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    raise SystemExit(main())
