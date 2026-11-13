import secrets

import pytest
from pydantic import ValidationError

from app.core.config import Settings


@pytest.fixture(autouse=True)
def clear_signing_environment(monkeypatch):
    for name in ("JWT_SECRET", "jwt_secret", "JWT_ALGORITHM", "jwt_algorithm", "SELLORA_PLATFORM_ADMIN_ENABLED"):
        monkeypatch.delenv(name, raising=False)


def test_platform_admin_rejects_unconfigured_key_but_disabled_platform_still_loads():
    assert not Settings(_env_file=None).platform_admin_enabled
    with pytest.raises(ValidationError, match="Platform Admin requires a non-placeholder JWT_SECRET"):
        Settings(_env_file=None, environment="production", platform_admin_enabled=True)


@pytest.mark.parametrize("value", ["", "short-secret-marker", "replace-with-a-long-random-jwt-secret"])
def test_platform_admin_rejects_inadequate_keys_without_echoing_input(value):
    with pytest.raises(ValidationError, match="JWT_SECRET") as error:
        Settings(_env_file=None, platform_admin_enabled=True, jwt_secret=value)
    if value:
        assert value not in str(error.value)


@pytest.mark.parametrize(("algorithm", "minimum"), [("HS256", 32), ("HS384", 48), ("HS512", 64)])
def test_platform_admin_accepts_explicit_signing_key_for_each_supported_hmac(algorithm, minimum):
    key = secrets.token_urlsafe(64)[:minimum]
    settings = Settings(_env_file=None, platform_admin_enabled=True, jwt_algorithm=algorithm, jwt_secret=key)
    assert settings.platform_admin_enabled and settings.jwt_secret == key


def test_platform_admin_enforces_algorithm_key_length():
    with pytest.raises(ValidationError, match="at least 64 bytes"):
        Settings(_env_file=None, platform_admin_enabled=True, jwt_algorithm="HS512", jwt_secret=secrets.token_urlsafe(32))


def test_platform_mfa_is_mandatory_for_enabled_production_platform():
    settings = Settings(
        _env_file=None, environment="production", platform_admin_enabled=True,
        platform_admin_mfa_required=False, jwt_secret=secrets.token_urlsafe(48),
    )
    assert settings.platform_admin_requires_mfa
    assert not Settings(_env_file=None, environment="development").platform_admin_requires_mfa


def test_totp_matches_rfc6238_sha1_vector_and_rejects_replay():
    from datetime import UTC, datetime

    from app.services.platform_mfa_service import matching_step, totp_code

    seed = b"12345678901234567890"
    now = datetime.fromtimestamp(59, UTC)
    assert totp_code(seed, 1) == "287082"
    assert matching_step(seed, "287082", now) == 1
    assert matching_step(seed, "287082", now, after=1) is None
    assert matching_step(seed, "２８７０８２", now) is None
