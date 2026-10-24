from __future__ import annotations

from datetime import UTC, datetime

from app.integrations.nova_poshta_client import NovaPoshtaClientError
from app.repositories.nova_poshta_cargo_repository import NovaPoshtaCargoRepository
from app.services.nova_poshta_cargo_description import accessory_cargo_description
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
        cargo_description = (settings.get("cargo_description") or "Товари").strip() or "Товари"
        if settings.get("cargo_description_mode", "STATIC") == "AUTO_ACCESSORIES":
            categories = NovaPoshtaCargoRepository(self.db).list_order_categories(
                shipment.workspace_id, shipment.order_id
            )
            cargo_description = accessory_cargo_description(categories) or cargo_description
        payload = {
            "PayerType": "Recipient",
            "PaymentMethod": "Cash",
            "DateTime": datetime.now(UTC).strftime("%d.%m.%Y"),
            "CargoType": "Parcel",
            "VolumeGeneral": "0.001",
            "Weight": "0.5",
            "ServiceType": "WarehouseWarehouse",
            "SeatsAmount": "1",
            "Description": cargo_description,
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
            mode = settings.get("cod_payment_mode", "MONEY_RETURN")
            if mode == "PAYMENT_CONTROL":
                # FOP/business payment to the sender account; mutually exclusive
                # with a backward money-delivery request.
                payload["AfterpaymentOnGoodsCost"] = str(cod_amount)
            elif mode == "MONEY_RETURN":
                payload["BackwardDeliveryData"] = [
                    {
                        "PayerType": "Recipient",
                        "CargoType": "Money",
                        "RedeliveryString": str(cod_amount),
                    }
                ]
            else:
                raise NovaPoshtaServiceError("NOVA_POSHTA_COD_PAYMENT_MODE_INVALID")
        return payload
