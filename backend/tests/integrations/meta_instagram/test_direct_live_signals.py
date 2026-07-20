import pytest

from app.ai.services.direct_order_intent_service import detect_direct_order_intent


@pytest.mark.parametrize(
    "text",
    [
        "Хочу замовити цей чорний годинник",
        "Можна замовити післяплатою?",
        "Беру цю модель, оформіть замовлення",
        "Хочу купить эти часы",
        "Can I order this item?",
    ],
)
def test_detects_probable_order_intent(text):
    signal = detect_direct_order_intent(text)

    assert signal.detected is True
    assert signal.confidence >= 0.75
    assert signal.reason


@pytest.mark.parametrize(
    "text",
    [
        "Добрий день",
        "Яка ціна?",
        "Де моє попереднє замовлення?",
        "Доставка вже приїхала?",
        "Дякую",
    ],
)
def test_does_not_overstate_non_order_messages(text):
    signal = detect_direct_order_intent(text)

    assert signal.detected is False
    assert signal.confidence == 0.0
