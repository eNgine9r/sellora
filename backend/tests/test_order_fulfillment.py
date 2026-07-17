from decimal import Decimal
from pathlib import Path
from types import MethodType, SimpleNamespace
from uuid import uuid4

from app.integrations.nova_poshta_client import NovaPoshtaClient
from app.models.order import PaymentStatus
from app.models.order_fulfillment import (
    OrderFulfillment,
    OrderFulfillmentResultCode,
    OrderFulfillmentState,
)
from app.models.shipment import Shipment
from app.schemas.order import OrderItemCreate
from app.schemas.order_fulfillment import OrderFulfillmentCreate
from app.services.nova_poshta_provider_service import NovaPoshtaProviderShipmentService
from app.services.order_fulfillment_service import OrderFulfillmentService


def _payload(*, create_ttn: bool = True) -> OrderFulfillmentCreate:
    return OrderFulfillmentCreate(
        idempotency_key="fulfillment-test-001",
        customer_id=uuid4(),
        recipient_name="Олена",
        recipient_phone="067 123 45 67",
        nova_poshta_city_ref="city-ref",
        city="Київ",
        nova_poshta_warehouse_ref="warehouse-ref",
        warehouse="Відділення №12",
        items=[
            OrderItemCreate(
                product_variant_id=uuid4(),
                quantity=1,
                unit_price=Decimal("500"),
                unit_cost=Decimal("120"),
            )
        ],
        payment_status=PaymentStatus.COD,
        create_ttn=create_ttn,
    )


def test_fulfillment_payload_normalizes_recipient_phone() -> None:
    assert _payload().recipient_phone == "+380671234567"


def test_ttn_retry_choice_does_not_change_idempotency_fingerprint() -> None:
    payload = _payload(create_ttn=False)
    assert OrderFulfillmentService._fingerprint(payload) == OrderFulfillmentService._fingerprint(
        payload.model_copy(update={"create_ttn": True})
    )


def test_provider_payload_sends_cod_as_backward_delivery_money() -> None:
    shipment = Shipment(
        recipient_name="Олена",
        recipient_phone="+380671234567",
        city="Київ",
        warehouse="Відділення №12",
        declared_value=Decimal("500"),
        cod_amount=Decimal("500"),
    )
    payload = NovaPoshtaProviderShipmentService.__new__(NovaPoshtaProviderShipmentService)._document_payload(
        shipment,
        {
            "sender_city_ref": "sender-city",
            "sender_warehouse_ref": "sender-warehouse",
            "sender_counterparty_ref": "sender",
            "sender_contact_ref": "contact",
            "sender_phone": "+380501234567",
        },
    )

    assert payload["BackwardDeliveryData"] == [
        {
            "PayerType": "Recipient",
            "CargoType": "Money",
            "RedeliveryString": "500",
        }
    ]


def test_sender_validation_uses_counterparty_model_for_contacts_and_addresses() -> None:
    client = NovaPoshtaClient("synthetic-key")
    calls = []

    def fake_call(model, method, properties=None, **_kwargs):
        calls.append((model, method, properties))
        return {"success": True, "data": [{"Ref": "match"}]}

    client._call = fake_call

    assert client.contact_belongs_to_counterparty("sender", "match")
    assert client.sender_address_belongs_to_sender("sender", "match")
    assert calls == [
        ("Counterparty", "getCounterpartyContactPersons", {"Ref": "sender"}),
        (
            "Counterparty",
            "getCounterpartyAddresses",
            {"Ref": "sender", "CounterpartyProperty": "Sender"},
        ),
    ]


def test_pending_idempotent_fulfillment_retries_only_ttn_creation() -> None:
    workspace_id = uuid4()
    shipment_id = uuid4()
    operation = OrderFulfillment(
        workspace_id=workspace_id,
        idempotency_key="fulfillment-test-001",
        request_fingerprint="unused",
        state=OrderFulfillmentState.COMPLETED.value,
        result_code=OrderFulfillmentResultCode.ORDER_CREATED_TTN_PENDING.value,
        customer_id=uuid4(),
        order_id=uuid4(),
        shipment_id=shipment_id,
    )
    provider_calls = []

    class Provider:
        def __init__(self, _db):
            pass

        def create_ttn(self, requested_workspace_id, requested_shipment_id, actor_user_id):
            provider_calls.append((requested_workspace_id, requested_shipment_id, actor_user_id))
            return SimpleNamespace(
                success=True,
                tracking_number="20450000000001",
                reused_existing_result=False,
                errors=[],
                manual_reconciliation_required=False,
                blind_retry_blocked=False,
            )

    service = OrderFulfillmentService(SimpleNamespace(commit=lambda: None), nova_poshta_service_factory=Provider)
    service._prepare_operation = MethodType(lambda self, *_args: (operation, True), service)
    service.operations = SimpleNamespace(get_by_key=lambda *_args, **_kwargs: operation)
    service._complete = MethodType(
        lambda self, _workspace_id, current, result_code, **kwargs: SimpleNamespace(
            result_code=result_code,
            tracking_number=current.tracking_number,
            kwargs=kwargs,
        ),
        service,
    )

    result = service.create(workspace_id, _payload(), actor_user_id=uuid4())

    assert len(provider_calls) == 1
    assert provider_calls[0][1] == shipment_id
    assert result.result_code == OrderFulfillmentResultCode.ORDER_AND_TTN_CREATED
    assert result.tracking_number == "20450000000001"


def test_fulfillment_migration_is_workspace_unique_and_rls_protected() -> None:
    migration = Path("alembic/versions/202607160024_order_fulfillments.py").read_text()

    assert 'down_revision: str | None = "202607160023"' in migration
    assert "uq_order_fulfillments_workspace_idempotency_key" in migration
    assert 'ENABLE ROW LEVEL SECURITY' in migration
