"""Live Direct inquiry classification regression (no provider, DB or network)."""
from app.services.direct_inquiry_lead_worker import qualifies


def test_inbound_commercial_inquiries_are_candidates():
    for message in (
        "Привіт! Яка ціна годинника?",
        "Хочу замовити",
        "Можна доставку Новою Поштою?",
        "Добрий вечір",
        "Is this available?",
    ):
        assert qualifies(message), message


def test_acknowledgements_or_empty_are_not_leads():
    for message in (None, "", "  ", "дякую", " ОК ", "+", "👍", "🙏", "https://example.com", "12345"):
        assert not qualifies(message), message
