from __future__ import annotations

from datetime import UTC, datetime

from app.services.nova_poshta_service import NovaPoshtaShipmentService
from app.utils.phone import to_nova_poshta_phone


class NovaPoshtaProviderShipmentService(NovaPoshtaShipmentService):
    """Real-provider shipment service with the full InternetDocument.save payload.

    The durable idempotency and reconciliation state machine remains implemented
    by ``NovaPoshtaShipmentService``. This adapter only supplies the provider
    payload required for a new private-person recipient and warehouse delivery.
    """

    def _document_payload(self, shipment, settings: dict) -> dict:
        return {
            "PayerType": "Recipient",
            "PaymentMethod": "Cash",
            "DateTime": datetime.now(UTC).strftime("%d.%m.%Y"),
            "CargoType": "Parcel",
            "VolumeGeneral": "0.001",
            "Weight": "0.5",
            "ServiceType": "WarehouseWarehouse",
            "SeatsAmount": "1",
            "Description": "Товар",
            "Cost": str(shipment.declared_value or 0),
            "CitySender": settings.get("sender_city_ref"),
            "Sender": settings.get("sender_counterparty_ref"),
            "SenderAddress": settings.get("sender_warehouse_ref"),
            "ContactSender": settings.get("sender_contact_ref"),
            "SendersPhone": to_nova_poshta_phone(settings.get("sender_phone")),
            "NewAddress": "1",
            "RecipientCityName": shipment.city,
            "RecipientAddressName": shipment.warehouse,
            "RecipientName": shipment.recipient_name,
            "RecipientType": "PrivatePerson",
            "RecipientsPhone": to_nova_poshta_phone(shipment.recipient_phone),
        }
