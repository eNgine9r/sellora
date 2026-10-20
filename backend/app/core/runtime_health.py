"""Bounded, content-free process and background-worker telemetry."""
import asyncio
import time
from threading import Lock
from datetime import UTC, datetime

WORKER_STATE: dict[str, object] = {}
LOOP_STATE: dict[str, float] = {"lag_seconds": 0.0}


def worker_phase(name: str) -> None:
    WORKER_STATE.update(phase=name, phase_started=time.monotonic())


def worker_finished(error: Exception | None = None) -> None:
    phase = str(WORKER_STATE.get("phase", "idle"))
    duration = max(0.0, time.monotonic() - float(WORKER_STATE.get("phase_started", time.monotonic())))
    WORKER_STATE.update(phase="idle", phase_started=time.monotonic(),
                        last_job=phase, last_duration_seconds=round(duration, 3),
                        last_completed_at=datetime.now(UTC).isoformat(),
                        last_error_type=type(error).__name__ if error else None)
    if error:
        WORKER_STATE["failure_count"] = int(WORKER_STATE.get("failure_count", 0)) + 1


def worker_snapshot() -> dict[str, object]:
    age = max(0.0, time.monotonic() - float(WORKER_STATE.get("phase_started", time.monotonic())))
    return {key: value for key, value in WORKER_STATE.items() if key != "phase_started"} | {
        "phase_elapsed_seconds": round(age, 3),
        "stalled": WORKER_STATE.get("phase", "idle") != "idle" and age > 300,
    }


async def monitor_event_loop() -> None:
    while True:
        started = time.monotonic()
        await asyncio.sleep(1)
        LOOP_STATE["lag_seconds"] = round(max(0.0, time.monotonic() - started - 1), 3)


_DB_LOCK = Lock()
_DB_STATE: dict[str, object] = {"operations": 0, "last_seconds": 0.0, "max_seconds": 0.0}


def record_db_operation(seconds: float) -> None:
    with _DB_LOCK:
        _DB_STATE["operations"] = int(_DB_STATE["operations"]) + 1
        _DB_STATE["last_seconds"] = round(seconds, 3)
        _DB_STATE["max_seconds"] = round(max(float(_DB_STATE["max_seconds"]), seconds), 3)


def db_snapshot() -> dict[str, object]:
    with _DB_LOCK:
        return dict(_DB_STATE)
