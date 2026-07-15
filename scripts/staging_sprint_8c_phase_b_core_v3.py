#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import httpx

V2_PATH = Path(__file__).with_name("staging_sprint_8c_phase_b_core_v2.py")
spec = importlib.util.spec_from_file_location("sellora_sprint_8c_phase_b_core_v2", V2_PATH)
if spec is None or spec.loader is None:
    raise SystemExit("Unable to load Sprint 8C Phase B v2 runner")
v2 = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = v2
spec.loader.exec_module(v2)

_original_request_retry = v2.base.request_retry


def bounded_request_retry(operation, attempts: int = 3):
    """Keep staging failures bounded instead of waiting on six long reads."""

    return _original_request_retry(operation, attempts=min(attempts, 3))


v2.base.request_retry = bounded_request_retry


def parse_runtime_timestamp(value: object) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


class StatelessHttpClient:
    """Create one isolated connection per request, matching the green readiness probe."""

    def __init__(self) -> None:
        self.timeout = httpx.Timeout(connect=15, read=30, write=60, pool=15)

    def request(self, method: str, url: str, **kwargs) -> httpx.Response:
        path = httpx.URL(url).path
        print(f"HTTP START {method.upper()} {path}", flush=True)
        with httpx.Client(
            timeout=self.timeout,
            follow_redirects=True,
            headers={"Connection": "close", "Cache-Control": "no-cache"},
        ) as client:
            response = client.request(method, url, **kwargs)
        print(f"HTTP DONE {method.upper()} {path} {response.status_code}", flush=True)
        return response

    def get(self, url: str, **kwargs) -> httpx.Response:
        return self.request("GET", url, **kwargs)

    def post(self, url: str, **kwargs) -> httpx.Response:
        return self.request("POST", url, **kwargs)

    def close(self) -> None:
        return None


class PhaseBClosureV3(v2.PhaseBClosureV2):
    """Require the approved runtime and keep every staging request isolated."""

    def __init__(self) -> None:
        super().__init__()
        old_client = self.client.client
        old_client.close()
        self.client.client = StatelessHttpClient()

    def check(self, name: str, condition: bool, detail: str = "") -> None:
        print(
            json.dumps(
                {
                    "check": name,
                    "status": "PASS" if condition else "FAIL",
                    "detail": detail[:200],
                },
                ensure_ascii=False,
            ),
            flush=True,
        )
        return super().check(name, condition, detail)

    def wait_runtime(self) -> None:
        allowed = {
            value.strip().lower()
            for value in os.getenv("EXPECTED_RUNTIME_COMMITS", "").split(",")
            if value.strip()
        }
        if not allowed:
            raise RuntimeError("EXPECTED_RUNTIME_COMMITS must contain an approved main commit")
        rejected = {
            value.strip().lower()
            for value in os.getenv("REJECTED_RUNTIME_COMMITS", "").split(",")
            if value.strip()
        }
        minimum_started_at = parse_runtime_timestamp(os.getenv("MIN_PROCESS_STARTED_AT"))
        if minimum_started_at is None:
            raise RuntimeError("MIN_PROCESS_STARTED_AT must be a valid ISO timestamp")

        deadline = time.monotonic() + 25 * 60
        last = "unavailable"
        rejected_observations = 0
        while time.monotonic() < deadline:
            try:
                response = self.client.get(f"{v2.base.API}/health")
                if response.status_code == 200:
                    body = response.json()
                    last = str(body.get("runtime_commit") or "legacy").lower()
                    process_started_at = parse_runtime_timestamp(body.get("process_started_at"))
                    rejected_match = next(
                        (commit for commit in rejected if last.startswith(commit[:12])),
                        None,
                    )
                    allowed_match = next(
                        (commit for commit in allowed if last.startswith(commit[:12])),
                        None,
                    )
                    post_fix_process = bool(
                        process_started_at
                        and process_started_at >= minimum_started_at
                    )
                    if rejected_match:
                        rejected_observations += 1
                        if rejected_observations >= 3:
                            self.result["runtime"] = {
                                "runtime_commit": last,
                                "process_started_at": body.get("process_started_at"),
                                "expected_commits": sorted(allowed),
                                "rejected_baselines": sorted(rejected),
                            }
                            expected = ",".join(sorted(commit[:12] for commit in allowed))
                            raise RuntimeError(
                                f"STALE_RUNTIME: Render is {last[:12]}; deploy expected main commit {expected}"
                            )
                    else:
                        rejected_observations = 0
                    if allowed_match and not rejected_match and post_fix_process:
                        self.result["runtime"] = {
                            "runtime_commit": last,
                            "process_started_at": body["process_started_at"],
                            "minimum_process_started_at": minimum_started_at.isoformat(),
                            "allowed_main_commits": sorted(allowed),
                            "matched_known_commit": allowed_match,
                            "rejected_baselines": sorted(rejected),
                        }
                        self.check("new identified Render process", True)
                        self.check(
                            "restart commit boundary",
                            True,
                            f"matched {allowed_match[:12]}",
                        )
                        return
            except RuntimeError:
                raise
            except Exception:
                last = "health-unavailable"
            time.sleep(15)
        raise RuntimeError(f"Expected approved runtime not observed; last marker {last[:20]}")


if __name__ == "__main__":
    v2.base.OUT.parent.mkdir(parents=True, exist_ok=True)
    closure = PhaseBClosureV3()
    try:
        exit_code = closure.run()
    except Exception as exc:
        closure.result["safe_error"] = str(exc)[:400]
        exit_code = 1
    finally:
        closure.close()
        v2.base.OUT.write_text(
            json.dumps(closure.result, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        print(json.dumps(closure.result, indent=2, ensure_ascii=False))
    raise SystemExit(exit_code)
