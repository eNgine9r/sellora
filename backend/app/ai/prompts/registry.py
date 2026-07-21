from dataclasses import dataclass
from typing import Any

from app.ai.schemas.structured_output import (
    DirectCustomerDataExtractionOutput,
    DirectMessageAnalysisOutput,
)


@dataclass(frozen=True)
class PromptDefinition:
    prompt_key: str
    prompt_version: str
    purpose: str
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]
    maximum_context: int
    model_class: str
    system_prompt: str


SAFETY_RULES = "Не вигадуй товари, ціни, stock або обіцянки доставки. Не підтверджуй замовлення і не створюй CRM-об'єкти. Поверни лише strict JSON."

CUSTOMER_DATA_EXTRACTION_RULES = """
Ти витягуєш дані отримувача й доставки з переписки Instagram-магазину.
Працюй з українською, російською, англійською, транслітом, скороченнями та помилками.
Розрізняй повідомлення клієнта й менеджера за полем direction. Дані отримувача бери лише з INBOUND.
Не вигадуй значення. Якщо поле не підтверджене текстом клієнта — поверни null і низьку confidence.
Нормалізуй ПІБ без зміни порядку слів. Телефон повертай у тому вигляді, який найкраще відновлено з тексту; backend виконає остаточну UA-нормалізацію.
Розпізнавай Нова Пошта, НП, новая почта, NP, відділення, поштомат, почтомат, branch, warehouse.
Номер відділення або поштомата повертай окремо у warehouse_number без символів №, #, НП-.
Якщо місто, телефон, ПІБ або точка доставки неоднозначні — clarification_required=true.
Не створюй замовлення, ТТН чи клієнта. Поверни лише JSON за схемою.
""".strip()

PROMPTS = {
    "DIRECT_MESSAGE_ANALYSIS": PromptDefinition("DIRECT_MESSAGE_ANALYSIS", "direct-message-analysis:v1", "Analyze synthetic Direct text", {}, DirectMessageAnalysisOutput.model_json_schema(), 12000, "fast", SAFETY_RULES),
    "DIRECT_CONVERSATION_SUMMARY": PromptDefinition("DIRECT_CONVERSATION_SUMMARY", "direct-conversation-summary:v1", "Summarize Direct conversation", {}, {}, 12000, "fast", SAFETY_RULES),
    "DIRECT_REPLY_SUGGESTION": PromptDefinition("DIRECT_REPLY_SUGGESTION", "direct-reply-suggestion:v1", "Draft manager-reviewed reply", {}, {}, 12000, "fast", SAFETY_RULES),
    "DIRECT_ACTION_DRAFT": PromptDefinition("DIRECT_ACTION_DRAFT", "direct-action-draft:v1", "Draft CRM action for approval", {}, {}, 12000, "fast", SAFETY_RULES),
    "PRODUCT_MENTION_NORMALIZATION": PromptDefinition("PRODUCT_MENTION_NORMALIZATION", "product-mention-normalization:v1", "Normalize product mentions", {}, {}, 4000, "fast", SAFETY_RULES),
    "DIRECT_CUSTOMER_DATA_EXTRACTION": PromptDefinition(
        "DIRECT_CUSTOMER_DATA_EXTRACTION",
        "direct-customer-data-extraction:v1",
        "Extract recipient, phone, city and delivery point from Direct conversation",
        {},
        DirectCustomerDataExtractionOutput.model_json_schema(),
        12000,
        "fast",
        CUSTOMER_DATA_EXTRACTION_RULES,
    ),
}


def get_prompt(prompt_key: str) -> PromptDefinition:
    return PROMPTS[prompt_key]
