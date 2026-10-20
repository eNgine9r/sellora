"""Regression checks for credentialed CORS on Sellora's public API."""
import pytest

from app import main as api_main


def test_production_uses_staging_origin_instead_of_wildcard(monkeypatch):
    monkeypatch.setattr(api_main.settings, "environment", "production")
    monkeypatch.delenv("SELLORA_CORS_ALLOWED_ORIGINS", raising=False)
    assert api_main.allowed_cors_origins() == ["https://sellora-web-staging.vercel.app"]


def test_explicit_trusted_origins_only(monkeypatch):
    monkeypatch.setattr(api_main.settings, "environment", "production")
    monkeypatch.setenv(
        "SELLORA_CORS_ALLOWED_ORIGINS",
        "https://sellora-web-staging.vercel.app, https://sellora.example.com",
    )
    assert api_main.allowed_cors_origins() == [
        "https://sellora-web-staging.vercel.app", "https://sellora.example.com"
    ]


@pytest.mark.parametrize("origin", [
    "*",
    "https://*.vercel.app",
    "http://sellora-web-staging.vercel.app",
    "https://sellora-web-staging.vercel.app/evil",
    "https://user@somewhere.example",
    "javascript:alert(1)",
])
def test_rejects_insecure_or_ambiguous_production_origin(monkeypatch, origin):
    monkeypatch.setattr(api_main.settings, "environment", "production")
    monkeypatch.setenv("SELLORA_CORS_ALLOWED_ORIGINS", origin)
    with pytest.raises(ValueError, match="trusted origins"):
        api_main.allowed_cors_origins()


def test_dev_localhost_allowed_only_outside_production(monkeypatch):
    monkeypatch.setattr(api_main.settings, "environment", "development")
    monkeypatch.delenv("SELLORA_CORS_ALLOWED_ORIGINS", raising=False)
    origins = api_main.allowed_cors_origins()
    assert "http://localhost:3000" in origins
    monkeypatch.setattr(api_main.settings, "environment", "production")
    assert "http://localhost:3000" not in api_main.allowed_cors_origins()
