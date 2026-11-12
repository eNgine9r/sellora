"""Read-only evidence for reviewable Smart Sale price hints.

A quoted price from Direct is NOT proof of purchase or bank settlement.
Only text actually sent by the shop before the exact TTN is considered.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.ai_direct import DirectMessage

# Intentional: no match for bare numbers, bank account / card / TTN or a
# package declared value. One outbound monetary quote is only a *hint*.
_MONEY = re.compile(
    r"(?<![\w\d])(?:"
    r"(?P<before>₴)\s*(?P<pre_amount>\d{3,6}(?:[.,]\d{1,2})?)"
    r"|(?P<amount>\d{3,6}(?:[.,]\d{1,2})?)\s*(?P<currency>грн\.?|грив(?:ень|ні|на|ні)?|uah|₴)"
    r")(?![\w\d])",
    re.IGNORECASE,
)
_NON_ITEM = re.compile(
    r"\b(?:доставк\w*|пересилк\w*|комісі\w*|поштов\w*|тариф\w*|"
    r"передплат\w*|завдат\w*|оплат[аи]\s+за\s+достав\w*|"
    r"наложенн\w*|післяплат\w*|страхов\w*)\b",
    re.IGNORECASE,
)
_MAX_QUOTES = 4
_MAX_CONTEXT_MESSAGES = 250
_MIN_AMOUNT = Decimal("100")
_MAX_AMOUNT = Decimal("1000000")
_WINDOW = timedelta(days=7)
_TTN = re.compile(r"(?<!\d)20\d{12}(?!\d)")


@dataclass(frozen=True)
class PriceQuote:
    amount: Decimal
    message_id: UUID


@dataclass(frozen=True)
class SaleQuoteContext:
    anchored_ids: frozenset[UUID]
    prices: tuple[PriceQuote, ...]
    anchor_found: bool


def extract_quotes(messages: list, tracking_number: str) -> SaleQuoteContext:
    """Extract finite, distinct outbound product prices before exact TTN.

    Input is newest-first and must have previously been workspace/conversation
    scoped by the caller. Old TTN/another sale is a hard context boundary.
    Returns IDs for validating existing SKU evidence against the *same* sale.
    """
    if not tracking_number or not _TTN.fullmatch(tracking_number):
        return SaleQuoteContext(frozenset(), (), False)
    # All messages in the provided slice should be sorted by real message time.
    ordered = sorted(messages, key=lambda m: (m.received_at, str(m.id)))
    anchors = [i for i, msg in enumerate(ordered) if (
        msg.direction == "OUTBOUND" and
        not getattr(msg, "is_synthetic", False) and
        tracking_number in (msg.text or "")
    )]
    if len(anchors) != 1:
        # Multiple exact mentions/forwarded labels need human review.
        return SaleQuoteContext(frozenset(), (), False)
    index = anchors[0]
    anchor = ordered[index]
    relevant = []
    for msg in reversed(ordered[:index]):
        if anchor.received_at - msg.received_at > _WINDOW:
            break
        if msg.direction == "OUTBOUND" and _TTN.search(msg.text or ""):
            break
        if getattr(msg, "is_synthetic", False):
            continue
        if msg.text:
            relevant.append(msg)
    # Restrict SKU and price evidence to exactly the same bounded sale context.
    ids = frozenset(msg.id for msg in relevant)
    prices: list[PriceQuote] = []
    seen: set[Decimal] = set()
    for msg in relevant:
        if msg.direction != "OUTBOUND" or msg.message_type != "TEXT":
            continue
        text = (msg.text or "")[:4000]
        if _NON_ITEM.search(text) or _TTN.search(text):
            continue
        found = []
        for match in _MONEY.finditer(text):
            raw = (match.group("pre_amount") or match.group("amount")).replace(",", ".")
            try:
                amount = Decimal(raw)
            except Exception:
                continue
            if _MIN_AMOUNT <= amount <= _MAX_AMOUNT:
                found.append(amount)
        # One message with multiple prices is not a trusted single quote.
        if len(set(found)) != 1:
            continue
        amount = found[0]
        if amount in seen:
            continue
        prices.append(PriceQuote(amount=amount, message_id=msg.id))
        seen.add(amount)
        if len(prices) >= _MAX_QUOTES:
            break
    return SaleQuoteContext(ids, tuple(prices), True)


class DirectSaleQuoteService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get(self, workspace_id: UUID, conversation_id: UUID, tracking_number: str) -> SaleQuoteContext:
        # Extra row detects an unsafe truncated conversation. Never base
        # a price or SKU on an incomplete history.
        rows = list(self.db.scalars(
            select(DirectMessage).where(
                DirectMessage.workspace_id == workspace_id,
                DirectMessage.conversation_id == conversation_id,
                DirectMessage.deleted_at.is_(None),
                DirectMessage.message_type == "TEXT",
            ).order_by(DirectMessage.received_at.desc(), DirectMessage.id.desc()).limit(_MAX_CONTEXT_MESSAGES + 1)
        ).all())
        if len(rows) > _MAX_CONTEXT_MESSAGES:
            return SaleQuoteContext(frozenset(), (), False)
        return extract_quotes(rows, tracking_number)
