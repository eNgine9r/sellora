from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class DirectOrderIntentSignal:
    detected: bool
    confidence: float
    reason: str | None = None


_EXPLICIT_ORDER_PATTERNS: tuple[tuple[str, str], ...] = (
    (r"\b(?:хочу|хотів|хотіла|хотіли)\s+(?:замовити|купити|оформити|взяти)\b", "explicit_purchase_request"),
    (r"\b(?:замовляю|замовлю|замовити|оформлю|оформити|оформіть|оформляйте|беру|купую|куплю)\b", "explicit_order_verb"),
    (r"\b(?:можна|як)\s+(?:замовити|оформити|купити)\b", "order_how_to"),
    (r"\b(?:відправляйте|надсилайте|оформіть\s+замовлення)\b", "fulfilment_request"),
    (r"\b(?:хочу|беру)\s+(?:цей|цю|це|таку|такий|такі)\b", "product_commitment"),
    (r"\b(?:хочу|хотел|хотела)\s+(?:заказать|купить|оформить|взять)\b", "explicit_purchase_request_ru"),
    (r"\b(?:заказываю|закажу|заказать|оформите|беру|покупаю|куплю)\b", "explicit_order_verb_ru"),
    (r"\b(?:can i|how do i|i want to)\s+(?:order|buy|purchase)\b", "explicit_order_en"),
)

_CONTEXT_PATTERNS: tuple[tuple[str, str], ...] = (
    (r"\b(?:післяплат(?:а|ою|и)?|накладен(?:ий|им|ого|ою)\s+платіж)\b", "cash_on_delivery"),
    (r"\b(?:наложенн(?:ый|ым|ого)\s+платеж)\b", "cash_on_delivery_ru"),
)


def detect_direct_order_intent(text: str | None) -> DirectOrderIntentSignal:
    normalized = " ".join((text or "").casefold().split())
    if not normalized:
        return DirectOrderIntentSignal(False, 0.0)

    for pattern, reason in _EXPLICIT_ORDER_PATTERNS:
        if re.search(pattern, normalized, flags=re.IGNORECASE):
            return DirectOrderIntentSignal(True, 0.92, reason)

    # A payment/delivery method question is treated as a probable order only when
    # the same message also contains a product or ordering context.
    ordering_context = bool(
        re.search(
            r"\b(?:замов|оформ|куп|беру|товар|годинник|прикраса|заказ|купить|order|buy)\w*\b",
            normalized,
            flags=re.IGNORECASE,
        )
    )
    if ordering_context:
        for pattern, reason in _CONTEXT_PATTERNS:
            if re.search(pattern, normalized, flags=re.IGNORECASE):
                return DirectOrderIntentSignal(True, 0.78, reason)

    return DirectOrderIntentSignal(False, 0.0)
