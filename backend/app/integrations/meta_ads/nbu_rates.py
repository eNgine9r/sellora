"""Official daily USD/UAH rates. No account credentials are sent to NBU."""
from datetime import date, datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

import httpx


class ExchangeRateUnavailable(ValueError):
    pass


def can_convert(source: str, target: str) -> bool:
    return source == target or (source, target) == ("USD", "UAH")


class NbuDailyRates:
    def __init__(self, *, url: str, client=None):
        self.url = url
        self.client = client

    def get_rates(self, days: set[date]) -> dict[date, Decimal]:
        if not days:
            return {}
        start, end = min(days), max(days)
        if (end - start).days > 90:
            raise ExchangeRateUnavailable("Invalid rate date range")
        params = {"start": start.strftime("%Y%m%d"), "end": end.strftime("%Y%m%d"),
                  "valcode": "usd", "sort": "exchangedate", "order": "asc", "json": ""}
        try:
            if self.client is None:
                with httpx.Client(timeout=10, follow_redirects=False) as client:
                    response = client.get(self.url, params=params)
            else:
                response = self.client.get(self.url, params=params, timeout=10, follow_redirects=False)
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, list) or len(payload) > 91:
                raise ValueError()
            rates = {}
            for row in payload:
                day = datetime.strptime(row["exchangedate"], "%d.%m.%Y").date()
                rate = Decimal(str(row["rate_per_unit"]))
                if (row["cc"] != "USD" or row["r030"] != 840 or row["units"] != 1
                    or not start <= day <= end or day in rates
                    or not rate.is_finite() or not 0 < rate < 1000000
                    or rate != rate.quantize(Decimal("0.00000001"))):
                    raise ValueError()
                rates[day] = rate
            if not days <= rates.keys():
                raise ValueError()
            return {day: rates[day] for day in days}
        except (httpx.HTTPError, ValueError, TypeError, KeyError, InvalidOperation):
            raise ExchangeRateUnavailable("Official NBU daily rates are unavailable for the requested dates.") from None


def converted_spend(original: Decimal, rate: Decimal) -> Decimal:
    amount = (original * rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    if not amount.is_finite() or not 0 <= amount < Decimal("10000000000"):
        raise ExchangeRateUnavailable("Converted advertising spend exceeds the supported amount.")
    return amount
