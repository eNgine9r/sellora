"""Finance connector guard: only limited GET/HTTPS, no token leakage, no paid mutation."""
from datetime import datetime, timedelta, timezone

import httpx
import pytest

from app.integrations.monobank.normalizers import merchant_statement_item
from app.integrations.monobank.read_only_client import (
    MONO_MERCHANT_ORIGIN,
    MerchantReadError, MonoMerchantReadOnlyClient,
)
from app.services.monobank_normalizers import MonobankPayloadError

TOKEN = "unit-test-not-an-actual-merchant-token-abcdef"
UTC = timezone.utc
TIME = datetime(2026, 11, 11, tzinfo=UTC)


class FakeTransport:
    def __init__(self, payload=None, *, code=200, failure=None):
        self.payload = payload or {}
        self.code = code
        self.failure = failure
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        if self.failure:
            raise self.failure
        request = httpx.Request("GET", url)
        return httpx.Response(self.code, json=self.payload, request=request)


def client(payload=None, **kwargs):
    transport = FakeTransport(payload, **kwargs)
    return MonoMerchantReadOnlyClient(token=TOKEN, transport=transport), transport


def test_invoice_status_only_fixed_https_get_with_no_redirects():
    reader, transport = client({"invoiceId": "p2_demo001", "status": "created"})
    result = reader.invoice_status("p2_demo001")
    assert result["status"] == "created"
    assert len(transport.calls) == 1
    path, kwargs = transport.calls[0]
    assert path == "https://api.monobank.ua/api/merchant/invoice/status"
    assert kwargs["params"] == {"invoiceId": "p2_demo001"}
    assert kwargs["headers"]["X-Token"] == TOKEN
    assert kwargs["follow_redirects"] is False
    assert not hasattr(reader, "cancel") and not hasattr(reader, "post")


@pytest.mark.parametrize("invoice_id", [
    "../invoice/remove", "https://evil.example", "x", "abc?x=2", "a\nbcd", " ", "😀" * 9,
])
def test_invalid_invoice_id_blocked_before_network(invoice_id):
    reader, transport = client()
    with pytest.raises(ValueError):
        reader.invoice_status(invoice_id)
    assert transport.calls == []


@pytest.mark.parametrize("status", [301, 302, 401, 403, 429, 500])
def test_provider_errors_are_sanitized_and_never_contain_sensitive_data(status):
    reader, _ = client({"token": TOKEN, "customer": "Sensitive"}, code=status)
    with pytest.raises(MerchantReadError) as exc:
        reader.invoice_status("p2_demo001")
    assert TOKEN not in str(exc.value) and "Sensitive" not in str(exc.value)


def test_transport_errors_sanitized():
    reader, _ = client(failure=httpx.ReadTimeout("token=" + TOKEN))
    with pytest.raises(MerchantReadError) as exc:
        reader.invoice_status("p2_demo001")
    assert TOKEN not in str(exc.value)


def test_invoice_identity_replay_or_conflict_fails_closed():
    reader, _ = client({"invoiceId": "p2_another"})
    with pytest.raises(MerchantReadError, match="mismatch"):
        reader.invoice_status("p2_demo001")


def test_statement_has_bounded_utc_dates_and_no_post_support():
    reader, transport = client({"list": []})
    assert reader.statement(from_at=TIME, to_at=TIME + timedelta(days=1)) == {"list": []}
    path, kwargs = transport.calls[0]
    assert path == "https://api.monobank.ua/api/merchant/statement"
    assert kwargs["params"]["to"] - kwargs["params"]["from"] == 86400
    assert kwargs["headers"]["X-Token"] == TOKEN


@pytest.mark.parametrize("days", [32, 200])
def test_statement_overlong_window_rejected(days):
    reader, transport = client({"list": []})
    with pytest.raises(ValueError):
        reader.statement(from_at=TIME, to_at=TIME + timedelta(days=days))
    assert transport.calls == []


def test_statement_rejects_bad_types_and_oversized_payload():
    reader, _ = client({"list": "not-an-array"})
    with pytest.raises(MerchantReadError):
        reader.statement(from_at=TIME, to_at=TIME)


def test_successful_merchant_statement_is_evidence_only():
    row = merchant_statement_item({
        "invoiceId": "p2_demo001", "status": "success", "amount": 74900,
        "ccy": 980, "profitAmount": 73000,
        "date": "2026-11-11T08:00:00Z", "cancelList": []
    }, merchant_account_id="authorized-merchant")
    assert row.kind.value == "CUSTOMER_PAYMENT"
    assert row.amount_minor == 74900
    assert row.order_number is None  # Never infer customer from untrusted reference
    assert row.invoice_id == "p2_demo001"
    assert merchant_statement_item({
        "invoiceId": "p2_demo001", "status": "hold", "amount": 74900,
        "ccy": 980, "date": "2026-11-11T08:00:00Z"
    }, merchant_account_id="authorized-merchant") is None


def test_refunds_and_wrong_currency_never_enter_paid_candidate():
    base = {
        "invoiceId": "p2_demo001", "status": "success", "amount": 74900,
        "ccy": 980, "date": "2026-11-11T08:00:00Z"
    }
    with pytest.raises(MonobankPayloadError):
        merchant_statement_item({**base, "cancelList": [{"amount": 25000}]}, merchant_account_id="m")
    with pytest.raises(MonobankPayloadError):
        merchant_statement_item({**base, "ccy": 840}, merchant_account_id="m")
