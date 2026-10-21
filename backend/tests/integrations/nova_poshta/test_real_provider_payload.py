from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.integrations.nova_poshta_client import NovaPoshtaClient, NovaPoshtaClientError

from app.services.nova_poshta_provider_service import NovaPoshtaProviderShipmentService


def test_real_provider_payload_contains_required_new_recipient_fields() -> None:
    shipment = SimpleNamespace(
        workspace_id=uuid4(),
        nova_poshta_city_ref="city-ref",
        nova_poshta_warehouse_ref="warehouse-ref",
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
    service.settings = SimpleNamespace(
        _require_connection=lambda workspace_id: (None, "synthetic-key"),
        client_factory=lambda key: SimpleNamespace(
            resolve_recipient_warehouse=lambda city_ref, warehouse_ref: ("Луцьк", "4")
        ),
    )
    payload = service._document_payload(shipment, settings)

    assert payload["NewAddress"] == "1"
    assert payload["RecipientType"] == "PrivatePerson"
    assert payload["RecipientCityName"] == "Луцьк"
    assert payload["RecipientAddressName"] == "4"
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


def test_reference_lookup_uses_exact_provider_city_and_warehouse_values() -> None:
    client = NovaPoshtaClient("synthetic-key")
    calls = []

    def fake_call(model, method, properties=None):
        calls.append((model, method, properties))
        if method == "getCities":
            return {"data": [{"Ref": "city-ref", "Description": "Луцьк"}]}
        return {"data": [{"Ref": "warehouse-ref", "Number": "4", "Description": "Відділення №4"}]}

    client._call = fake_call
    assert client.resolve_recipient_warehouse("city-ref", "warehouse-ref") == ("Луцьк", "4")
    assert calls == [
        ("Address", "getCities", {"Ref": "city-ref"}),
        ("Address", "getWarehouses", {"CityRef": "city-ref", "Ref": "warehouse-ref"}),
    ]


def test_reference_lookup_rejects_invalid_warehouse_without_provider_write() -> None:
    client = NovaPoshtaClient("synthetic-key")
    def fake_call(model, method, properties=None):
        if method == "getCities":
            return {"data": [{"Ref": "city-ref", "Description": "Луцьк"}]}
        return {"data": []}
    client._call = fake_call
    with pytest.raises(NovaPoshtaClientError) as exc:
        client.resolve_recipient_warehouse("city-ref", "missing-wh")
    assert exc.value.code == "NOVA_POSHTA_RECIPIENT_WAREHOUSE_INVALID"
