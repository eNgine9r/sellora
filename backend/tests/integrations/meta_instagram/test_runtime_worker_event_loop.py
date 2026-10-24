"""Regression coverage for FastAPI event-loop starvation by Meta worker DB I/O."""

import asyncio
import threading
import time

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.integrations.meta_instagram import runtime_worker


@pytest.mark.asyncio
async def test_async_db_jobs_run_on_an_independent_worker_loop():
    api_thread_id = threading.get_ident()

    async def synthetic_job():
        assert asyncio.get_running_loop().is_running()
        return str(threading.get_ident())

    result = await asyncio.to_thread(
        runtime_worker._run_async_db_job_in_worker_thread, synthetic_job
    )
    assert result != str(api_thread_id)


@pytest.mark.asyncio
async def test_health_remains_responsive_when_history_sync_db_blocks(monkeypatch):
    """A stalled synchronous DB call must never block the API event loop."""
    started = threading.Event()
    release = threading.Event()
    finished = threading.Event()
    stop = asyncio.Event()

    def fake_webhook_batch():
        return 0

    async def stalled_history():
        started.set()
        try:
            release.wait(timeout=2.0)
        finally:
            finished.set()
        return None

    async def idle_extraction():
        return None

    monkeypatch.setattr(runtime_worker, "process_webhook_batch", fake_webhook_batch)
    monkeypatch.setattr(runtime_worker, "process_history_sync_job", stalled_history)
    monkeypatch.setattr(runtime_worker, "process_customer_data_extraction_job", idle_extraction)
    monkeypatch.setattr(runtime_worker, "webhook_poll_seconds", lambda: 1.0)

    worker = asyncio.create_task(runtime_worker.run_instagram_webhook_worker(stop))
    try:
        assert await asyncio.to_thread(started.wait, 1.5)
        before = time.monotonic()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/health")
        duration = time.monotonic() - before
        assert response.status_code == 200
        assert response.json()["status"] == "ok"
        assert not finished.is_set(), (
            f"/health did not return until the synchronous DB task finished ({duration:.3f}s)"
        )
    finally:
        stop.set()
        release.set()
        await asyncio.wait_for(worker, timeout=3)
