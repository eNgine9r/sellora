#!/usr/bin/env python3
from __future__ import annotations

import os
import time

import httpx

from staging_sprint_8c_phase_a import main


def wait_for_runtime() -> None:
    api = os.environ["STAGING_API_URL"].rstrip("/")
    expected = os.environ["EXPECTED_RUNTIME_COMMIT"].strip()
    deadline = time.monotonic() + 15 * 60
    last_seen = "unavailable"
    timeout = httpx.Timeout(connect=30.0, read=90.0, write=30.0, pool=30.0)
    with httpx.Client(timeout=timeout, follow_redirects=True) as client:
        while time.monotonic() < deadline:
            try:
                response = client.get(f"{api}/health")
                if response.status_code == 200:
                    payload = response.json()
                    last_seen = str(payload.get("runtime_commit") or "legacy-health")
                    if last_seen.startswith(expected[:12]) and payload.get("process_started_at"):
                        print(f"Expected runtime deployed: {last_seen[:12]}")
                        return
            except Exception:
                last_seen = "health-unavailable"
            time.sleep(15)
    raise RuntimeError(f"Expected Render runtime was not observed; last safe marker: {last_seen[:12]}")


if __name__ == "__main__":
    wait_for_runtime()
    raise SystemExit(main())
