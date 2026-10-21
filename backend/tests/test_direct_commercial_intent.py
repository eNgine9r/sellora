from types import SimpleNamespace
import pytest
from app.ai.services.direct_commercial_intent_service import (
    CommercialStage, classify_commercial_message, classify_commercial_conversation
)

@pytest.mark.parametrize("message,stage", [
    ("Доброго дня", CommercialStage.NONE),
    ("Дякую!", CommercialStage.NONE),
    ("?", CommercialStage.NONE),
    ("Мені подобаються ці прикраси", CommercialStage.INTEREST),
    ("Цікавлять сережки", CommercialStage.INTEREST),
    ("Хочу подивитись годинники", CommercialStage.INTEREST),
    ("Чи є браслети в наявності?", CommercialStage.PRODUCT_QUESTION),
    ("Яка ціна на каблучку?", CommercialStage.PRODUCT_QUESTION),
    ("Скільки доставка?", CommercialStage.PRODUCT_QUESTION),
    ("У вас є сережки?", CommercialStage.PRODUCT_QUESTION),
    ("Хочу замовити браслет", CommercialStage.PURCHASE_REQUEST),
    ("Беру цей годинник", CommercialStage.PURCHASE_REQUEST),
    ("Можна оформити замовлення?", CommercialStage.PURCHASE_REQUEST),
    ("Не хочу купити цю каблучку", CommercialStage.NONE),
    ("Не замовляйте мені товар", CommercialStage.NONE),
    ("Скасуйте замовлення", CommercialStage.NONE),
    ("Не цікаві годинники", CommercialStage.NONE),
])
def test_safe_commercial_classification(message,stage):
    assert classify_commercial_message(message).stage==stage

def test_latest_negative_cancels_old_request():
    messages=[SimpleNamespace(text="Скасуйте замовлення"),SimpleNamespace(text="Хочу замовити сережки")]
    assert classify_commercial_conversation(messages).stage==CommercialStage.NONE

def test_latest_purchase_signal_takes_precedence_over_prior_questions():
    messages=[SimpleNamespace(text="Куплю годинник"),SimpleNamespace(text="Яка ціна на годинник?")]
    assert classify_commercial_conversation(messages).stage==CommercialStage.PURCHASE_REQUEST

def test_not_confirmed_order_even_with_explicit_request():
    assert classify_commercial_message("Беру цей браслет").stage.value != "CONFIRMED_ORDER"
