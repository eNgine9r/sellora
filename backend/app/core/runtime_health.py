"""Bounded, content-free process and background-worker telemetry."""
from collections.abc import Callable

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


class RuntimePressureMonitor:
    """Sample pressure independently of probe traffic; never acquire a DB slot.

    Short bursts reset immediately. Ten seconds of saturation or loop lag are
    degraded. A stopped sampler is visible after five seconds.
    """
    def __init__(self) -> None:
        self._since: dict[str, float] = {}
        self._sampled_at: float | None = None

    def observe(
        self, lag_seconds: float, *, checked_out: int | None = None,
        capacity: int | None = None, now: float | None = None,
    ) -> None:
        now = time.monotonic() if now is None else now
        self._sampled_at = now
        signals = {
            "event_loop_lag": lag_seconds >= 1.0,
            "db_pool_saturated": bool(capacity and capacity > 0 and checked_out is not None and checked_out >= capacity),
        }
        for name, active in signals.items():
            if active:
                # A single long scheduling pause already represents sustained lag.
                onset = now - lag_seconds if name == "event_loop_lag" else now
                self._since.setdefault(name, onset)
            else:
                self._since.pop(name, None)

    def snapshot(self, *, now: float | None = None) -> dict[str, object]:
        now = time.monotonic() if now is None else now
        reasons = [name for name, since in self._since.items() if now - since >= 10.0]
        sample_age = None if self._sampled_at is None else max(0.0, now - self._sampled_at)
        if sample_age is not None and sample_age > 5.0:
            reasons.append("runtime_monitor_stale")
        return {"reasons": reasons, "sample_age_seconds": None if sample_age is None else round(sample_age, 3)}


runtime_pressure = RuntimePressureMonitor()


async def monitor_event_loop(pool_snapshot: Callable[[], dict[str, int | None]] | None = None) -> None:
    # This process-local sampler doesn't query PostgreSQL or depend on AnyIO's
    # request thread pool, so saturation cannot consume the health-check budget.
    runtime_pressure.observe(0.0)
    while True:
        started = time.monotonic()
        await asyncio.sleep(1)
        lag = max(0.0, time.monotonic() - started - 1)
        LOOP_STATE["lag_seconds"] = round(lag, 3)
        pool = pool_snapshot() if pool_snapshot is not None else {}
        runtime_pressure.observe(lag, checked_out=pool.get("checked_out"), capacity=pool.get("capacity"))


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
