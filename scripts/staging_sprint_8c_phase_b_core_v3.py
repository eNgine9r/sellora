#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import os
import sys
import time
from pathlib import Path

V2_PATH = Path(__file__).with_name("staging_sprint_8c_phase_b_core_v2.py")
spec = importlib.util.spec_from_file_location("sellora_sprint_8c_phase_b_core_v2", V2_PATH)
if spec is None or spec.loader is None:
    raise SystemExit("Unable to load Sprint 8C Phase B v2 runner")
v2 = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = v2
spec.loader.exec_module(v2)


class PhaseBClosureV3(v2.PhaseBClosureV2):
    """Accept any explicitly allowed main runtime that contains the merged fix."""

    def wait_runtime(self) -> None:
        configured = os.getenv("EXPECTED_RUNTIME_COMMITS", "").strip()
        allowed = {
            value.strip().lower()
            for value in configured.split(",")
            if value.strip()
        }
        if not allowed:
            allowed = {str(v2.base.EXPECTED_COMMIT).lower()}

        deadline = time.monotonic() + 25 * 60
        last = "unavailable"
        while time.monotonic() < deadline:
            try:
                response = self.client.get(f"{v2.base.API}/health")
                if response.status_code == 200:
                    body = response.json()
                    last = str(body.get("runtime_commit") or "legacy").lower()
                    matched = next(
                        (commit for commit in allowed if last.startswith(commit[:12])),
                        None,
                    )
                    if matched and body.get("process_started_at"):
                        self.result["runtime"] = {
                            "runtime_commit": last,
                            "process_started_at": body["process_started_at"],
                            "allowed_main_commits": sorted(allowed),
                        }
                        self.check("new identified Render process", True)
                        self.check("restart commit boundary", True, f"matched {matched[:12]}")
                        return
            except Exception:
                last = "health-unavailable"
            time.sleep(15)
        raise RuntimeError(f"Expected runtime not observed; last marker {last[:20]}")


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
