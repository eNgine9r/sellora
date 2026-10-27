"""Rule-based, conservative commercial interest classification.

The category is a *hint*, never order confirmation, customer payment evidence,
or an instruction to automatically message a customer or create an order.
"""
from dataclasses import dataclass
from enum import StrEnum
import re

from app.ai.services.direct_order_intent_service import detect_direct_order_intent


class CommercialStage(StrEnum):
    NONE = "NONE"
    INTEREST = "INTEREST"
    PRODUCT_QUESTION = "PRODUCT_QUESTION"
    PURCHASE_REQUEST = "PURCHASE_REQUEST"


@dataclass(frozen=True)
class CommercialSignal:
    stage: CommercialStage
    reason: str | None = None


_NEGATED = re.compile(
    r"\b(?:не\s+(?:хочу|буду|треба|потрібно|замовля|купую|беру)|"
    r"не\s+замовляйте|не\s+купуватиму|не\s+цікавить|"
    r"скасуйте|відмінити|отмена|тільки\s+не|не\s+надо|не\s+цікав\w*|не\s+хочу\s+заказывать)\b",
    re.IGNORECASE,
)
_PRODUCT = re.compile(
    r"\b(?:товар\w*|модел\w*|розмір\w*|колір\w*|браслет\w*|сереж\w*|"
    r"каблуч\w*|підвіск\w*|ланцюж\w*|кольє|годинник\w*|"
    r"прикра\w*|набір\w*|аксесуар\w*|купити|куплю|купую)\b",
    re.IGNORECASE,
)
_QUESTION = re.compile(
    r"(?:\?|\b(?:скільки|яка\s+ціна|яку\s+ціну|яка\s+вартість|коштує|"
    r"чи\s+є|є\s+в\s+наявності|в\s+наявності|"
    r"доступн\w*|наявн\w*|"
    r"можна\s+побачити|покажіть|підкажіть|"
    r"який\s+розмір|які\s+кольори|є\s+доставка|"
    r"скільки\s+доставка|доставляєте|"
    r"цена|сколько|есть\s+в\s+наличии)\b)",
    re.IGNORECASE,
)
_INTEREST = re.compile(
    r"\b(?:цікав\w*|подоба\w*|сподоба\w*|хотілося\s+б|хочу\s+подивитись|"
    r"дивлюсь|розглядаю|интерес\w*|нравит\w*)\b",
    re.IGNORECASE,
)
_NEGATED_REQUEST = re.compile(
    r"\b(?:не|ні|нет|без|не\s+треба)\s+(?:хочу|беру|куплю|купити|замовляю|замовити|оформити|заказать)\b",
    re.IGNORECASE,
)


def classify_commercial_message(text: str | None) -> CommercialSignal:
    normalized = " ".join((text or "").casefold().split())[:4000]
    if not normalized:
        return CommercialSignal(CommercialStage.NONE)
    if _NEGATED.search(normalized) or _NEGATED_REQUEST.search(normalized):
        return CommercialSignal(CommercialStage.NONE, "NEGATED")
    if detect_direct_order_intent(normalized).detected:
        return CommercialSignal(CommercialStage.PURCHASE_REQUEST, "EXPLICIT_REQUEST")
    has_product = bool(_PRODUCT.search(normalized))
    if has_product and _QUESTION.search(normalized):
        return CommercialSignal(CommercialStage.PRODUCT_QUESTION, "PRODUCT_QUESTION")
    if _INTEREST.search(normalized) or has_product:
        return CommercialSignal(CommercialStage.INTEREST, "PRODUCT_INTEREST")
    # Question about delivery with no product context is not a purchase.
    if _QUESTION.search(normalized) and re.search(r"\b(?:ціна|вартість|доставка|післяплата)\b",normalized):
        return CommercialSignal(CommercialStage.PRODUCT_QUESTION, "GENERAL_QUESTION")
    return CommercialSignal(CommercialStage.NONE)


def classify_commercial_conversation(messages) -> CommercialSignal:
    """Use the latest genuine inbound signal, without promoting earlier intent
    through later cancellation. Input is in repository newest-first order."""
    for item in messages:
        signal=classify_commercial_message(item.text)
        if signal.reason == "NEGATED":
            return signal
        if signal.stage != CommercialStage.NONE:
            return signal
    return CommercialSignal(CommercialStage.NONE)
