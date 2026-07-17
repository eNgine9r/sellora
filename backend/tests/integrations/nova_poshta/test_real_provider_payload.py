from types import SimpleNamespace

from app.services.nova_poshta_provider_service import NovaPoshtaProviderShipmentService


def test_real_provider_payload_contains_required_new_recipient_fields() -> None:
    shipment = SimpleNamespace(
        declared_value=100,
        city="Луцьк",
        warehouse="Відділення №1",
        recipient_name="Recipient",
        recipient_phone="380671234567",
    )
    settings = {
        "sender_city_ref": "sender-city-ref",
        "sender_warehouse_ref": "sender-warehouse-ref",
        "sender_counterparty_ref": "sender-counterparty-ref",
        "sender_contact_ref": "sender-contact-ref",
        "sender_phone": "380671234567",
    }

    service = NovaPoshtaProviderShipmentService.__new__(NovaPoshtaProviderShipmentService)
    payload = service._document_payload(shipment, settings)

    assert payload["NewAddress"] == "1"
    assert payload["RecipientType"] == "PrivatePerson"
    assert payload["RecipientCityName"] == "Луцьк"
    assert payload["RecipientAddressName"] == "Відділення №1"
    assert payload["Weight"] == "0.5"
    assert payload["VolumeGeneral"] == "0.001"
    assert payload["SeatsAmount"] == "1"
    assert payload["DateTime"]
    assert payload["SendersPhone"] == "380671234567"
    assert payload["RecipientsPhone"] == "380671234567"
    assert payload["CitySender"] == "sender-city-ref"
    assert payload["Sender"] == "sender-counterparty-ref"
    assert payload["ContactSender"] == "sender-contact-ref"
    assert "CityRecipient" not in payload
    assert "RecipientAddress" not in payload
