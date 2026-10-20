"""Regression for Issue #266: sync DB/provider work must leave API loop responsive."""
import asyncio
import time
from types import SimpleNamespace

import pytest

from app.integrations.meta_instagram import runtime_worker


class Session:
    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def commit(self):
        pass

    def rollback(self):
        pass


class StalledService:
    def __init__(self, db):
        pass

    async def process_next(self):
        # Simulates a synchronous DB/socket operation inside the async service.
        time.sleep(0.4)
        return None


@pytest.mark.asyncio
@pytest.mark.parametrize("job", ["history", "extraction"])
async def test_stalled_background_job_keeps_api_loop_responsive(monkeypatch, job):
    monkeypatch.setattr(runtime_worker, "SessionLocal", Session)
    monkeypatch.setattr(runtime_worker, "InstagramHistorySyncService", StalledService)
    monkeypatch.setattr(runtime_worker, "DirectCustomerDataExtractionService", StalledService)
    monkeypatch.setattr(runtime_worker, "_customer_extraction_cooldown_active", lambda db: False)
    process = (runtime_worker.process_history_sync_job if job == "history"
               else runtime_worker.process_customer_data_extraction_job)
    started = time.monotonic()
    worker = asyncio.create_task(process())
    try:
        await asyncio.sleep(0.01)
        api_loop_latency = time.monotonic() - started
    finally:
        await worker
    assert api_loop_latency < 0.2, f"API event loop blocked for {api_loop_latency:.3f}s"
