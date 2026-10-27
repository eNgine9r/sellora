from datetime import date
from decimal import Decimal

import httpx
import pytest

from app.integrations.meta_ads.nbu_rates import NbuDailyRates, ExchangeRateUnavailable, can_convert, converted_spend

DAY = date(2026, 10, 1)
URL = "https://nbu.example.invalid/rates"
ROW = {"exchangedate": "01.10.2026", "cc": "USD", "r030": 840, "units": 1, "rate_per_unit": "43.1234"}


def provider(payload, status=200):
    def handler(request):
        assert request.method == "GET" and request.url.params["valcode"] == "usd"
        assert request.url.params["start"] == "20261001" and request.url.params["end"] == "20261001"
        assert "authorization" not in request.headers
        return httpx.Response(status, json=payload)
    return NbuDailyRates(url=URL, client=httpx.Client(transport=httpx.MockTransport(handler)))


def test_daily_nbu_rate_and_half_up_rounding():
    assert provider([ROW]).get_rates({DAY}) == {DAY: Decimal("43.1234")}
    assert converted_spend(Decimal("1.25"), Decimal("44.5678")) == Decimal("55.71")
    assert converted_spend(Decimal("0.01"), Decimal("42.5")) == Decimal("0.43")
    assert can_convert("USD", "UAH") and can_convert("UAH", "UAH")
    assert not can_convert("EUR", "UAH") and not can_convert("UAH", "USD")


@pytest.mark.parametrize("payload", [[], {}, [ROW, ROW], [dict(ROW, exchangedate="02.10.2026")],
    [dict(ROW, cc="EUR")], [dict(ROW, r030=978)], [dict(ROW, units=100)], [dict(ROW, rate_per_unit="0")],
    [dict(ROW, rate_per_unit="-1")], [dict(ROW, rate_per_unit="NaN")], [dict(ROW, rate_per_unit="Infinity")],
    [dict(ROW, rate_per_unit="43.123456789")], [dict(ROW, rate_per_unit="bad")], [None]])
def test_invalid_or_missing_rate_fails_closed(payload):
    with pytest.raises(ExchangeRateUnavailable):
        provider(payload).get_rates({DAY})


def test_http_error_and_overflow_fail_closed():
    with pytest.raises(ExchangeRateUnavailable):
        provider([ROW], 503).get_rates({DAY})
    with pytest.raises(ExchangeRateUnavailable):
        converted_spend(Decimal("9999999999.99"), Decimal("45"))
