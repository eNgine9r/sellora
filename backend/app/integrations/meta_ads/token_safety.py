from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import asdict, is_dataclass
from hashlib import sha256
from typing import Any

SECRET_FIELD_MARKERS = ("access_token", "refresh_token", "oauth_token", "client_secret", "app_secret", "authorization_header", "cookie", "password")
SECRET_FIELD_NAMES = {"authorization"}
REDACTED_VALUE = "[REDACTED]"


class TokenSafetyError(ValueError):
    """Raised when a response-like payload contains unsafe secret material."""


def mask_token(value: str | None, visible_suffix: int = 4) -> str:
    """Return a safe display mask for a token-like value without exposing it."""
    if not value:
        return ""
    suffix = value[-visible_suffix:] if len(value) > visible_suffix else ""
    if value.startswith("mock_token_"):
        return f"mock_token_************{suffix}"
    return f"********{suffix}"


def safe_token_fingerprint(value: str | None) -> str:
    """Return a short one-way fingerprint for diagnostics without storing tokens."""
    if not value:
        return ""
    return sha256(value.encode("utf-8")).hexdigest()[:12]


def _is_secret_key(key: str) -> bool:
    normalized = key.lower()
    return normalized in SECRET_FIELD_NAMES or any(marker in normalized for marker in SECRET_FIELD_MARKERS)


def redact_secret_fields(payload: Any) -> Any:
    """Recursively redact secret-like fields from a mapping/list/dataclass payload."""
    if is_dataclass(payload):
        return redact_secret_fields(asdict(payload))
    if isinstance(payload, Mapping):
        return {key: REDACTED_VALUE if _is_secret_key(str(key)) else redact_secret_fields(value) for key, value in payload.items()}
    if isinstance(payload, str):
        return payload
    if isinstance(payload, Sequence) and not isinstance(payload, (str, bytes, bytearray)):
        return [redact_secret_fields(item) for item in payload]
    return payload


def assert_no_raw_token_in_response(payload: Any) -> None:
    """Fail if a response-like payload exposes a raw token or secret field."""
    unsafe_paths: list[str] = []

    def walk(value: Any, path: str) -> None:
        if is_dataclass(value):
            walk(asdict(value), path)
            return
        if isinstance(value, Mapping):
            for key, child in value.items():
                child_path = f"{path}.{key}" if path else str(key)
                if _is_secret_key(str(key)):
                    unsafe_paths.append(child_path)
                walk(child, child_path)
            return
        if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
            for index, child in enumerate(value):
                walk(child, f"{path}[{index}]")
            return
        if isinstance(value, str) and value.startswith("mock_token_") and "*" not in value:
            unsafe_paths.append(path or "<root>")

    walk(payload, "")
    if unsafe_paths:
        raise TokenSafetyError("Response contains unsafe token material: " + ", ".join(sorted(set(unsafe_paths))))
