from __future__ import annotations

import re

_ALLOWED_UA_PHONE_RE = re.compile(r"^\+?[0-9\s()\-]+$")
_FORMATTING_RE = re.compile(r"[\s()\-]")


class PhoneNormalizationError(ValueError):
    pass


def normalize_ua_phone(raw: str | None) -> str | None:
    if raw is None:
        return None
    value = raw.strip()
    if not value:
        return None
    if not _ALLOWED_UA_PHONE_RE.fullmatch(value) or value.count("+") > 1 or ("+" in value and not value.startswith("+")):
        raise PhoneNormalizationError("INVALID_UA_PHONE")
    digits = _FORMATTING_RE.sub("", value[1:] if value.startswith("+") else value)
    if len(digits) == 10 and digits.startswith("0"):
        digits = f"38{digits}"
    if len(digits) != 12 or not digits.startswith("380"):
        raise PhoneNormalizationError("INVALID_UA_PHONE")
    return f"+{digits}"


def to_nova_poshta_phone(canonical: str) -> str:
    normalized = normalize_ua_phone(canonical)
    if normalized is None:
        raise PhoneNormalizationError("NOVA_POSHTA_PHONE_REQUIRED")
    return normalized[1:]


def format_ua_phone_for_display(canonical: str) -> str:
    normalized = normalize_ua_phone(canonical)
    if normalized is None:
        return ""
    digits = normalized[1:]
    return f"+{digits[:3]} {digits[3:5]} {digits[5:8]} {digits[8:10]} {digits[10:12]}"
