from app.main import health


def test_health_exposes_safe_runtime_identity() -> None:
    payload = health()

    assert payload["status"] == "ok"
    assert payload["runtime_commit"]
    assert payload["process_started_at"]
    assert "secret" not in payload
    assert "token" not in payload
