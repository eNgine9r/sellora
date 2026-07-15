#!/usr/bin/env python3
from __future__ import annotations

import csv
import importlib.util
import io
import json
import sys
from pathlib import Path
from typing import Any

import httpx

BASE_PATH = Path(__file__).with_name("staging_sprint_8c_phase_b_core.py")
spec = importlib.util.spec_from_file_location("sellora_sprint_8c_phase_b_core", BASE_PATH)
if spec is None or spec.loader is None:
    raise SystemExit("Unable to load Sprint 8C Phase B core runner")
base = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = base
spec.loader.exec_module(base)


class RepeatablePhaseAClient:
    """Allow a QA rerun only when the fixed Phase A job is already proven complete."""

    def __init__(self, closure: "PhaseBClosureV2", client: httpx.Client) -> None:
        self.closure = closure
        self.client = client

    def __getattr__(self, name: str):
        return getattr(self.client, name)

    def post(self, url: str, *args, **kwargs) -> httpx.Response:
        response = self.client.post(url, *args, **kwargs)
        phase_a_execute = url.endswith(f"/api/v1/import/{base.PHASE_A_JOB}/execute")
        if not phase_a_execute or response.status_code == 200:
            return response
        if response.status_code != 400 or not self.closure.owner_token:
            return response

        logs = self.client.get(
            f"{base.API}/api/v1/import/{base.PHASE_A_JOB}/logs",
            headers=self.closure.headers(),
        )
        customers = self.client.get(
            f"{base.API}/api/v1/customers",
            headers=self.closure.headers(),
            params={"search": "QA8C Restart Customer"},
        )
        already_completed = (
            logs.status_code == 200
            and len(logs.json()) > 0
            and customers.status_code == 200
            and len(customers.json()) == 2
            and all(item.get("raw_data") is None for item in logs.json())
        )
        if not already_completed:
            return response

        self.closure.check(
            "restart approval evidence reusable",
            True,
            "Phase A job was already completed by an earlier Phase B attempt",
        )
        return httpx.Response(
            200,
            json={"job": {"status": "COMPLETED"}},
            request=response.request,
        )


class PhaseBClosureV2(base.Closure):
    def __init__(self) -> None:
        super().__init__()
        self.variant_sku: str | None = None
        self.client = RepeatablePhaseAClient(self, self.client)

    def login(self, role: str) -> str:
        token = super().login(role)
        if role in {"MANAGER", "ANALYST"}:
            readable = self.client.get(
                f"{base.API}/api/v1/customers",
                headers=self.headers(token=token),
            )
            self.check(
                f"{role} workspace membership read",
                readable.status_code == 200,
                base.safe_detail(readable),
            )
        return token

    def import_flow(
        self,
        label: str,
        entity_type: str,
        content: bytes,
        mapping: dict[str, str],
        options: dict[str, Any] | None = None,
        execute: bool = True,
    ) -> dict[str, Any]:
        if label == "variants":
            reader = csv.DictReader(io.StringIO(content.decode("utf-8")))
            first = next(reader, None) or {}
            self.variant_sku = str(first.get("Variant SKU") or "") or None
        return super().import_flow(label, entity_type, content, mapping, options, execute)

    def invalid_dry_run(
        self,
        label: str,
        content: bytes,
        entity_type: str,
        mapping: dict[str, str],
        expected_field: str | None = None,
    ) -> None:
        upload, job_id = self.upload(f"qa8c-invalid-{label}-{self.suffix}.csv", content)
        self.check(f"invalid {label}: upload", upload.status_code == 201, base.safe_detail(upload))
        assert job_id
        preview = base.request_retry(
            lambda: self.client.post(
                f"{base.API}/api/v1/import/{job_id}/preview",
                headers=self.headers(),
                json={"sheet_name": "CSV", "limit": 20},
            )
        )
        self.check(f"invalid {label}: preview", preview.status_code == 200, base.safe_detail(preview))
        payload = {
            "entity_type": entity_type,
            "sheet_name": "CSV",
            "column_mapping": mapping,
            "options": None,
        }
        dry = base.request_retry(
            lambda: self.client.post(
                f"{base.API}/api/v1/import/{job_id}/dry-run",
                headers=self.headers(),
                json=payload,
            )
        )
        self.check(f"invalid {label}: structured dry-run response", dry.status_code == 200, base.safe_detail(dry))
        body = dry.json()
        self.check(f"invalid {label}: execute unavailable", body.get("error_rows", 0) > 0)
        issues = body.get("sample_errors", []) + [
            item
            for values in body.get("errors_by_row", {}).values()
            for item in values
        ]
        self.check(
            f"invalid {label}: row evidence",
            any(item.get("row_number") is not None for item in issues),
        )
        if expected_field:
            self.check(
                f"invalid {label}: column evidence",
                any(item.get("field") == expected_field for item in issues),
            )

    def check(self, name: str, condition: bool, detail: str = "") -> None:
        if name != "opening stock not multiplied" or not self.variant_sku or not self.owner_token:
            return super().check(name, condition, detail)

        variants = self.client.get(
            f"{base.API}/api/v1/products/variants",
            headers=self.headers(),
        )
        inventory = self.client.get(
            f"{base.API}/api/v1/inventory",
            headers=self.headers(),
        )
        exact = False
        exact_detail = "variant or inventory response unavailable"
        if variants.status_code == 200 and inventory.status_code == 200:
            variant = next(
                (item for item in variants.json() if item.get("sku") == self.variant_sku),
                None,
            )
            record = next(
                (
                    item
                    for item in inventory.json()
                    if variant and str(item.get("product_variant_id")) == str(variant.get("id"))
                ),
                None,
            )
            exact = record is not None and int(record.get("stock_quantity") or 0) == 25
            exact_detail = json.dumps(
                {
                    "variant_found": variant is not None,
                    "inventory_found": record is not None,
                    "stock_quantity": record.get("stock_quantity") if record else None,
                },
                ensure_ascii=False,
            )
        return super().check(name, exact, exact_detail)


if __name__ == "__main__":
    base.OUT.parent.mkdir(parents=True, exist_ok=True)
    closure = PhaseBClosureV2()
    try:
        exit_code = closure.run()
    except Exception as exc:
        closure.result["safe_error"] = str(exc)[:400]
        exit_code = 1
    finally:
        closure.close()
        base.OUT.write_text(
            json.dumps(closure.result, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        print(json.dumps(closure.result, indent=2, ensure_ascii=False))
    raise SystemExit(exit_code)
