import asyncio
import time
from types import SimpleNamespace

import httpx
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from starlette.requests import Request

from app.core import runtime_health
from app.main import app
from app.api.v1.session_auth import _origin


@pytest.mark.asyncio
async def test_async_liveness_does_not_need_database_or_anyio_worker_pool(monkeypatch):
    from app.database.session import engine
    def no_db(*args, **kwargs):
        raise AssertionError("Liveness must not touch DB")
    monkeypatch.setattr(engine, "connect", no_db)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://qa") as client:
        started = time.monotonic()
        response = await client.get("/health/live")
        assert response.status_code == 200
        assert time.monotonic() - started < 0.5


def test_stalled_worker_is_degraded_while_liveness_remains_ok(monkeypatch):
    monkeypatch.setenv("META_INSTAGRAM_WEBHOOK_WORKER_ENABLED", "true")
    monkeypatch.setattr(app.state, "instagram_webhook_worker_task", SimpleNamespace(done=lambda: False), raising=False)
    monkeypatch.setattr(runtime_health, "WORKER_STATE", {
        "phase": "history", "phase_started": time.monotonic() - 301,
    })
    client = TestClient(app)
    assert client.get("/health/live").status_code == 200
    response = client.get("/health/ready")
    assert response.status_code == 503
    assert response.json()["worker"]["stalled"] is True
    assert "sql" not in response.text.lower()
    assert "token" not in response.text.lower()


@pytest.mark.parametrize("origin", [None, "null", "https://untrusted.example",
    "https://sellora-web-staging.vercel.app.untrusted.example"])
def test_cookie_routes_reject_absent_or_untrusted_origins(origin):
    headers = [] if origin is None else [(b"origin", origin.encode())]
    request = Request({"type": "http", "headers": headers})
    with pytest.raises(HTTPException) as exc:
        _origin(request)
    assert exc.value.status_code == 403


def test_cookie_route_accepts_trusted_staging_origin():
    request = Request({"type": "http", "headers": [
        (b"origin", b"https://sellora-web-staging.vercel.app"),
    ]})
    _origin(request)
