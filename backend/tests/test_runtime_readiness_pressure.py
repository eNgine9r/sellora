"""Readiness must report sustained pressure without using a DB connection."""
import asyncio
import threading
from types import SimpleNamespace

import httpx
import pytest
from fastapi import Response
from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool

from app import main
from app.core import runtime_health
from app.integrations.meta_instagram import runtime_worker


def monitor():
    return runtime_health.RuntimePressureMonitor()


def test_pool_pressure_requires_continuous_grace_and_recovers():
    state = monitor()
    state.observe(0.02, checked_out=10, capacity=10, now=100)
    state.observe(0.02, checked_out=10, capacity=10, now=109)
    assert state.snapshot(now=109)["reasons"] == []
    state.observe(0.02, checked_out=10, capacity=10, now=110)
    assert state.snapshot(now=110)["reasons"] == ["db_pool_saturated"]
    state.observe(0.02, checked_out=9, capacity=10, now=111)
    assert state.snapshot(now=111)["reasons"] == []


def test_brief_saturation_does_not_accumulate_across_recovery():
    state = monitor()
    for start in (0, 20, 40):
        state.observe(0, checked_out=10, capacity=10, now=start)
        state.observe(0, checked_out=0, capacity=10, now=start+9)
        assert state.snapshot(now=start+9)["reasons"] == []


def test_event_loop_sustained_lag_and_recovery():
    state = monitor()
    state.observe(1.1, now=100)
    state.observe(1.1, now=110)
    assert state.snapshot(now=110)["reasons"] == ["event_loop_lag"]
    state.observe(0.01, now=111)
    assert state.snapshot(now=111)["reasons"] == []


def test_single_long_event_loop_stall_reports_immediately():
    state = monitor()
    state.observe(12, now=100)
    assert state.snapshot(now=100)["reasons"] == ["event_loop_lag"]


def test_stale_monitor_and_unknown_pool():
    state = monitor()
    state.observe(0, now=100)
    assert state.snapshot(now=100)["reasons"] == []
    assert state.snapshot(now=106)["reasons"] == ["runtime_monitor_stale"]
    state.observe(0, now=106)
    assert state.snapshot(now=106)["reasons"] == []


@pytest.mark.parametrize("capacity", [None, 0, -1])
def test_unknown_or_unbounded_pool_is_not_marked_saturated(capacity):
    state = monitor()
    state.observe(0, checked_out=10, capacity=capacity, now=100)
    state.observe(0, checked_out=10, capacity=capacity, now=120)
    assert state.snapshot(now=120)["reasons"] == []


@pytest.mark.asyncio
async def test_readiness_degrades_without_affecting_liveness(monkeypatch):
    state = monitor()
    state.observe(0, checked_out=10, capacity=10, now=100)
    state.observe(0, checked_out=10, capacity=10, now=110)
    monkeypatch.setattr(main, "runtime_pressure", SimpleNamespace(snapshot=lambda: state.snapshot(now=110)))
    monkeypatch.setattr(main, "webhook_worker_enabled", lambda: False)
    response = Response()
    payload = await main.readiness(response)
    assert response.status_code == 503
    assert payload["degraded_reasons"] == ["db_pool_saturated"]
    assert await main.liveness() == {"status": "ok"}


@pytest.mark.asyncio
async def test_required_missing_worker_still_degrades(monkeypatch):
    monkeypatch.setattr(main, "runtime_pressure", monitor())
    monkeypatch.setattr(main, "webhook_worker_enabled", lambda: True)
    monkeypatch.setattr(main, "settings", SimpleNamespace(meta_instagram_webhook_processing_enabled=True))
    monkeypatch.setattr(main.app.state, "instagram_webhook_worker_task", None, raising=False)
    response = Response()
    payload = await main.readiness(response)
    assert response.status_code == 503
    assert "webhook_worker_unavailable" in payload["degraded_reasons"]


@pytest.mark.asyncio
async def test_actual_queue_pool_saturation_does_not_block_health_http(monkeypatch):
    engine = create_engine("sqlite://", poolclass=QueuePool, pool_size=1, max_overflow=0, pool_timeout=0.05)
    state = monitor()
    monkeypatch.setattr(main, "runtime_pressure", SimpleNamespace(snapshot=lambda: state.snapshot(now=110)))
    monkeypatch.setattr(main, "webhook_worker_enabled", lambda: False)
    monkeypatch.setattr(main, "engine", engine)
    with engine.connect():
        state.observe(0, checked_out=engine.pool.checkedout(), capacity=1, now=100)
        state.observe(0, checked_out=engine.pool.checkedout(), capacity=1, now=110)
        # Any readiness DB checkout would time out while the only slot is held.
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=main.app), base_url="http://test") as client:
            live, ready = await asyncio.wait_for(asyncio.gather(client.get("/health/live"), client.get("/health/ready")), timeout=1)
        assert live.status_code == 200
        assert ready.status_code == 503
        assert ready.json()["degraded_reasons"] == ["db_pool_saturated"]
    state.observe(0, checked_out=0, capacity=1, now=110)
    response = Response()
    assert (await main.readiness(response))["status"] == "ok"
    engine.dispose()


@pytest.mark.asyncio
@pytest.mark.parametrize("job", ["history", "extraction", "webhook"])
async def test_blocked_worker_jobs_leave_http_responsive(monkeypatch, job):
    entered, release = threading.Event(), threading.Event()
    def blocked():
        entered.set()
        assert release.wait(timeout=3)
        return None
    monkeypatch.setattr(main, "runtime_pressure", monitor())
    monkeypatch.setattr(main, "webhook_worker_enabled", lambda: False)
    for name in ("process_webhook_batch", "_process_history_sync_job", "_process_customer_data_extraction_job"):
        monkeypatch.setattr(runtime_worker, name, lambda: None)
    monkeypatch.setenv("DIRECT_MEDIA_CACHE_ENABLED", "false")
    target = {"webhook":"process_webhook_batch", "history":"_process_history_sync_job", "extraction":"_process_customer_data_extraction_job"}[job]
    monkeypatch.setattr(runtime_worker, target, blocked)
    stop = asyncio.Event()
    task = asyncio.create_task(runtime_worker.run_instagram_webhook_worker(stop))
    try:
        assert await asyncio.to_thread(entered.wait, 1)
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=main.app), base_url="http://test") as client:
            responses = await asyncio.wait_for(asyncio.gather(client.get("/health/live"), client.get("/health/ready")), timeout=1)
        assert all(r.status_code == 200 for r in responses)
        assert not task.done()
    finally:
        release.set()
        stop.set()
        await asyncio.wait_for(task, timeout=2)
