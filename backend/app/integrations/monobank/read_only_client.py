"""Minimal monobank merchant read client.

SECURITY CONTRACT:
- Only whitelisted GET paths and a fixed HTTPS origin.
- No payment/refund/invoice-creation functions, and never log access tokens.
- Credentials must be supplied by an isolated, separately authorized runtime;
  this module does not read a user's Personal API token or database settings.
- Never request live monobank access as part of tests or app startup.
- A Merchant X-Token may also authorize *write/refund* actions in the bank's API;
  GET-only code does NOT make the credential itself read-only.
"""
from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Protocol

import httpx

MONO_MERCHANT_ORIGIN = "https://api.monobank.ua"
_INVOICE_ID = re.compile(r"^[A-Za-z0-9_-]{5,120}$")
_MAX_WINDOW_SECONDS = 31 * 86400


class MerchantReadError(RuntimeError):
    """Sanitized error for staff and logs (no raw token, body, or URL)."""


class MerchantClientTransport(Protocol):
    def get(self, url: str, *, params: dict[str, str | int],
            headers: dict[str, str], timeout: float, follow_redirects: bool) -> httpx.Response: ...


class MonoMerchantReadOnlyClient:
    """No generic HTTP method, URL, header, or token exposed to callers."""

    def __init__(self, *, token: str, transport: MerchantClientTransport):
        if not isinstance(token, str) or not 20 <= len(token) <= 512 or any(ch.isspace() for ch in token):
            raise ValueError("Merchant credential is unavailable or invalid")
        self._token = token
        self._transport = transport

    def _fetch(self, path: str, *, params: dict[str, str | int]) -> dict:
        if path not in {"/api/merchant/invoice/status", "/api/merchant/statement"}:
            raise MerchantReadError("Unsupported merchant operation")
        try:
            response = self._transport.get(
                MONO_MERCHANT_ORIGIN + path,
                params=params,
                headers={"X-Token": self._token, "Accept": "application/json"},
                timeout=8.0,
                follow_redirects=False,
            )
            if response.status_code != 200:
                # Explicitly reject redirects, unauthenticated and rate limits;
                # never include a provider response that might leak PII/secrets.
                if response.status_code == 429:
                    raise MerchantReadError("Merchant API rate limit")
                if response.status_code in {401, 403}:
                    raise MerchantReadError("Merchant API access denied")
                raise MerchantReadError("Merchant API unavailable")
            if len(response.content) > 524288:
                raise MerchantReadError("Merchant response exceeds safe limit")
            result = response.json()
            if not isinstance(result, dict):
                raise MerchantReadError("Invalid merchant response")
            return result
        except (httpx.RequestError, ValueError) as exc:
            raise MerchantReadError("Merchant API transport/format error") from None

    def invoice_status(self, invoice_id: str) -> dict:
        if not isinstance(invoice_id, str) or not _INVOICE_ID.fullmatch(invoice_id):
            raise ValueError("Invalid invoice identifier")
        value = self._fetch("/api/merchant/invoice/status", params={"invoiceId": invoice_id})
        if value.get("invoiceId") != invoice_id:
            raise MerchantReadError("Invoice identity mismatch")
        return value

    def statement(self, *, from_at: datetime, to_at: datetime) -> dict:
        if from_at.tzinfo is None or to_at.tzinfo is None:
            raise ValueError("UTC-aware datetimes required")
        start = int(from_at.astimezone(UTC).timestamp())
        stop = int(to_at.astimezone(UTC).timestamp())
        if start <= 0 or stop < start or stop - start > _MAX_WINDOW_SECONDS:
            raise ValueError("Invalid merchant statement window")
        value = self._fetch("/api/merchant/statement", params={"from": start, "to": stop})
        if not isinstance(value.get("list"), list) or len(value["list"]) > 2000:
            raise MerchantReadError("Invalid or excessive statement size")
        return value
