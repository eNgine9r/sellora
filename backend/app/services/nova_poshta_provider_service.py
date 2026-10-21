from __future__ import annotations

from datetime import UTC, datetime

from app.integrations.nova_poshta_client import NovaPoshtaClientError
from app.services.nova_poshta_service import NovaPoshtaServiceError, NovaPoshtaShipmentService
from app.utils.phone import to_nova_poshta_phone


class NovaPoshtaProviderShipmentService(NovaPoshtaShipmentService):
    """Real-provider shipment service with the full InternetDocument.save payload.

    The durable idempotency and reconciliation state machine remains implemented
    by ``NovaPoshtaShipmentService``. This adapter only supplies the provider
    payload required for a new private-person recipient and warehouse delivery.
    """

    def _document_payload(self, shipment, settings: dict) -> dict:
        # The user-facing city/warehouse labels are not valid NewAddress values:
        # e.g. "м. Луцьк, Волинська обл." / "Відділення №4: вул. ...".
        # Resolve verified provider references without changing the saved labels.
        _connection, api_key = self.settings._require_connection(shipment.workspace_id)
        try:
            recipient_city, recipient_warehouse = self.settings.client_factory(
                api_key
            ).resolve_recipient_warehouse(
                shipment.nova_poshta_city_ref,
                shipment.nova_poshta_warehouse_ref,
            )
        except NovaPoshtaClientError as exc:
            # Never expose raw provider data or credentials via a route exception.
            raise NovaPoshtaServiceError(exc.code) from exc
        payload = {
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
            "RecipientCityName": recipient_city,
            "RecipientAddressName": recipient_warehouse,
            "RecipientName": shipment.recipient_name,
            "RecipientType": "PrivatePerson",
            "RecipientsPhone": to_nova_poshta_phone(shipment.recipient_phone),
        }
        cod_amount = getattr(shipment, "cod_amount", None)
        if cod_amount and cod_amount > 0:
            payload["BackwardDeliveryData"] = [
                {
                    "PayerType": "Recipient",
                    "CargoType": "Money",
                    "RedeliveryString": str(cod_amount),
                }
            ]
        return payload
