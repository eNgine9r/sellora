#!/usr/bin/env python3
from __future__ import annotations

import csv
import io
import json
import os
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable

import httpx

API = os.getenv("STAGING_API_URL", "https://sellora-api-staging.onrender.com").rstrip("/")
WORKSPACE_ID = os.environ["STAGING_TEST_WORKSPACE_ID"]
OUT = Path("artifacts/sprint-8c-performance.json")
DATASETS = (100, 1000, 5000)


def required(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required input: {name}")
    return value


def request_retry(operation: Callable[[], httpx.Response], attempts: int = 5) -> httpx.Response:
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            response = operation()
            if response.status_code < 500:
                return response
        except (httpx.TimeoutException, httpx.NetworkError) as exc:
            last_error = exc
        if attempt < attempts:
            time.sleep(min(attempt * 5, 20))
    if last_error is not None:
        raise last_error
    return operation()


def safe_detail(response: httpx.Response) -> str:
    try:
        body = response.json()
        if isinstance(body, dict):
            return str(body.get("detail") or f"HTTP {response.status_code}")[:300]
    except Exception:
        pass
    return f"HTTP {response.status_code}"


def customer_csv(row_count: int, suffix: str) -> bytes:
    stream = io.StringIO(newline="")
    writer = csv.writer(stream)
    writer.writerow(["Name", "Phone", "Instagram"])
    for index in range(row_count):
        writer.writerow([
            f"QA8C-PERF-{row_count}-{suffix}-{index:05d}",
            f"38067{index:07d}",
            f"qa8c_perf_{row_count}_{suffix}_{index:05d}",
        ])
    return stream.getvalue().encode("utf-8")


class PerformanceClosure:
    def __init__(self) -> None:
        self.result: dict[str, Any] = {
            "decision": "FAIL",
            "datasets": [],
            "runtime_before": {},
            "runtime_after": {},
            "safe_error": None,
        }
        self.timeout = httpx.Timeout(connect=30, read=900, write=900, pool=30)
        self.client = httpx.Client(timeout=self.timeout, follow_redirects=True)
        self.token = ""
        self.suffix = datetime.now(UTC).strftime("%m%d%H%M%S").lower()

    def close(self) -> None:
        self.client.close()

    def health(self) -> dict[str, str]:
        response = request_retry(lambda: self.client.get(f"{API}/health"))
        if response.status_code != 200:
            raise RuntimeError("Backend health check failed")
        body = response.json()
        return {
            "status": str(body.get("status")),
            "runtime_commit": str(body.get("runtime_commit")),
            "process_started_at": str(body.get("process_started_at")),
        }

    def login(self) -> None:
        response = request_retry(lambda: self.client.post(
            f"{API}/api/v1/auth/login",
            json={
                "email": required("STAGING_OWNER_EMAIL"),
                "password": required("STAGING_OWNER_PASSWORD"),
            },
        ))
        if response.status_code != 200:
            raise RuntimeError("OWNER login failed")
        self.token = str(response.json().get("access_token") or "")
        if not self.token:
            raise RuntimeError("OWNER access token missing")

    def headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.token}",
            "X-Workspace-ID": WORKSPACE_ID,
        }

    def run_dataset(self, row_count: int) -> dict[str, Any]:
        content = customer_csv(row_count, self.suffix)
        evidence: dict[str, Any] = {
            "rows": row_count,
            "bytes": len(content),
            "upload_seconds": 0.0,
            "validation_seconds": 0.0,
            "dry_run_seconds": 0.0,
            "execute_seconds": 0.0,
            "total_seconds": 0.0,
            "processed_rows": 0,
            "success_rows": 0,
            "status": "FAIL",
            "safe_error": None,
        }
        total_started = time.perf_counter()
        try:
            upload_started = time.perf_counter()
            upload = request_retry(lambda: self.client.post(
                f"{API}/api/v1/import/upload",
                headers=self.headers(),
                files={
                    "file": (
                        f"qa8c-performance-{row_count}-{self.suffix}.csv",
                        content,
                        "text/csv",
                    )
                },
            ))
            evidence["upload_seconds"] = round(time.perf_counter() - upload_started, 3)
            if upload.status_code != 201:
                raise RuntimeError(f"Upload failed: {safe_detail(upload)}")
            job_id = str(upload.json().get("job_id") or "")
            if not job_id:
                raise RuntimeError("Upload returned no job ID")

            sheets = request_retry(lambda: self.client.get(
                f"{API}/api/v1/import/{job_id}/sheets",
                headers=self.headers(),
            ))
            if sheets.status_code != 200 or sheets.json().get("sheets") != ["CSV"]:
                raise RuntimeError(f"Sheet listing failed: {safe_detail(sheets)}")

            preview = request_retry(lambda: self.client.post(
                f"{API}/api/v1/import/{job_id}/preview",
                headers=self.headers(),
                json={"sheet_name": "CSV", "limit": 20},
            ))
            if preview.status_code != 200:
                raise RuntimeError(f"Preview failed: {safe_detail(preview)}")

            payload = {
                "entity_type": "customers",
                "sheet_name": "CSV",
                "column_mapping": {
                    "name": "Name",
                    "phone": "Phone",
                    "instagram_username": "Instagram",
                },
                "options": {"duplicate_policy": "SKIP"},
            }
            validation_started = time.perf_counter()
            validation = request_retry(lambda: self.client.post(
                f"{API}/api/v1/import/{job_id}/validate",
                headers=self.headers(),
                json=payload,
            ))
            evidence["validation_seconds"] = round(time.perf_counter() - validation_started, 3)
            if validation.status_code != 200 or validation.json().get("is_valid") is not True:
                raise RuntimeError(f"Validation failed: {safe_detail(validation)}")

            dry_started = time.perf_counter()
            dry = request_retry(lambda: self.client.post(
                f"{API}/api/v1/import/{job_id}/dry-run",
                headers=self.headers(),
                json=payload,
            ))
            evidence["dry_run_seconds"] = round(time.perf_counter() - dry_started, 3)
            if dry.status_code != 200:
                raise RuntimeError(f"Dry-run failed: {safe_detail(dry)}")
            dry_body = dry.json()
            if dry_body.get("total_rows") != row_count or dry_body.get("error_rows") != 0:
                raise RuntimeError("Dry-run counts do not match the synthetic dataset")

            execute_started = time.perf_counter()
            execute = request_retry(lambda: self.client.post(
                f"{API}/api/v1/import/{job_id}/execute",
                headers=self.headers(),
                json={**payload, "mode": "create_only", "dry_run": False},
            ), attempts=2)
            evidence["execute_seconds"] = round(time.perf_counter() - execute_started, 3)
            if execute.status_code != 200:
                raise RuntimeError(f"Execute failed: {safe_detail(execute)}")
            job = execute.json().get("job", {})
            evidence["processed_rows"] = int(job.get("processed_rows") or 0)
            evidence["success_rows"] = int(job.get("success_rows") or 0)
            if job.get("status") != "COMPLETED":
                raise RuntimeError(f"Unexpected job status: {job.get('status')}")
            if evidence["processed_rows"] != row_count or evidence["success_rows"] != row_count:
                raise RuntimeError("Execute counts do not match the synthetic dataset")

            after = self.health()
            before = self.result["runtime_before"]
            if after.get("process_started_at") != before.get("process_started_at"):
                raise RuntimeError("Render process restarted during benchmark")
            evidence["status"] = "PASS"
            return evidence
        except Exception as exc:
            evidence["safe_error"] = str(exc)[:300]
            return evidence
        finally:
            evidence["total_seconds"] = round(time.perf_counter() - total_started, 3)

    def run(self) -> int:
        self.result["runtime_before"] = self.health()
        self.login()
        for row_count in DATASETS:
            evidence = self.run_dataset(row_count)
            self.result["datasets"].append(evidence)
            if evidence["status"] != "PASS":
                self.result["runtime_after"] = self.health()
                return 1
        self.result["runtime_after"] = self.health()
        if self.result["runtime_after"].get("process_started_at") != self.result["runtime_before"].get("process_started_at"):
            self.result["safe_error"] = "Render process identity changed during performance gate"
            return 1
        self.result["decision"] = "PASS"
        return 0


def main() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    closure = PerformanceClosure()
    try:
        return closure.run()
    except Exception as exc:
        closure.result["safe_error"] = str(exc)[:300]
        return 1
    finally:
        closure.close()
        OUT.write_text(json.dumps(closure.result, indent=2, ensure_ascii=False), encoding="utf-8")
        print(json.dumps(closure.result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    raise SystemExit(main())
