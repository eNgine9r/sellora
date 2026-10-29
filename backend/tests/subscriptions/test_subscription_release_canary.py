"""Offline release-probe checks; the HTTP server and all credentials are synthetic."""
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from types import SimpleNamespace
from uuid import uuid4

import pytest

from scripts import verify_subscription_status as canary


@pytest.fixture
def target(monkeypatch):
    selected, foreign = str(uuid4()), str(uuid4())
    state = SimpleNamespace(
        payload={"workspace_id": selected, "status": "UNMANAGED", "plan_code": None,
                 "current_period_start": None, "current_period_end": None,
                 "cancel_at_period_end": False, "has_current_term": False, "enforcement_enabled": False},
        cache="no-store", requests=[], redirect=False, raw=None, allow_manager=False,
    )

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_GET(self):
            state.requests.append((self.command, self.path))
            token = self.headers.get("Authorization")
            workspace = self.headers.get("X-Workspace-ID")
            code = (401 if not token else 400 if not workspace else
                    200 if workspace == selected and (token == "Bearer synthetic-owner" or state.allow_manager) else 403)
            self.send_response(302 if state.redirect else code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Cache-Control", state.cache)
            if state.redirect:
                self.send_header("Location", "/redirect-must-not-be-followed?synthetic-secret")
            self.end_headers()
            self.wfile.write(state.raw if state.raw is not None else json.dumps(state.payload).encode())

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    for key, value in {"API_URL": f"http://127.0.0.1:{server.server_port}/api/v1",
                       "WORKSPACE_ID": selected, "FOREIGN_WORKSPACE_ID": foreign,
                       "OWNER_TOKEN": "synthetic-owner", "MANAGER_TOKEN": "synthetic-manager",
                       "ANALYST_TOKEN": "synthetic-analyst"}.items():
        monkeypatch.setenv(canary.PREFIX + key, value)
    try:
        yield state
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


@pytest.mark.parametrize("status", canary.STATUSES)
def test_status_contract_and_denials_use_only_get(target, status):
    target.payload.update(status=status, has_current_term=status in {"ACTIVE", "TRIALING"})
    result = canary.run(status, require_denials=True)
    assert result["result"] == "PASS" and result["skipped"] == []
    assert "foreign_workspace_denied" in result["checks"]
    assert len(target.requests) == 6
    assert set(target.requests) == {("GET", canary.PATH)}


@pytest.mark.parametrize("change,check", [
    ({"workspace_id": str(uuid4())}, "workspace_match"),
    ({"status": "ACTIVE"}, "expected_status"),
    ({"enforcement_enabled": True}, "enforcement_disabled"),
    ({"has_current_term": True}, "current_term"),
    ({"plan_code": "unexpected-enrollment"}, "no_automatic_enrollment"),
])
def test_contract_drift_fails_without_logging_body(target, capsys, change, check):
    target.payload.update(change, private="synthetic-private-body")
    assert canary.main([]) == 1
    assert json.loads(capsys.readouterr().out) == {"result": "FAIL", "check": check}


def test_no_store_is_required(target):
    target.cache = "private, no-cache"
    with pytest.raises(canary.CanaryError, match="^cache_no_store$"):
        canary.run("UNMANAGED", False)


def test_redirect_is_not_followed_or_logged(target, capsys):
    target.redirect = True
    assert canary.main([]) == 1
    assert json.loads(capsys.readouterr().out) == {"result": "FAIL", "check": "owner_http_302"}
    assert target.requests == [("GET", canary.PATH)]


@pytest.mark.parametrize("raw,check", [(b"synthetic-secret-not-json", "owner_invalid_json"),
                                      (b"x" * 16385, "owner_body_too_large")])
def test_invalid_body_is_not_logged(target, capsys, raw, check):
    target.raw = raw
    assert canary.main([]) == 1
    assert json.loads(capsys.readouterr().out) == {"result": "FAIL", "check": check}


@pytest.mark.parametrize("url", ["https://synthetic-secret@example.test", "https://example.test?token=synthetic-secret",
                               "https://example.test/#synthetic-secret", "http://example.test",
                               "https://example.test/other", "https://example.test:bad", ""])
def test_unsafe_target_fails_before_request(url):
    with pytest.raises(canary.CanaryError, match="^invalid_api_url$"):
        canary.endpoint(url)


def test_optional_denials_are_explicit_and_strict_mode_requires_them(target, monkeypatch):
    monkeypatch.delenv(canary.PREFIX + "MANAGER_TOKEN")
    monkeypatch.delenv(canary.PREFIX + "ANALYST_TOKEN")
    monkeypatch.delenv(canary.PREFIX + "FOREIGN_WORKSPACE_ID")
    with pytest.raises(canary.CanaryError, match="^missing_denial_environment$"):
        canary.run("UNMANAGED", True)
    assert target.requests == []
    assert canary.run("UNMANAGED", False)["skipped"] == ["manager_denied", "analyst_denied", "foreign_workspace_denied"]


def test_role_access_regression_is_failure(target):
    target.allow_manager = True
    with pytest.raises(canary.CanaryError, match="^manager_denied_http_200$"):
        canary.run("UNMANAGED", True)


def test_transport_error_text_is_not_logged(target, monkeypatch, capsys):
    def fail(*args, **kwargs):
        raise OSError("synthetic-secret-from-transport")
    monkeypatch.setattr(canary, "build_opener", lambda *args: SimpleNamespace(open=fail))
    assert canary.main([]) == 1
    assert json.loads(capsys.readouterr().out) == {"result": "FAIL", "check": "http_request_failed"}


def test_bad_environment_is_not_logged(target, monkeypatch, capsys):
    monkeypatch.setenv(canary.PREFIX + "OWNER_TOKEN", "synthetic-secret\ninjected-header")
    assert canary.main([]) == 1
    assert json.loads(capsys.readouterr().out) == {"result": "FAIL", "check": "invalid_token"}
    assert target.requests == []
