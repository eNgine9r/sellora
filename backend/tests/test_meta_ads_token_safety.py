from __future__ import annotations

import pytest

from app.integrations.meta_ads.token_safety import TokenSafetyError, assert_no_raw_token_in_response, mask_token, redact_secret_fields, safe_token_fingerprint


def _synthetic_secret() -> str:
    return "mock_" + "token_" + "1234567890abcd"


def test_mask_token_never_returns_raw_value() -> None:
    raw = _synthetic_secret()

    masked = mask_token(raw)

    assert masked == "mock_token_************abcd"
    assert masked != raw
    assert "1234567890" not in masked


def test_redact_secret_fields_recursively() -> None:
    payload = {
        "message": "safe",
        "nested": {"client_secret": "synthetic-client-secret", "access_token": _synthetic_secret()},
        "items": [{"authorization": "Bearer synthetic"}],
    }

    redacted = redact_secret_fields(payload)

    assert redacted["message"] == "safe"
    assert redacted["nested"]["client_secret"] == "[REDACTED]"
    assert redacted["nested"]["access_token"] == "[REDACTED]"
    assert redacted["items"][0]["authorization"] == "[REDACTED]"


def test_safe_token_fingerprint_is_short_and_one_way() -> None:
    raw = _synthetic_secret()

    fingerprint = safe_token_fingerprint(raw)

    assert len(fingerprint) == 12
    assert fingerprint not in raw


def test_assert_no_raw_token_rejects_secret_fields_and_raw_values() -> None:
    with pytest.raises(TokenSafetyError):
        assert_no_raw_token_in_response({"access_token": "synthetic"})
    with pytest.raises(TokenSafetyError):
        assert_no_raw_token_in_response({"value": _synthetic_secret()})

    assert_no_raw_token_in_response({"masked_value": mask_token(_synthetic_secret()), "token_stored": False})
