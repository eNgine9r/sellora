from datetime import UTC, datetime
from types import MethodType

from app.integrations.nova_poshta_client import NovaPoshtaClient


def test_provider_reconciliation_by_additional_information() -> None:
    client = NovaPoshtaClient("synthetic-key")
    marker = "SELLORA:11111111-2222-3333-4444-555555555555"
    rows = [
        {
            "Ref": "other-ref",
            "IntDocNumber": "20400000000001",
            "Description": "Біжутерія",
            "AdditionalInformation": "not the marker",
        },
        {
            "Ref": "matching-ref",
            "IntDocNumber": "20400000000002",
            "Description": "Біжутерія",
            "AdditionalInformation": marker,
        },
    ]
    def fake_call(self, model, method, properties=None, **kwargs):
        assert (model,method)==("InternetDocument","getDocumentList")
        return {"data":rows}
    client._call = MethodType(fake_call,client)
    result = client.find_internet_document(marker,datetime.now(UTC),datetime.now(UTC))
    assert result is not None
    assert result.tracking_number == "20400000000002"
    assert result.document_ref == "matching-ref"


def test_provider_reconciliation_supports_legacy_description_marker() -> None:
    client = NovaPoshtaClient("synthetic-key")
    marker = "SELLORA:11111111-2222-3333-4444-555555555555"
    def fake_call(self, model, method, properties=None, **kwargs):
        return {"data":[{"Ref":"legacy-ref","IntDocNumber":"20400000000003","Description":marker}]}
    client._call = MethodType(fake_call,client)
    result = client.find_internet_document(marker,datetime.now(UTC),datetime.now(UTC))
    assert result is not None
    assert result.document_ref == "legacy-ref"
