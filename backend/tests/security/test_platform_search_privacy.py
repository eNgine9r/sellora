import logging
import socket
import threading
import time

import httpx
import uvicorn

from app.database.session import get_db
from app.main import app

DIRECTORY = "/api/v1/platform-admin/workspaces"
MARKER = "synthetic-private-search-marker"


def test_directory_errors_document_the_redacted_shape():
    paths = app.openapi()["paths"]
    for path, method in ((DIRECTORY, "get"), (DIRECTORY + "/search", "post")):
        schema = paths[path][method]["responses"]["422"]["content"]["application/json"]["schema"]
        assert schema["$ref"] == "#/components/schemas/PlatformWorkspaceRequestError"


def test_directory_legacy_queries_and_validation_do_not_echo_filters_or_reach_access_logs(caplog):
    # Bypass authentication only for this transport test. Real RBAC is covered in PostgreSQL.
    from app.api.v1.router import api_router

    def platform_routes(router):
        for route in router.routes:
            if hasattr(route, "dependant"):
                yield route
            elif hasattr(route, "original_router"):
                yield from platform_routes(route.original_router)

    dependencies = [
        item.call for route in platform_routes(api_router)
        if route.path in ("/platform-admin/workspaces", "/platform-admin/workspaces/search")
        for item in route.dependant.dependencies
        if getattr(item.call, "platform_capability", None) == "workspaces.read"
    ]
    assert len(dependencies) == 2
    previous = dict(app.dependency_overrides)
    app.dependency_overrides[get_db] = lambda: None
    app.dependency_overrides.update({dependency: lambda: None for dependency in dependencies})

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
        with httpx.Client(base_url=f"http://127.0.0.1:{port}", trust_env=False) as browser:
            legacy = browser.get(DIRECTORY, params={"q": MARKER, "cursor": MARKER})
            alias = browser.get(DIRECTORY + "/", params={"q": MARKER})
            malformed = browser.post(DIRECTORY + "/search", json={"q": {"value": MARKER}})
            cursor = browser.post(DIRECTORY + "/search", json={"cursor": MARKER * 40})
            query = browser.post(DIRECTORY + "/search", params={"q": MARKER}, json={})
            post_alias = browser.post(DIRECTORY + "/search/", params={"cursor": MARKER}, json={})
            invalid_json = browser.post(
                DIRECTORY + "/search", content=f'{{"q":"{MARKER}"', headers={"Content-Type": "application/json"},
            )
            for response in (legacy, alias, malformed, cursor, query, post_alias, invalid_json):
                assert response.status_code == 422
                assert response.headers["cache-control"] == "private, no-store"
                assert MARKER not in response.text
    finally:
        server.should_exit = True
        thread.join(timeout=5)
        sock.close()
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous)
    assert not thread.is_alive()
    logs = [record.getMessage() for record in caplog.records if record.name == "uvicorn.access"]
    assert len(logs) == 7 and all(DIRECTORY in line for line in logs)
    assert all(MARKER not in line and "?" not in line for line in logs)
