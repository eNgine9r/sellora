"""Checks for accurate, tenant-safe accessories text in Nova Poshta."""
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.repositories.nova_poshta_cargo_repository import NovaPoshtaCargoRepository
from app.services.nova_poshta_cargo_description import accessory_cargo_description
from app.services.nova_poshta_provider_service import NovaPoshtaProviderShipmentService


@pytest.mark.parametrize(
    ("products", "description"),
    [
        ([("Сріблястий браслет", "Браслети")], "Аксесуари (біжутерія)"),
        ([("Сережки", "Сережки"), ("Каблучка", "Каблучки")], "Аксесуари (біжутерія)"),
        ([("Підвіска", "Підвіски/Ланцюжки"), ("Кулон", "Кулони/Хрестики")], "Аксесуари (біжутерія)"),
        ([("Годинник жіночий", "Годинники")], "Аксесуари (годинник)"),
        ([("Смарт-годинник", "other")], "Аксесуари (годинник)"),
        ([("Годинник", "Годинники"), ("Браслет", "Браслети")], "Аксесуари (годинник, біжутерія)"),
        ([("Набір годинник + браслет", "Набір")], "Аксесуари (годинник, біжутерія)"),
        ([("Набір годинник", "Набір")], "Аксесуари (годинник)"),
        ([("Набір Сережки", "Набір")], "Аксесуари (біжутерія)"),
        ([("Набір без деталей", "Набір")], None),
        ([("Набір без деталей", "Набір"), ("Браслет", "Браслети")], "Аксесуари"),
        ([("Phone case", "Electronics")], None),
        ([], None),
    ],
)
def test_accessory_cargo_description_mapping(products, description) -> None:
    assert accessory_cargo_description(products) == description


def test_never_expose_technical_identifiers_and_customer_names() -> None:
    rows = [
        ("SELLORA:secret-b9cb1 UUID 51f-2f; recipient name", "Годинники"),
        ("+380XXXXXXXXX SELLORA:code", "Браслети"),
    ]
    result = accessory_cargo_description(rows)
    assert result == "Аксесуари (годинник, біжутерія)"
    assert "SELLORA" not in result and "380" not in result and "UUID" not in result


def test_auto_mode_queries_only_current_workspace_order(monkeypatch) -> None:
    workspace_id, order_id = uuid4(), uuid4()
    captured = []

    def fake_query(self, workspace, order):
        captured.append((workspace, order))
        return [("Годинник", "Годинники"), ("Браслет", "Браслети")]

    monkeypatch.setattr(NovaPoshtaCargoRepository, "list_order_categories", fake_query)
    shipment = SimpleNamespace(
        workspace_id=workspace_id,
        order_id=order_id,
        nova_poshta_city_ref="city-ref",
        nova_poshta_warehouse_ref="warehouse-ref",
        declared_value=600,
        cod_amount=600,
        recipient_name="Іван Петренко",
        recipient_phone="380671234567",
    )
    service = NovaPoshtaProviderShipmentService.__new__(NovaPoshtaProviderShipmentService)
    service.db = object()
    service.settings = SimpleNamespace(
        _require_connection=lambda _: (None, "synthetic-key"),
        client_factory=lambda _: SimpleNamespace(
            resolve_recipient_warehouse=lambda city, warehouse: ("Луцьк", "4")
        ),
    )
    settings = {
        "sender_city_ref": "sender-city",
        "sender_warehouse_ref": "sender-warehouse",
        "sender_counterparty_ref": "sender-counterparty",
        "sender_contact_ref": "sender-contact",
        "sender_phone": "380671234567",
        "cod_payment_mode": "PAYMENT_CONTROL",
        "cargo_description_mode": "AUTO_ACCESSORIES",
        "cargo_description": "Товари",
    }
    payload = service._document_payload(shipment, settings)
    assert captured == [(workspace_id, order_id)]
    assert payload["Description"] == "Аксесуари (годинник, біжутерія)"
    assert payload["AfterpaymentOnGoodsCost"] == "600"
    assert "BackwardDeliveryData" not in payload

    captured.clear()
    settings["cargo_description_mode"] = "STATIC"
    settings["cargo_description"] = "Мій опис"
    payload = service._document_payload(shipment, settings)
    assert not captured
    assert payload["Description"] == "Мій опис"


def test_order_category_query_scopes_every_join() -> None:
    """Query construction remains tenant-isolated and cannot leak product categories."""
    from sqlalchemy.sql import Select
    from sqlalchemy import select
    from app.models.order import Order
    from app.models.order_item import OrderItem
    from app.models.product import Product
    from app.models.product_variant import ProductVariant

    # Check the query actually compiled by the repository, without a live DB.
    class RecordingDb:
        def __init__(self):
            self.query = None

        def execute(self, query):
            self.query = query
            return SimpleNamespace(all=lambda: [])

    db = RecordingDb()
    workspace, order = uuid4(), uuid4()
    assert NovaPoshtaCargoRepository(db).list_order_categories(workspace, order) == []
    query = db.query
    sql = str(query)
    for table in ("order_items", "orders", "product_variants", "products"):
        assert table + ".workspace_id" in sql
    assert "order_items.order_id" in sql
    assert "order_items.deleted_at IS NULL" in sql
    assert "orders.deleted_at IS NULL" in sql
