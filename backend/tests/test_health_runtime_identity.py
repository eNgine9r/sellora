import pytest

from app.main import health, liveness, allowed_cors_origins


@pytest.mark.asyncio
async def test_health_exposes_safe_runtime_identity() -> None:
    payload = await health()

    assert payload["status"] == "ok"
    assert payload["runtime_commit"]
    assert payload["process_started_at"]
    assert "secret" not in payload
    assert "token" not in payload


@pytest.mark.asyncio
async def test_liveness_is_independent_of_database() -> None:
    assert (await liveness())["status"] == "ok"

def test_restricted_cors_rejects_wildcard(monkeypatch) -> None:
    monkeypatch.setenv("SELLORA_CORS_ALLOWED_ORIGINS", "*")
    with pytest.raises(ValueError, match="trusted origins"):
        allowed_cors_origins()
