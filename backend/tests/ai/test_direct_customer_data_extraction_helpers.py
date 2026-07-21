from app.ai.schemas.structured_output import (
    CustomerDeliveryPointType,
    CustomerDeliveryProvider,
    DirectCustomerDataExtractionOutput,
)
from app.ai.services.direct_customer_data_extraction_service import (
    DirectCustomerDataExtractionService,
)


def test_customer_data_signal_accepts_compact_ukrainian_delivery_message() -> None:
    assert DirectCustomerDataExtractionService._looks_like_customer_data(
        ["0987379999 Черненко Крістіна Володимирівна Київ НП-273"]
    )


def test_customer_data_signal_accepts_split_messages() -> None:
    assert DirectCustomerDataExtractionService._looks_like_customer_data(
        ["Крістіна Черненко", "098 737 99 99", "Київ", "нова пошта 273"]
    )


def test_customer_data_signal_ignores_general_question() -> None:
    assert not DirectCustomerDataExtractionService._looks_like_customer_data(
        ["Добрий день, чи є чорний годинник у наявності?"]
    )


def test_extraction_normalizes_ukrainian_phone_and_warehouse_number() -> None:
    output = DirectCustomerDataExtractionOutput(
        recipient_name="  Черненко   Крістіна Володимирівна ",
        phone="098 737-99-99",
        city="Київ",
        region=None,
        delivery_provider=CustomerDeliveryProvider.NOVA_POSHTA,
        delivery_point_type=CustomerDeliveryPointType.WAREHOUSE,
        warehouse_number="НП-273",
        warehouse_text="Нова Пошта 273",
        notes=None,
        recipient_name_confidence=0.98,
        phone_confidence=0.99,
        city_confidence=0.99,
        delivery_provider_confidence=0.99,
        warehouse_confidence=0.98,
        overall_confidence=0.98,
        clarification_required=False,
        missing_fields=[],
    )

    normalized = DirectCustomerDataExtractionService._normalize(output)

    assert normalized["recipient_name"] == "Черненко Крістіна Володимирівна"
    assert normalized["phone"] == "+380987379999"
    assert normalized["warehouse_number"] == "НП-273"
    assert normalized["missing_fields"] == []


def test_invalid_phone_is_not_applied_silently() -> None:
    output = DirectCustomerDataExtractionOutput(
        recipient_name="Крістіна Черненко",
        phone="12345",
        city="Київ",
        region=None,
        delivery_provider=CustomerDeliveryProvider.NOVA_POSHTA,
        delivery_point_type=CustomerDeliveryPointType.WAREHOUSE,
        warehouse_number="273",
        warehouse_text="НП 273",
        notes=None,
        recipient_name_confidence=0.9,
        phone_confidence=0.9,
        city_confidence=0.9,
        delivery_provider_confidence=0.9,
        warehouse_confidence=0.9,
        overall_confidence=0.9,
        clarification_required=False,
        missing_fields=[],
    )

    normalized = DirectCustomerDataExtractionService._normalize(output)

    assert normalized["phone"] is None
    assert normalized["phone_confidence"] == 0
    assert normalized["clarification_required"] is True
    assert "phone" in normalized["missing_fields"]
