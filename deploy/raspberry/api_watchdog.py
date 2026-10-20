"""Local journal alert and bounded same-image recovery. No data/credential access."""
from __future__ import annotations
import argparse
import fcntl
import json
from pathlib import Path
import re
import subprocess
import time
import urllib.request

CONTAINER = "sellora-rpi-backend-1"


def decide(state: dict, actual_image: str, healthy: bool, now: float) -> tuple[str, dict]:
    updated = dict(state)
    if actual_image != state["expected_image"]:
        return "BLOCKED_IMAGE_CHANGED", updated
    updated["failures"] = 0 if healthy else int(state.get("failures", 0)) + 1
    if healthy:
        return "HEALTHY", updated
    if updated["failures"] < 3 or now - float(state.get("last_restart", 0)) < 1800:
        return "ALERT_HTTP_UNRESPONSIVE", updated
    updated.update(failures=0, last_restart=now)
    return "RESTART_SAME_IMAGE", updated


def image_id() -> str:
    result = subprocess.run(["docker", "inspect", "--format", "{{.Image}}", CONTAINER],
                            capture_output=True, text=True, timeout=5, check=True)
    return result.stdout.strip()


def probe(path: str) -> bool:
    try:
        with urllib.request.urlopen("http://127.0.0.1:18000" + path, timeout=3) as response:
            return response.status == 200 and json.load(response).get("status") == "ok"
    except Exception:
        return False


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", type=Path, required=True)
    args = parser.parse_args()
    with args.plan.with_suffix(".lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return 0
        state = json.loads(args.plan.read_text())
        if not re.fullmatch(r"sha256:[0-9a-f]{64}", state.get("expected_image", "")):
            raise RuntimeError("INVALID_IMAGE_GUARD")
        observed = image_id()
        decision, updated = decide(state, observed, probe("/health"), time.time())
        if decision != "HEALTHY":
            print("SELLORA_API_WATCHDOG " + decision, flush=True)
        elif state.get("readiness_required") and not probe("/health/ready"):
            print("SELLORA_API_WATCHDOG ALERT_WORKER_DEGRADED", flush=True)
        temporary = args.plan.with_suffix(".tmp")
        temporary.write_text(json.dumps(updated) + "\n")
        temporary.replace(args.plan)
        if decision == "RESTART_SAME_IMAGE":
            # Recheck immediately before recovery; never deploy, retag or change env/schema.
            if image_id() != state["expected_image"]:
                print("SELLORA_API_WATCHDOG BLOCKED_IMAGE_CHANGED", flush=True)
                return 2
            subprocess.run(["docker", "restart", "--time", "15", CONTAINER],
                           capture_output=True, timeout=25, check=True)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        # Never print subprocess environment, URLs or raw exception strings.
        print("SELLORA_API_WATCHDOG ERROR_" + type(exc).__name__, flush=True)
        raise SystemExit(1)
