import logging
import socket
import threading
import time

import httpx
import pytest
import uvicorn
from fastapi import FastAPI, Query

from app.middleware.meta_ads_oauth_redaction import MetaAdsOAuthQueryRedactionMiddleware


@pytest.mark.parametrize("suffix", ["", "/", "//"])
@pytest.mark.parametrize("query,expected", [
    ("code=synthetic-private-code&state=synthetic-private-state", 200),
    ("code=synthetic-private-code&state=" + "x" * 50, 422),
])
def test_actual_uvicorn_access_log_redacts_callback_query_even_validation_failure(caplog, query, expected, suffix):
    app = FastAPI()
    app.add_middleware(MetaAdsOAuthQueryRedactionMiddleware)
    seen = []

    @app.get("/api/v1/integrations/meta-ads/oauth/callback")
    def callback(code: str, state: str = Query(max_length=40)):
        seen.append((code, state))
        return {"ok": True}

    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(app, log_config=None, access_log=True, lifespan="off"))
    thread = threading.Thread(target=server.run, kwargs={"sockets": [sock]}, daemon=True)
    caplog.set_level(logging.INFO, logger="uvicorn.access")
    thread.start()
    try:
        for _ in range(200):
            if server.started:
                break
            time.sleep(0.01)
        assert server.started
        response = httpx.get(f"http://127.0.0.1:{port}/api/v1/integrations/meta-ads/oauth/callback{suffix}?{query}", timeout=3, follow_redirects=False)
        assert response.status_code == (307 if suffix else expected)
        if suffix:
            assert response.headers["location"].endswith("/oauth/callback?" + query)
        assert response.headers["cache-control"] == "no-store"
        assert response.headers["referrer-policy"] == "no-referrer"
    finally:
        server.should_exit = True
        thread.join(timeout=5)
        sock.close()
    assert not thread.is_alive()
    logs = [r.getMessage() for r in caplog.records if r.name == "uvicorn.access"]
    assert len(logs) == 1 and "/api/v1/integrations/meta-ads/oauth/callback" in logs[0]
    assert "synthetic-private-code" not in logs[0] and "state=" not in logs[0] and "code=" not in logs[0]
    if expected == 200 and not suffix:
        assert seen == [("synthetic-private-code", "synthetic-private-state")]


def test_production_app_installs_callback_redaction():
    from app.main import app
    assert any(m.cls is MetaAdsOAuthQueryRedactionMiddleware for m in app.user_middleware)
