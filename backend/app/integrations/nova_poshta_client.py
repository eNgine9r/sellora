from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import json
import re
from typing import Any
from urllib import error, request

from app.core.config import get_settings


class NovaPoshtaClientError(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        code: str = "NOVA_POSHTA_PROVIDER_ERROR",
        retryable: bool = False,
        ambiguous: bool = False,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.retryable = retryable
        self.ambiguous = ambiguous


@dataclass(frozen=True)
class NovaPoshtaCity:
    ref: str
    description: str


@dataclass(frozen=True)
class NovaPoshtaWarehouse:
    ref: str
    description: str
    number: str | None = None


@dataclass(frozen=True)
class NovaPoshtaDocumentResult:
    tracking_number: str
    document_ref: str
    status: str | None = None


class NovaPoshtaClient:
    def __init__(self, api_key: str, base_url: str | None = None, timeout_seconds: int = 10) -> None:
        self.api_key = api_key
        self.base_url = base_url or get_settings().nova_poshta_api_url
        self.timeout_seconds = timeout_seconds

    def _safe_rejection_code(self, body: dict[str, Any]) -> str:
        """Return a bounded, credential-safe provider validation code.

        Nova Poshta returns actionable validation messages in ``errors`` while the
        previous client collapsed every rejection to one generic code. Preserve
        only the first sanitized message so staging/runtime evidence can identify
        an invalid field without exposing API keys, phones, UUIDs or document IDs.
        The result is bounded to the database ``String(120)`` contract.
        """
        values = body.get("errors") or body.get("warnings") or body.get("info") or []
        if not isinstance(values, list):
            values = [values]
        detail = next((str(value).strip() for value in values if str(value).strip()), "")
        if not detail:
            return "NOVA_POSHTA_PROVIDER_REJECTED"
        detail = detail.replace(self.api_key, "[REDACTED]")
        detail = re.sub(
            r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b",
            "[VALUE]",
            detail,
        )
        detail = re.sub(r"\b\d{7,}\b", "[VALUE]", detail)
        detail = re.sub(r"\s+", " ", detail).strip()
        prefix = "NOVA_POSHTA_PROVIDER_REJECTED::"
        return (prefix + detail)[:120]

    def _call(
        self,
        model: str,
        method: str,
        properties: dict[str, Any] | None = None,
        *,
        ambiguous_on_transport: bool = False,
    ) -> dict[str, Any]:
        payload = json.dumps(
            {
                "apiKey": self.api_key,
                "modelName": model,
                "calledMethod": method,
                "methodProperties": properties or {},
            }
        ).encode("utf-8")
        req = request.Request(
            self.base_url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=self.timeout_seconds) as response:
                body = json.loads(response.read().decode("utf-8"))
        except (error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise NovaPoshtaClientError(
                "Nova Poshta transport request failed",
                code=(
                    "NOVA_POSHTA_PROVIDER_RESPONSE_AMBIGUOUS"
                    if ambiguous_on_transport
                    else "NOVA_POSHTA_PROVIDER_UNAVAILABLE"
                ),
                retryable=True,
                ambiguous=ambiguous_on_transport,
            ) from exc
        if not body.get("success"):
            raise NovaPoshtaClientError(
                "Nova Poshta rejected the request",
                code=self._safe_rejection_code(body),
                retryable=False,
                ambiguous=False,
            )
        return body

    def test_connection(self) -> bool:
        self._call("Address", "getAreas", {})
        return True

    def search_cities(self, query: str, limit: int = 20) -> list[NovaPoshtaCity]:
        body = self._call("Address", "searchSettlements", {"CityName": query, "Limit": str(limit)})
        addresses = body.get("data", [{}])[0].get("Addresses", []) if body.get("data") else []
        return [
            NovaPoshtaCity(
                ref=str(item.get("DeliveryCity") or item.get("Ref") or ""),
                description=str(item.get("Present") or item.get("Description") or ""),
            )
            for item in addresses
            if item.get("DeliveryCity") or item.get("Ref")
        ]

    def search_warehouses(
        self,
        city_ref: str,
        query: str | None = None,
        limit: int = 50,
    ) -> list[NovaPoshtaWarehouse]:
        props = {"CityRef": city_ref, "Limit": str(limit)}
        if query:
            props["FindByString"] = query
        body = self._call("Address", "getWarehouses", props)
        return [
            NovaPoshtaWarehouse(
                ref=str(item.get("Ref") or ""),
                description=str(item.get("Description") or ""),
                number=str(item.get("Number")) if item.get("Number") else None,
            )
            for item in body.get("data", [])
            if item.get("Ref")
        ]

    def counterparty_exists(self, counterparty_ref: str) -> bool:
        body = self._call("Counterparty", "getCounterparties", {"Ref": counterparty_ref})
        return any(str(item.get("Ref") or "") == counterparty_ref for item in body.get("data", []))

    def contact_belongs_to_counterparty(self, counterparty_ref: str, contact_ref: str) -> bool:
        body = self._call("ContactPerson", "getCounterpartyContactPersons", {"Ref": counterparty_ref})
        return any(str(item.get("Ref") or "") == contact_ref for item in body.get("data", []))

    def warehouse_belongs_to_city(self, city_ref: str, warehouse_ref: str) -> bool:
        return any(item.ref == warehouse_ref for item in self.search_warehouses(city_ref, None, 500))

    def sender_address_belongs_to_sender(self, sender_ref: str, address_ref: str) -> bool:
        body = self._call("Address", "getCounterpartyAddresses", {"Ref": sender_ref, "CounterpartyProperty": "Sender"})
        return any(str(item.get("Ref") or "") == address_ref for item in body.get("data", []))

    def create_internet_document(self, payload: dict[str, Any]) -> NovaPoshtaDocumentResult:
        body = self._call(
            "InternetDocument",
            "save",
            payload,
            ambiguous_on_transport=True,
        )
        item = body.get("data", [{}])[0] if body.get("data") else {}
        return NovaPoshtaDocumentResult(
            tracking_number=str(item.get("IntDocNumber") or ""),
            document_ref=str(item.get("Ref") or ""),
            status="CREATED",
        )

    def find_internet_document(
        self,
        marker: str,
        date_from: datetime,
        date_to: datetime,
    ) -> NovaPoshtaDocumentResult | None:
        body = self._call(
            "InternetDocument",
            "getDocumentList",
            {
                "DateTimeFrom": date_from.strftime("%d.%m.%Y"),
                "DateTimeTo": date_to.strftime("%d.%m.%Y"),
                "GetFullList": "1",
            },
        )
        matches: list[NovaPoshtaDocumentResult] = []
        for item in body.get("data", []):
            searchable = " ".join(
                str(item.get(key) or "")
                for key in (
                    "Description",
                    "AdditionalInformation",
                    "AdditionalInformationEW",
                    "InfoRegClientBarcodes",
                )
            )
            if marker not in searchable:
                continue
            tracking_number = str(item.get("IntDocNumber") or item.get("Number") or "")
            document_ref = str(item.get("Ref") or "")
            if tracking_number and document_ref:
                matches.append(
                    NovaPoshtaDocumentResult(
                        tracking_number=tracking_number,
                        document_ref=document_ref,
                        status=str(item.get("StateName") or item.get("Status") or "") or None,
                    )
                )
        if len(matches) > 1:
            raise NovaPoshtaClientError(
                "Multiple Nova Poshta documents matched the reconciliation marker",
                code="NOVA_POSHTA_RECONCILIATION_MULTIPLE_MATCHES",
                ambiguous=True,
            )
        return matches[0] if matches else None

    def get_document_status(self, tracking_number: str) -> str | None:
        body = self._call(
            "TrackingDocument",
            "getStatusDocuments",
            {"Documents": [{"DocumentNumber": tracking_number}]},
        )
        item = body.get("data", [{}])[0] if body.get("data") else {}
        return str(item.get("Status") or item.get("StatusCode") or "") or None
