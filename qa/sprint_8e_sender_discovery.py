#!/usr/bin/env python3
"""Read-only Nova Poshta sender tuple discovery for Sprint 8E.

No provider or Sellora writes are performed. The report contains only counts,
boolean capability flags and SHA-256 prefixes for provider references.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

NP_API_URL = os.environ.get("NOVA_POSHTA_API_URL", "https://api.novaposhta.ua/v2.0/json/")
OUT = Path("artifacts/sprint-8e/sender-discovery.json")
TIMEOUT = httpx.Timeout(connect=30, read=90, write=90, pool=30)


def digest(value: Any) -> str | None:
    text = str(value or "").strip()
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16] if text else None


def phone_present(value: Any) -> bool:
    digits = re.sub(r"\D", "", str(value or ""))
    return len(digits) >= 10


class Discovery:
    def __init__(self) -> None:
        self.requests = 0
        self.http_5xx = 0
        self.safe_error: str | None = None
        self.candidates: list[dict[str, Any]] = []

    def call(self, model: str, method: str, properties: dict[str, Any]) -> dict[str, Any]:
        payload = {
            "apiKey": os.environ["STAGING_NOVA_POSHTA_API_KEY"],
            "modelName": model,
            "calledMethod": method,
            "methodProperties": properties,
        }
        with httpx.Client(timeout=TIMEOUT, follow_redirects=True, headers={"Connection": "close"}) as client:
            response = client.post(NP_API_URL, json=payload)
        self.requests += 1
        if response.status_code >= 500:
            self.http_5xx += 1
        response.raise_for_status()
        body = response.json()
        if body.get("success") is not True:
            errors = [str(item)[:120] for item in body.get("errors", [])]
            raise RuntimeError(f"Provider directory call {method} failed with {len(errors)} errors")
        return body

    def run_discovery(self) -> None:
        body = self.call(
            "Counterparty",
            "getCounterparties",
            {"CounterpartyProperty": "Sender", "Page": "1"},
        )
        counterparties = [item for item in body.get("data", []) if item.get("Ref")]
        if not counterparties:
            raise RuntimeError("No sender counterparties returned by Nova Poshta")

        for counterparty in counterparties[:20]:
            ref = str(counterparty.get("Ref"))
            contacts_body = self.call(
                "Counterparty",
                "getCounterpartyContactPersons",
                {"Ref": ref, "Page": "1"},
            )
            addresses_body = self.call(
                "Counterparty",
                "getCounterpartyAddresses",
                {"Ref": ref, "CounterpartyProperty": "Sender"},
            )
            contacts = [item for item in contacts_body.get("data", []) if item.get("Ref")]
            addresses = [item for item in addresses_body.get("data", []) if item.get("Ref")]

            contact_summaries = []
            for contact in contacts[:20]:
                contact_summaries.append(
                    {
                        "ref_sha256_prefix": digest(contact.get("Ref")),
                        "description_present": bool(str(contact.get("Description") or "").strip()),
                        "phone_present": phone_present(contact.get("Phones") or contact.get("Phone")),
                        "email_present": bool(str(contact.get("Email") or "").strip()),
                    }
                )

            address_summaries = []
            for address in addresses[:50]:
                description = str(address.get("Description") or "")
                address_type = str(address.get("Type") or address.get("AddressType") or "")
                address_summaries.append(
                    {
                        "ref_sha256_prefix": digest(address.get("Ref")),
                        "city_ref_sha256_prefix": digest(address.get("CityRef")),
                        "description_present": bool(description.strip()),
                        "description_length": len(description),
                        "type_present": bool(address_type.strip()),
                        "type_value": address_type[:50] if address_type else None,
                        "warehouse_like": "warehouse" in address_type.lower()
                        or "відділен" in description.lower()
                        or "warehouse" in description.lower(),
                    }
                )

            usable_contacts = [item for item in contact_summaries if item["phone_present"]]
            usable_addresses = [
                item
                for item in address_summaries
                if item["ref_sha256_prefix"] and item["city_ref_sha256_prefix"]
            ]
            self.candidates.append(
                {
                    "counterparty_ref_sha256_prefix": digest(ref),
                    "description_present": bool(str(counterparty.get("Description") or "").strip()),
                    "counterparty_type_present": bool(str(counterparty.get("CounterpartyType") or "").strip()),
                    "contact_count": len(contacts),
                    "address_count": len(addresses),
                    "usable_contact_count": len(usable_contacts),
                    "usable_address_count": len(usable_addresses),
                    "contacts": contact_summaries,
                    "addresses": address_summaries,
                    "usable_sender_tuple": bool(usable_contacts and usable_addresses),
                }
            )

        if not any(item["usable_sender_tuple"] for item in self.candidates):
            raise RuntimeError("Nova Poshta returned no coherent sender/contact/address tuple")

    def write_report(self) -> None:
        decision = "PASS" if self.safe_error is None else "FAIL"
        report = {
            "sprint": "8E",
            "phase": "sender-discovery-read-only",
            "decision": decision,
            "counterparty_count": len(self.candidates),
            "usable_tuple_count": sum(1 for item in self.candidates if item["usable_sender_tuple"]),
            "candidates": self.candidates,
            "network": {
                "requests": self.requests,
                "provider_writes": 0,
                "http_5xx": self.http_5xx,
            },
            "safe_error": self.safe_error,
            "generated_at": datetime.now(UTC).isoformat(),
        }
        encoded = json.dumps(report, ensure_ascii=False, indent=2)
        for name in ("STAGING_NOVA_POSHTA_API_KEY",):
            secret = os.environ.get(name)
            if secret and secret in encoded:
                report["decision"] = "FAIL"
                report["safe_error"] = f"SANITIZATION_FAILED_{name}"
                encoded = json.dumps(report, ensure_ascii=False, indent=2)
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(encoded, encoding="utf-8")
        print(json.dumps({
            "decision": report["decision"],
            "counterparty_count": report["counterparty_count"],
            "usable_tuple_count": report["usable_tuple_count"],
            "network": report["network"],
            "artifact": str(OUT),
        }))

    def run(self) -> int:
        try:
            if not os.environ.get("STAGING_NOVA_POSHTA_API_KEY"):
                raise RuntimeError("Nova Poshta API key input is missing")
            self.run_discovery()
        except Exception as exc:
            self.safe_error = str(exc)[:500]
        finally:
            self.write_report()
        return 0 if self.safe_error is None else 1


if __name__ == "__main__":
    sys.exit(Discovery().run())
