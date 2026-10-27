"""Validated, bounded daily Marketing API reader. No Meta write methods."""
from __future__ import annotations

import json
import re
from datetime import UTC, date, datetime
from decimal import Decimal, InvalidOperation
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.integrations.meta_ads.graph_transport import MetaGraphTransport
from app.integrations.meta_ads.live_read_only_client import MetaReadOnlyClientError, MetaReadOnlyErrorCode
from app.integrations.meta_ads.schemas import MetaAdAccountDTO, MetaCampaignDTO, MetaInsightsRowDTO


def malformed():
    return MetaReadOnlyClientError(MetaReadOnlyErrorCode.MALFORMED_RESPONSE)


def account_id(value):
    if not isinstance(value, str) or not re.fullmatch(r"act_[0-9]{1,40}", value):
        raise malformed()
    return value


def numeric_id(value):
    if not isinstance(value, str) or not re.fullmatch(r"[0-9]{1,40}", value):
        raise malformed()
    return value


class MetaAdsLiveReader:
    def __init__(self, *, access_token, api_version, transport=None):
        self.token = access_token
        self.transport = transport or MetaGraphTransport(api_version)

    def _pages(self, path, params):
        params = {**params, "limit": 100}
        seen = set()
        result = []
        for _ in range(50):
            payload = self.transport.request(path, token=self.token, params=params)
            rows = payload.get("data")
            if not isinstance(rows, list) or len(rows) > 100 or not all(isinstance(r, dict) for r in rows):
                raise malformed()
            result.extend(rows)
            paging = payload.get("paging") or {}
            if not isinstance(paging, dict):
                raise malformed()
            if not paging.get("next"):
                return result
            # Never follow the provider's next URL, including its token query.
            cursors = paging.get("cursors") or {}
            if not isinstance(cursors, dict):
                raise malformed()
            cursor = cursors.get("after")
            if not isinstance(cursor, str) or not re.fullmatch(r"[A-Za-z0-9_=-]{1,2048}", cursor) or cursor in seen:
                raise malformed()
            seen.add(cursor)
            params = {**params, "after": cursor}
        raise malformed()

    def list_ad_accounts(self):
        result = []
        seen = set()
        for row in self._pages("/me/adaccounts", {"fields": "id,name,currency,timezone_name,account_status"}):
            identifier = account_id(row.get("id"))
            currency = row.get("currency")
            timezone = row.get("timezone_name")
            if not isinstance(currency, str) or not re.fullmatch(r"[A-Z]{3}", currency):
                raise malformed()
            try:
                ZoneInfo(timezone)
            except (ZoneInfoNotFoundError, TypeError, ValueError):
                raise malformed() from None
            if identifier in seen:
                raise malformed()
            seen.add(identifier)
            if str(row.get("account_status", 1)) != "1":
                continue
            result.append(MetaAdAccountDTO(identifier, str(row.get("name") or identifier)[:255], currency, timezone))
        return result

    def list_campaigns(self, identifier):
        result = []
        seen = set()
        for row in self._pages(f"/{account_id(identifier)}/campaigns", {"fields": "id,name,status,objective"}):
            campaign = numeric_id(row.get("id"))
            if campaign in seen:
                raise malformed()
            seen.add(campaign)
            result.append(MetaCampaignDTO(campaign, identifier, str(row.get("name") or campaign)[:255],
                str(row.get("status") or "UNKNOWN"), str(row.get("objective") or "UNKNOWN"), "META", datetime.now(UTC)))
        return result

    def get_campaign_insights_preview(self, identifier, date_from: date, date_to: date):
        if not 0 <= (date_to - date_from).days <= 90:
            raise malformed()
        data = self._pages(f"/{account_id(identifier)}/insights", {
            "fields": "campaign_id,date_start,date_stop,spend,impressions,clicks,actions,account_currency",
            "time_range": json.dumps({"since": date_from.isoformat(), "until": date_to.isoformat()}, separators=(",", ":")),
            "time_increment": 1, "level": "campaign",
        })
        result = []
        seen = set()
        try:
            for row in data:
                campaign = numeric_id(row.get("campaign_id"))
                day = date.fromisoformat(row["date_start"])
                if not date_from <= day <= date_to or row.get("date_stop", day.isoformat()) != day.isoformat() or (campaign, day) in seen:
                    raise malformed()
                seen.add((campaign, day))
                spend = Decimal(str(row.get("spend", "0"))).quantize(Decimal("0.01"))
                if not spend.is_finite() or spend < 0 or spend >= Decimal("10000000000"):
                    raise malformed()
                actions = row.get("actions", [])
                if not isinstance(actions, list):
                    raise malformed()
                # This one canonical action is a count of conversations started.
                # Other messaging action types overlap and must not be summed.
                messages = [a.get("value", 0) for a in actions if isinstance(a, dict)
                    and a.get("action_type") == "onsite_conversion.messaging_conversation_started_7d"]
                if len(messages) > 1:
                    raise malformed()
                counts = [int(row.get("impressions", 0)), int(row.get("clicks", 0)), int(messages[0]) if messages else 0]
                if any(n < 0 or n > 2147483647 for n in counts):
                    raise malformed()
                currency = row.get("account_currency")
                if not isinstance(currency, str) or not re.fullmatch(r"[A-Z]{3}", currency):
                    raise malformed()
                result.append(MetaInsightsRowDTO(campaign, day, spend, *counts, currency=currency))
        except (ValueError, TypeError, KeyError, InvalidOperation):
            raise malformed() from None
        return result
