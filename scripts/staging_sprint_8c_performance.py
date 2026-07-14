#!/usr/bin/env python3
from __future__ import annotations

import csv
import io
import json
import os
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

API = os.getenv("STAGING_API_URL", "https://sellora-api-staging.onrender.com").rstrip("/")
EXPECTED_COMMIT = os.getenv("EXPECTED_RUNTIME_COMMIT", "96a95bca5e378d6dc6da5e6d9bddbb96d935d3b4")
WORKSPACE = os.environ["STAGING_TEST_WORKSPACE_ID"]
OUT = Path("artifacts/sprint-8c-performance.json")


def csv_bytes(size: int, marker: str) -> bytes:
    stream = io.StringIO(newline="")
    writer = csv.writer(stream)
    writer.writerow(["Name", "Instagram"])
    for index in range(size):
        writer.writerow([f"QA8C PERF {marker} {index:05d}", f"qa8c_perf_{marker}_{index:05d}"])
    return stream.getvalue().encode("utf-8")


def main() -> int:
    result: dict[str, Any] = {"decision": "FAIL", "runtime": {}, "datasets": [], "safe_error": None}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    timeout = httpx.Timeout(connect=30, read=1200, write=1200, pool=30)
    try:
        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            deadline = time.monotonic() + 25 * 60
            baseline = None
            while time.monotonic() < deadline:
                health = client.get(f"{API}/health")
                if health.status_code == 200:
                    body = health.json()
                    if str(body.get("runtime_commit", "")).startswith(EXPECTED_COMMIT[:12]) and body.get("process_started_at"):
                        baseline = body
                        break
                time.sleep(15)
            if not baseline:
                raise RuntimeError("Expected identified runtime was not observed")
            result["runtime"] = {"commit": baseline["runtime_commit"], "process_started_at": baseline["process_started_at"]}

            login = client.post(f"{API}/api/v1/auth/login", json={"email": os.environ["STAGING_OWNER_EMAIL"], "password": os.environ["STAGING_OWNER_PASSWORD"]})
            if login.status_code != 200 or not login.json().get("access_token"):
                raise RuntimeError("Synthetic OWNER login failed")
            headers = {"Authorization": f"Bearer {login.json()['access_token']}", "X-Workspace-ID": WORKSPACE}
            suffix = datetime.now(UTC).strftime("%m%d%H%M%S").lower()

            for size in (100, 1000, 5000):
                marker = f"{suffix}_{size}"
                content = csv_bytes(size, marker)
                entry: dict[str, Any] = {"rows": size, "bytes": len(content), "upload": None, "preview": None, "dry_run": None, "execute": None, "status": "FAIL", "core_500": 0, "timeout": 0, "process_restarted": None}
                try:
                    started = time.perf_counter()
                    upload = client.post(f"{API}/api/v1/import/upload", headers=headers, files={"file": (f"qa8c-perf-{marker}.csv", content, "text/csv")})
                    entry["upload"] = round(time.perf_counter() - started, 3)
                    if upload.status_code != 201:
                        if upload.status_code >= 500: entry["core_500"] += 1
                        raise RuntimeError(f"upload HTTP {upload.status_code}")
                    job_id = upload.json()["job_id"]

                    started = time.perf_counter()
                    preview = client.post(f"{API}/api/v1/import/{job_id}/preview", headers=headers, json={"sheet_name": "CSV", "limit": 20})
                    entry["preview"] = round(time.perf_counter() - started, 3)
                    if preview.status_code != 200:
                        if preview.status_code >= 500: entry["core_500"] += 1
                        raise RuntimeError(f"preview HTTP {preview.status_code}")

                    payload = {"entity_type": "customers", "sheet_name": "CSV", "column_mapping": {"name": "Name", "instagram_username": "Instagram"}, "options": {"duplicate_policy": "SKIP"}}
                    started = time.perf_counter()
                    dry = client.post(f"{API}/api/v1/import/{job_id}/dry-run", headers=headers, json=payload)
                    entry["dry_run"] = round(time.perf_counter() - started, 3)
                    if dry.status_code != 200 or dry.json().get("error_rows") != 0 or dry.json().get("total_rows") != size:
                        if dry.status_code >= 500: entry["core_500"] += 1
                        raise RuntimeError(f"dry-run HTTP {dry.status_code}")

                    started = time.perf_counter()
                    executed = client.post(f"{API}/api/v1/import/{job_id}/execute", headers=headers, json={**payload, "mode": "create_only", "dry_run": False})
                    entry["execute"] = round(time.perf_counter() - started, 3)
                    if executed.status_code != 200 or executed.json().get("job", {}).get("status") != "COMPLETED":
                        if executed.status_code >= 500: entry["core_500"] += 1
                        raise RuntimeError(f"execute HTTP {executed.status_code}")
                    if executed.json()["job"].get("success_rows") != size:
                        raise RuntimeError("execute row count mismatch")

                    post = client.get(f"{API}/health")
                    if post.status_code != 200:
                        raise RuntimeError("post-benchmark health failed")
                    post_body = post.json()
                    entry["process_restarted"] = post_body.get("process_started_at") != baseline["process_started_at"]
                    if entry["process_restarted"]:
                        raise RuntimeError("backend process restarted during benchmark")
                    entry["status"] = "PASS"
                except httpx.TimeoutException:
                    entry["timeout"] = 1
                    entry["safe_error"] = "Timeout during benchmark"
                    result["datasets"].append(entry)
                    raise
                except Exception as exc:
                    entry["safe_error"] = str(exc)[:200]
                    result["datasets"].append(entry)
                    raise
                result["datasets"].append(entry)

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
