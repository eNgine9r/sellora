"""No real credentials or customer data: isolated in-memory auth-throttle tests."""

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest

import app.auth.login_throttle as throttle_module


class FakeResult:
    def __init__(self, row):
        self.row = row

    def first(self):
        return self.row


class FakeDb:
    def __init__(self):
        self.counters = {}
        self.commits = 0

    def execute(self, stmt, params):
        statement = str(stmt).upper().strip()
        key = params["key"]
        if statement.startswith("SELECT"):
            count, expiry = self.counters[key] if key in self.counters else (0, None)
            return FakeResult(
                SimpleNamespace(failure_count=count, reset_at=expiry)
                if expiry else None
            )
        if statement.startswith("INSERT"):
            current, expiry = self.counters.get(key, (0, None))
            now = params["now"]
            self.counters[key] = (
                1 if expiry is None or expiry <= now else current + 1,
                params["expiry"] if expiry is None or expiry <= now else expiry,
            )
            return FakeResult(None)
        if statement.startswith("DELETE"):
            self.counters.pop(key, None)
            return FakeResult(None)
        raise AssertionError("Unexpected SQL operation")

    def commit(self):
        self.commits += 1


@pytest.fixture
def enabled(monkeypatch):
    settings = SimpleNamespace(
        jwt_secret="synthetic-strong-test-secret-never-deploy",
        login_rate_limit_enabled=True,
        login_rate_limit_max_failures=3,
        login_rate_limit_window_seconds=900,
    )
    monkeypatch.setattr(throttle_module, "get_settings", lambda: settings)
    return settings


def test_three_failures_are_shared_and_fourth_attempt_is_rate_limited(enabled):
    db = FakeDb()
    a = throttle_module.LoginThrottle(db)
    for _ in range(3):
        a.check("Shop@Example.com")
        a.failed("SHOP@example.com")

    # Separate service object sees the same persisted counter.
    b = throttle_module.LoginThrottle(db)
    with pytest.raises(throttle_module.LoginThrottled) as exc:
        b.check("shop@example.com")
    assert 1 <= exc.value.retry_after_seconds <= 900
    assert len(db.counters) == 1
    assert "shop@example.com" not in repr(db.counters)
    assert db.commits == 3


def test_success_clears_failure_counter(enabled):
    db = FakeDb()
    guard = throttle_module.LoginThrottle(db)
    guard.failed("shop@example.com")
    guard.succeeded("shop@example.com")
    guard.check("shop@example.com")
    assert db.counters == {}


def test_expired_window_resets_counter(enabled):
    db = FakeDb()
    guard = throttle_module.LoginThrottle(db)
    for _ in range(3):
        guard.failed("shop@example.com")
    key = guard._key("shop@example.com")
    db.counters[key] = (3, datetime.now(UTC) - timedelta(seconds=1))
    guard.check("shop@example.com")
    guard.failed("shop@example.com")
    assert db.counters[key][0] == 1


def test_rate_limiter_disabled_has_no_side_effects(enabled):
    enabled.login_rate_limit_enabled = False
    db = FakeDb()
    guard = throttle_module.LoginThrottle(db)
    guard.check("shop@example.com")
    guard.failed("shop@example.com")
    guard.succeeded("shop@example.com")
    assert db.counters == {} and db.commits == 0


def test_fingerprint_is_hmac_and_normalized(enabled):
    guard = throttle_module.LoginThrottle(FakeDb())
    key = guard._key(" Shop@Example.COM ")
    assert len(key) == 64
    assert key == guard._key("shop@example.com")
    assert "shop" not in key and "@" not in key
    assert key != guard._key("different@example.com")


def test_login_endpoint_returns_429_without_verifying_password(enabled, monkeypatch):
    from app.api.v1.auth import login
    from app.schemas.auth import LoginRequest
    from fastapi import HTTPException

    db = FakeDb()
    guard = throttle_module.LoginThrottle(db)
    for _ in range(3):
        guard.failed("test@example.com")
    with pytest.raises(HTTPException) as exc:
        login(LoginRequest(email="test@example.com", password="invalid"), db=db)
    assert exc.value.status_code == 429
    assert int(exc.value.headers["Retry-After"]) >= 1
