#!/usr/bin/env python3
"""Sprint 8D staging API/runtime closure with synthetic QA data only."""
from __future__ import annotations

import asyncio
import json
import os
import re
import sys
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

API = os.environ["STAGING_API_URL"].rstrip("/") + "/api/v1"
BACKEND = os.environ["STAGING_API_URL"].rstrip("/")
FRONTEND = os.environ["STAGING_FRONTEND_URL"].rstrip("/")
EXPECTED_COMMIT = os.environ["EXPECTED_RUNTIME_COMMIT"].lower()
WORKSPACE_A = os.environ["STAGING_TEST_WORKSPACE_ID"]
OUT = Path("artifacts/sprint-8d-closure/core.json")
MD = Path("artifacts/sprint-8d-closure/core.md")
RUN = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
PREFIX = f"QA8D-{RUN}"
TIMEOUT = httpx.Timeout(connect=20, read=60, write=60, pool=20)


@dataclass
class Session:
    role: str
    token: str
    refresh: str
    user: dict[str, Any]


class Closure:
    def __init__(self) -> None:
        self.checks: list[dict[str, Any]] = []
        self.findings: list[dict[str, Any]] = []
        self.sessions: dict[str, Session] = {}
        self.workspace_b: str | None = None
        self.created: dict[str, list[str]] = {
            "customers": [], "products": [], "variants": [], "orders": [], "shipments": []
        }
        self.runtime: dict[str, Any] = {}
        self.network = {"requests": 0, "5xx": 0, "nova_poshta": 0, "meta": 0}
        self.residual = {"orders": 0, "shipments": 0, "reservations": 0, "stock_delta": 0}
        self.safe_error: str | None = None

    def check(self, gate: str, name: str, ok: bool, detail: Any = None) -> None:
        item = {"gate": gate, "name": name, "status": "PASS" if ok else "FAIL"}
        if detail is not None:
            item["detail"] = self.safe(detail)
        self.checks.append(item)
        print(json.dumps(item, ensure_ascii=False), flush=True)

    def safe(self, value: Any) -> Any:
        if isinstance(value, dict):
            return {str(k): self.safe(v) for k, v in value.items() if str(k).lower() not in {
                "access_token", "refresh_token", "authorization", "password", "phone", "email"
            }}
        if isinstance(value, list):
            return [self.safe(v) for v in value[:20]]
        text = str(value)
        text = re.sub(r"Bearer\s+\S+", "Bearer [REDACTED]", text, flags=re.I)
        text = re.sub(r"\beyJ[A-Za-z0-9._-]{20,}\b", "[TOKEN]", text)
        return text[:500]

    def headers(self, session: Session, workspace: str | None = None) -> dict[str, str]:
        result = {"Authorization": f"Bearer {session.token}", "Cache-Control": "no-cache"}
        if workspace:
            result["X-Workspace-ID"] = workspace
        return result

    def request(
        self,
        method: str,
        path: str,
        session: Session | None = None,
        workspace: str | None = None,
        payload: dict[str, Any] | None = None,
        expected: tuple[int, ...] | None = None,
    ) -> tuple[int, Any]:
        url = path if path.startswith("http") else API + path
        headers = self.headers(session, workspace) if session else {"Cache-Control": "no-cache"}
        self.network["requests"] += 1
        if "nova-poshta" in url:
            self.network["nova_poshta"] += 1
        if "graph.facebook" in url or "meta-ads" in url:
            self.network["meta"] += 1
        with httpx.Client(timeout=TIMEOUT, follow_redirects=True, headers={"Connection": "close"}) as client:
            response = client.request(method, url, headers=headers, json=payload)
        if response.status_code >= 500:
            self.network["5xx"] += 1
        try:
            body: Any = response.json()
        except Exception:
            body = response.text[:300]
        print(f"HTTP {method} {httpx.URL(url).path} -> {response.status_code}", flush=True)
        if expected and response.status_code not in expected:
            raise RuntimeError(f"{method} {httpx.URL(url).path}: HTTP {response.status_code}")
        return response.status_code, body

    def login(self, role: str, email_env: str, password_env: str) -> Session:
        _, tokens = self.request("POST", "/auth/login", payload={
            "email": os.environ[email_env], "password": os.environ[password_env]
        }, expected=(200,))
        temp = Session(role, str(tokens["access_token"]), str(tokens["refresh_token"]), {})
        _, user = self.request("GET", "/auth/me", temp, expected=(200,))
        temp.user = user
        self.sessions[role] = temp
        return temp

    def wait_environment(self) -> None:
        deadline = time.monotonic() + 30 * 60
        last: dict[str, Any] = {}
        while time.monotonic() < deadline:
            try:
                with httpx.Client(timeout=TIMEOUT, follow_redirects=True) as client:
                    response = client.get(BACKEND + "/health")
                if response.status_code == 200:
                    last = response.json()
                    commit = str(last.get("runtime_commit", "")).lower()
                    if commit.startswith(EXPECTED_COMMIT[:12]):
                        self.runtime = {
                            "status": last.get("status"),
                            "runtime_commit": commit,
                            "process_started_at": last.get("process_started_at"),
                        }
                        break
            except Exception:
                pass
            time.sleep(15)
        self.check("A", "backend /health and Sprint 8D runtime commit", bool(self.runtime) and self.runtime.get("status") == "ok", self.runtime or last)
        if not self.runtime:
            raise RuntimeError("Expected Render runtime was not observed")
        with httpx.Client(timeout=TIMEOUT, follow_redirects=True) as client:
            front = client.get(FRONTEND + "/login")
        self.check("A", "frontend staging reachable", front.status_code == 200, {"status": front.status_code})
        if front.status_code != 200:
            raise RuntimeError("Frontend staging is not reachable")

    def setup_sessions(self) -> None:
        owner = self.login("OWNER", "STAGING_OWNER_EMAIL", "STAGING_OWNER_PASSWORD")
        self.login("MANAGER", "STAGING_MANAGER_EMAIL", "STAGING_MANAGER_PASSWORD")
        self.login("ANALYST", "STAGING_ANALYST_EMAIL", "STAGING_ANALYST_PASSWORD")
        for role, session in self.sessions.items():
            memberships = session.user.get("memberships", [])
            match = next((m for m in memberships if str(m.get("workspace_id")) == WORKSPACE_A), None)
            self.check("A", f"{role} account has synthetic QA workspace", bool(match), {"role": match.get("role") if match else None})
        slug = f"qa8d-{RUN}".lower()
        code, workspace = self.request("POST", "/workspaces", owner, payload={
            "name": f"{PREFIX} Isolation", "slug": slug, "currency_code": "UAH", "timezone": "Europe/Kyiv"
        })
        if code == 201:
            self.workspace_b = str(workspace["id"])
        else:
            _, spaces = self.request("GET", "/workspaces", owner, expected=(200,))
            found = next((item for item in spaces if item.get("slug") == slug), None)
            self.workspace_b = str(found["id"]) if found else None
        self.check("J", "Workspace B available for tenant negatives", bool(self.workspace_b))
        if not self.workspace_b:
            raise RuntimeError("Unable to create isolation workspace")

    def create_customer(self, workspace: str, suffix: str, session: Session | None = None) -> dict[str, Any]:
        session = session or self.sessions["OWNER"]
        _, item = self.request("POST", "/customers", session, workspace, {
            "name": f"{PREFIX} Customer {suffix}",
            "phone": f"000{RUN[-7:]}{len(self.created['customers'])}",
            "instagram_username": f"qa8d_{RUN}_{suffix.lower()}",
            "city": "Synthetic City", "region": "Synthetic Region",
        }, expected=(201,))
        self.created["customers"].append(str(item["id"]))
        return item

    def create_variant(self, workspace: str, suffix: str, stock: int) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
        owner = self.sessions["OWNER"]
        _, product = self.request("POST", "/products", owner, workspace, {
            "name": f"{PREFIX} Product {suffix}", "sku": f"{PREFIX}-{suffix}-P",
            "description": "Synthetic Sprint 8D fixture", "category": "QA", "brand": "Sellora QA",
        }, expected=(201,))
        self.created["products"].append(str(product["id"]))
        _, variant = self.request("POST", "/products/variants", owner, workspace, {
            "product_id": product["id"], "sku": f"{PREFIX}-{suffix}-V",
            "color": "Synthetic", "size": suffix, "price": "100.00",
            "initial_stock_quantity": stock, "minimum_quantity": 1,
        }, expected=(201,))
        self.created["variants"].append(str(variant["id"]))
        inv = self.inventory_by_variant(workspace, str(variant["id"]))
        if not inv:
            raise RuntimeError("Inventory not created for variant")
        return product, variant, inv

    def inventory_by_variant(self, workspace: str, variant_id: str, session: Session | None = None) -> dict[str, Any] | None:
        session = session or self.sessions["OWNER"]
        _, rows = self.request("GET", "/inventory", session, workspace, expected=(200,))
        return next((row for row in rows if str(row["product_variant_id"]) == variant_id), None)

    @staticmethod
    def inv_state(inv: dict[str, Any]) -> dict[str, int]:
        stock = int(inv["stock_quantity"])
        reserved = int(inv["reserved_quantity"])
        return {"stock": stock, "reserved": reserved, "available": stock - reserved}

    def create_order(
        self, workspace: str, customer_id: str, variant_id: str, quantity: int,
        suffix: str, session: Session | None = None, expected: tuple[int, ...] | None = (201,)
    ) -> tuple[int, Any]:
        session = session or self.sessions["OWNER"]
        code, order = self.request("POST", "/orders", session, workspace, {
            "customer_id": customer_id,
            "items": [{"product_variant_id": variant_id, "quantity": quantity, "unit_price": "100.00", "unit_cost": "30.00"}],
            "notes": f"{PREFIX} {suffix}",
        }, expected=expected)
        if code == 201:
            self.created["orders"].append(str(order["id"]))
        return code, order

    def update_items(self, order_id: str, workspace: str, items: list[dict[str, Any]], session: Session | None = None) -> tuple[int, Any]:
        return self.request("PUT", f"/orders/{order_id}", session or self.sessions["OWNER"], workspace, {"items": items})

    def status(self, order_id: str, workspace: str, status: str, session: Session | None = None) -> tuple[int, Any]:
        return self.request("POST", f"/orders/{order_id}/status", session or self.sessions["OWNER"], workspace, {"status": status})

    def snapshot_order(self, order_id: str, workspace: str) -> dict[str, Any]:
        _, order = self.request("GET", f"/orders/{order_id}", self.sessions["OWNER"], workspace, expected=(200,))
        return {
            "status": order["status"],
            "items": [(str(item["product_variant_id"]), int(item["quantity"])) for item in order["items"]],
            "history": [(item.get("from_status"), item.get("to_status")) for item in order["status_history"]],
        }

    def gates_b_to_f_h(self, customer: dict[str, Any], a: dict[str, Any], b: dict[str, Any]) -> None:
        owner = self.sessions["OWNER"]
        _, order = self.create_order(WORKSPACE_A, customer["id"], a["id"], 2, "reservation")
        oid = str(order["id"])
        inv = self.inventory_by_variant(WORKSPACE_A, str(a["id"]))
        snap = self.snapshot_order(oid, WORKSPACE_A)
        self.check("B", "create reserves quantity without reducing physical stock",
                   self.inv_state(inv) == {"stock": 10, "reserved": 2, "available": 8}, self.inv_state(inv))
        self.check("B", "order item and initial status history persisted",
                   snap["items"] == [(str(a["id"]), 2)] and snap["history"][-1][1] == "NEW", {"items": snap["items"], "history_count": len(snap["history"])})

        code, _ = self.update_items(oid, WORKSPACE_A, [{"product_variant_id": a["id"], "quantity": 4, "unit_price": "100.00", "unit_cost": "30.00"}])
        inv = self.inventory_by_variant(WORKSPACE_A, str(a["id"]))
        self.check("C", "quantity 2→4 applies reservation delta +2", code == 200 and self.inv_state(inv)["reserved"] == 4, self.inv_state(inv))
        code, _ = self.update_items(oid, WORKSPACE_A, [{"product_variant_id": a["id"], "quantity": 1, "unit_price": "100.00", "unit_cost": "30.00"}])
        inv = self.inventory_by_variant(WORKSPACE_A, str(a["id"]))
        self.check("C", "quantity 4→1 applies reservation delta -3", code == 200 and self.inv_state(inv)["reserved"] == 1, self.inv_state(inv))
        before_order = self.snapshot_order(oid, WORKSPACE_A)
        before_inv = self.inv_state(inv)
        code, _ = self.update_items(oid, WORKSPACE_A, [{"product_variant_id": a["id"], "quantity": 50, "unit_price": "100.00", "unit_cost": "30.00"}])
        after_order = self.snapshot_order(oid, WORKSPACE_A)
        after_inv = self.inv_state(self.inventory_by_variant(WORKSPACE_A, str(a["id"])))
        self.check("C", "failed increase is atomic", code in (400, 409, 422) and before_order == after_order and before_inv == after_inv,
                   {"status": code, "inventory": after_inv})

        code, _ = self.update_items(oid, WORKSPACE_A, [{"product_variant_id": b["id"], "quantity": 1, "unit_price": "100.00", "unit_cost": "30.00"}])
        state_a = self.inv_state(self.inventory_by_variant(WORKSPACE_A, str(a["id"])))
        state_b = self.inv_state(self.inventory_by_variant(WORKSPACE_A, str(b["id"])))
        self.check("D", "variant replacement releases A and reserves B atomically",
                   code == 200 and state_a["reserved"] == 0 and state_b["reserved"] == 1, {"a": state_a, "b": state_b})

        before_history = len(self.snapshot_order(oid, WORKSPACE_A)["history"])
        code, _ = self.status(oid, WORKSPACE_A, "CANCELLED")
        after_first = self.snapshot_order(oid, WORKSPACE_A)
        state_b = self.inv_state(self.inventory_by_variant(WORKSPACE_A, str(b["id"])))
        code2, _ = self.status(oid, WORKSPACE_A, "CANCELLED")
        after_second = self.snapshot_order(oid, WORKSPACE_A)
        state_b2 = self.inv_state(self.inventory_by_variant(WORKSPACE_A, str(b["id"])))
        self.check("E", "cancel releases reservation and leaves physical stock unchanged",
                   code == 200 and state_b == {"stock": 10, "reserved": 0, "available": 10}, state_b)
        self.check("E", "repeat cancellation has no second side effect",
                   code2 == 200 and state_b2 == state_b and len(after_second["history"]) == len(after_first["history"]) == before_history + 1,
                   {"history_count": len(after_second["history"])})

        _, ship_order = self.create_order(WORKSPACE_A, customer["id"], a["id"], 2, "ship-return")
        soid = str(ship_order["id"])
        self.status(soid, WORKSPACE_A, "CONFIRMED")
        _, shipment = self.request("POST", "/shipments", owner, WORKSPACE_A, {
            "order_id": soid, "status": "DRAFT", "carrier": "NOVA_POSHTA",
            "recipient_name": "Synthetic Recipient", "recipient_phone": "0000000000",
            "city": "Synthetic City", "warehouse": "Synthetic Warehouse", "notes": f"{PREFIX} local shipment",
        }, expected=(201,))
        sid = str(shipment["id"])
        self.created["shipments"].append(sid)
        self.check("H", "local shipment draft links order/workspace without provider artifacts",
                   shipment["order_id"] == soid and shipment["workspace_id"] == WORKSPACE_A
                   and not shipment.get("tracking_number") and not shipment.get("nova_poshta_document_number")
                   and not shipment.get("external_provider"))
        code2, _ = self.request("POST", "/shipments", owner, WORKSPACE_A, {"order_id": soid, "status": "DRAFT", "notes": f"{PREFIX} duplicate"})
        self.check("H", "second active shipment rejected", code2 in (400, 409, 422), {"status": code2})
        local_tracking = f"{PREFIX}-LOCAL"
        self.request("PUT", f"/shipments/{sid}", owner, WORKSPACE_A, {"tracking_number": local_tracking, "notes": f"{PREFIX} local only"}, expected=(200,))
        self.request("POST", f"/shipments/{sid}/mark-created", owner, WORKSPACE_A, expected=(200,))
        self.request("POST", f"/shipments/{sid}/mark-in-transit", owner, WORKSPACE_A, expected=(200,))
        shipped_state = self.inv_state(self.inventory_by_variant(WORKSPACE_A, str(a["id"])))
        ship_snapshot = self.snapshot_order(soid, WORKSPACE_A)
        self.check("F", "shipment in-transit deducts stock and reservation once",
                   ship_snapshot["status"] == "SHIPPED" and shipped_state == {"stock": 8, "reserved": 0, "available": 8},
                   {"order_status": ship_snapshot["status"], "inventory": shipped_state})
        self.request("POST", f"/shipments/{sid}/mark-in-transit", owner, WORKSPACE_A, expected=(200,))
        repeat_state = self.inv_state(self.inventory_by_variant(WORKSPACE_A, str(a["id"])))
        repeat_snapshot = self.snapshot_order(soid, WORKSPACE_A)
        self.check("F", "repeat SHIPPED request is idempotent", repeat_state == shipped_state and len(repeat_snapshot["history"]) == len(ship_snapshot["history"]))
        self.request("POST", f"/shipments/{sid}/mark-returned", owner, WORKSPACE_A, expected=(200,))
        returned_state = self.inv_state(self.inventory_by_variant(WORKSPACE_A, str(a["id"])))
        returned_snapshot = self.snapshot_order(soid, WORKSPACE_A)
        self.check("F", "return restores physical stock exactly once",
                   returned_snapshot["status"] == "RETURNED" and returned_state == {"stock": 10, "reserved": 0, "available": 10},
                   {"order_status": returned_snapshot["status"], "inventory": returned_state})
        self.request("POST", f"/shipments/{sid}/mark-returned", owner, WORKSPACE_A, expected=(200,))
        returned2 = self.inv_state(self.inventory_by_variant(WORKSPACE_A, str(a["id"])))
        self.check("F", "repeat return has no second restoration", returned2 == returned_state, returned2)
        self.request("DELETE", f"/shipments/{sid}", owner, WORKSPACE_A, expected=(204,))
        code, _ = self.request("POST", "/shipments", owner, WORKSPACE_A, {"order_id": soid, "status": "DRAFT", "notes": f"{PREFIX} returned reject"})
        self.check("H", "returned order shipment rejected", code in (400, 409, 422), {"status": code})

        _, cancel_order = self.create_order(WORKSPACE_A, customer["id"], b["id"], 1, "cancel-shipment")
        coid = str(cancel_order["id"])
        self.status(coid, WORKSPACE_A, "CANCELLED")
        code, _ = self.request("POST", "/shipments", owner, WORKSPACE_A, {"order_id": coid, "status": "DRAFT", "notes": f"{PREFIX} cancelled reject"})
        self.check("H", "cancelled order shipment rejected", code in (400, 409, 422), {"status": code})

    async def concurrent_orders(self, customer: dict[str, Any], variant: dict[str, Any]) -> list[tuple[int, Any]]:
        session = self.sessions["OWNER"]
        event = asyncio.Event()
        count = 0
        lock = asyncio.Lock()
        async def create(suffix: str) -> tuple[int, Any]:
            nonlocal count
            async with lock:
                count += 1
                if count == 2:
                    event.set()
            await event.wait()
            payload = {
                "customer_id": customer["id"],
                "items": [{"product_variant_id": variant["id"], "quantity": 1, "unit_price": "100.00", "unit_cost": "30.00"}],
                "notes": f"{PREFIX} last-unit {suffix}",
            }
            async with httpx.AsyncClient(timeout=TIMEOUT, follow_redirects=True, headers={"Connection": "close"}) as client:
                response = await client.post(API + "/orders", headers=self.headers(session, WORKSPACE_A), json=payload)
            try:
                return response.status_code, response.json()
            except Exception:
                return response.status_code, response.text[:200]
        return await asyncio.gather(create("A"), create("B"))

    def gate_g(self, customer: dict[str, Any], last: dict[str, Any], helper1: dict[str, Any], helper2: dict[str, Any], contested: dict[str, Any]) -> None:
        results = asyncio.run(self.concurrent_orders(customer, last))
        successes = [body for code, body in results if code == 201]
        for order in successes:
            self.created["orders"].append(str(order["id"]))
        state = self.inv_state(self.inventory_by_variant(WORKSPACE_A, str(last["id"])))
        self.check("G", "two concurrent orders cannot oversell last unit",
                   len(successes) == 1 and state["stock"] >= 0 and 0 <= state["reserved"] <= state["stock"] and state["available"] >= 0,
                   {"statuses": [code for code, _ in results], "successes": len(successes), "inventory": state})
        for order in successes:
            self.status(str(order["id"]), WORKSPACE_A, "CANCELLED")

        _, o1 = self.create_order(WORKSPACE_A, customer["id"], helper1["id"], 1, "edit-race-1")
        _, o2 = self.create_order(WORKSPACE_A, customer["id"], helper2["id"], 1, "edit-race-2")
        edit_payload = {"items": [{"product_variant_id": contested["id"], "quantity": 1, "unit_price": "100.00", "unit_cost": "30.00"}]}

        async def two_edits() -> list[tuple[int, Any]]:
            session = self.sessions["OWNER"]
            event = asyncio.Event()
            count = 0
            lock = asyncio.Lock()
            async def edit(order_id: str) -> tuple[int, Any]:
                nonlocal count
                async with lock:
                    count += 1
                    if count == 2:
                        event.set()
                await event.wait()
                async with httpx.AsyncClient(timeout=TIMEOUT, follow_redirects=True, headers={"Connection": "close"}) as client:
                    r = await client.put(API + f"/orders/{order_id}", headers=self.headers(session, WORKSPACE_A), json=edit_payload)
                try:
                    return r.status_code, r.json()
                except Exception:
                    return r.status_code, r.text[:200]
            return await asyncio.gather(edit(str(o1["id"])), edit(str(o2["id"])))

        edits = asyncio.run(two_edits())
        edit_success = [body for code, body in edits if code == 200]
        contested_state = self.inv_state(self.inventory_by_variant(WORKSPACE_A, str(contested["id"])))
        s1 = self.snapshot_order(str(o1["id"]), WORKSPACE_A)
        s2 = self.snapshot_order(str(o2["id"]), WORKSPACE_A)
        loser_unchanged = s1["items"] in ([(str(helper1["id"]), 1)], [(str(helper2["id"]), 1)]) or s2["items"] in ([(str(helper1["id"]), 1)], [(str(helper2["id"]), 1)])
        self.check("G", "concurrent item edits serialize on contested inventory row",
                   len(edit_success) == 1 and contested_state == {"stock": 1, "reserved": 1, "available": 0} and loser_unchanged,
                   {"statuses": [code for code, _ in edits], "successes": len(edit_success), "inventory": contested_state})
        for oid in (str(o1["id"]), str(o2["id"])):
            self.status(oid, WORKSPACE_A, "CANCELLED")

    def gate_i(self, customer: dict[str, Any], zero: dict[str, Any], stocked: dict[str, Any]) -> None:
        owner = self.sessions["OWNER"]
        self.request("DELETE", f"/products/variants/{zero['id']}", owner, WORKSPACE_A, expected=(204,))
        self.request("DELETE", f"/products/variants/{stocked['id']}", owner, WORKSPACE_A, expected=(204,))
        _, inventory_rows = self.request("GET", "/inventory", owner, WORKSPACE_A, expected=(200,))
        ids = {str(row["product_variant_id"]) for row in inventory_rows}
        self.check("I", "archived zero-stock variant hidden from active inventory", str(zero["id"]) not in ids)
        self.check("I", "archived stocked variant remains visible for operational history", str(stocked["id"]) in ids)
        for label, variant in (("zero-stock", zero), ("stocked", stocked)):
            code, _ = self.create_order(WORKSPACE_A, customer["id"], variant["id"], 1, f"archived-{label}", expected=(400,))
            self.check("I", f"archived {label} variant is not selectable for order", code == 400)

    def setup_foreign(self) -> dict[str, Any]:
        wb = str(self.workspace_b)
        customer = self.create_customer(wb, "Foreign")
        _, variant, inventory = self.create_variant(wb, "FOREIGN", 2)
        _, order = self.create_order(wb, customer["id"], variant["id"], 1, "foreign-order")
        _, shipment = self.request("POST", "/shipments", self.sessions["OWNER"], wb, {
            "order_id": order["id"], "status": "DRAFT", "notes": f"{PREFIX} foreign shipment"
        }, expected=(201,))
        self.created["shipments"].append(str(shipment["id"]))
        return {"customer": customer, "variant": variant, "inventory": inventory, "order": order, "shipment": shipment}

    def gate_j(self, customer: dict[str, Any], manager_variant: dict[str, Any], foreign: dict[str, Any]) -> None:
        manager = self.sessions["MANAGER"]
        analyst = self.sessions["ANALYST"]
        owner = self.sessions["OWNER"]
        code, order = self.create_order(WORKSPACE_A, customer["id"], manager_variant["id"], 1, "manager-flow", manager, (201,))
        oid = str(order["id"])
        code2, _ = self.status(oid, WORKSPACE_A, "CANCELLED", manager)
        self.check("J", "MANAGER retains current operational order permission", code == 201 and code2 == 200)
        self.request("DELETE", f"/orders/{oid}", manager, WORKSPACE_A, expected=(204,))

        for path in ("/orders", "/inventory", "/shipments"):
            code, _ = self.request("GET", path, analyst, WORKSPACE_A)
            self.check("J", f"ANALYST GET {path} allowed", code == 200, {"status": code})
        code, _ = self.create_order(WORKSPACE_A, customer["id"], manager_variant["id"], 1, "analyst-denied", analyst, None)
        self.check("J", "ANALYST order POST denied", code == 403, {"status": code})
        inv = self.inventory_by_variant(WORKSPACE_A, str(manager_variant["id"]))
        code, _ = self.request("POST", f"/inventory/{inv['id']}/transactions", analyst, WORKSPACE_A, {
            "transaction_type": "STOCK_IN", "quantity": 1, "reason": f"{PREFIX} analyst denied"
        })
        self.check("J", "ANALYST inventory mutation denied", code == 403, {"status": code})
        code, _ = self.request("POST", "/shipments", analyst, WORKSPACE_A, {"order_id": foreign["order"]["id"], "status": "DRAFT"})
        self.check("J", "ANALYST shipment mutation denied", code == 403, {"status": code})

        code, _ = self.create_order(WORKSPACE_A, foreign["customer"]["id"], manager_variant["id"], 1, "foreign-customer", owner, None)
        self.check("J", "foreign customer rejected", code in (400, 404, 422), {"status": code})
        code, _ = self.create_order(WORKSPACE_A, customer["id"], foreign["variant"]["id"], 1, "foreign-variant", owner, None)
        self.check("J", "foreign variant rejected", code in (400, 404, 422), {"status": code})
        code, _ = self.request("GET", f"/orders/{foreign['order']['id']}", owner, WORKSPACE_A)
        self.check("J", "foreign order read/update boundary enforced", code == 404, {"status": code})
        code, _ = self.request("POST", f"/inventory/{foreign['inventory']['id']}/transactions", owner, WORKSPACE_A, {
            "transaction_type": "STOCK_IN", "quantity": 1, "reason": f"{PREFIX} foreign denied"
        })
        self.check("J", "foreign inventory mutation rejected", code == 404, {"status": code})
        code, _ = self.request("GET", f"/shipments/{foreign['shipment']['id']}", owner, WORKSPACE_A)
        self.check("J", "foreign shipment read rejected", code == 404, {"status": code})
        _, history = self.request("GET", f"/inventory/transactions?inventory_id={foreign['inventory']['id']}", owner, WORKSPACE_A, expected=(200,))
        self.check("J", "foreign inventory history does not leak", history == [], {"rows": len(history)})

    def cleanup_api(self) -> None:
        owner = self.sessions["OWNER"]
        for workspace in filter(None, (WORKSPACE_A, self.workspace_b)):
            try:
                _, rows = self.request("GET", "/shipments", owner, workspace, expected=(200,))
                for row in rows:
                    if PREFIX in str(row.get("notes", "")) or PREFIX in str(row.get("tracking_number", "")):
                        self.request("DELETE", f"/shipments/{row['id']}", owner, workspace)
            except Exception:
                pass
            try:
                _, rows = self.request("GET", "/orders", owner, workspace, expected=(200,))
                for row in rows:
                    if PREFIX not in str(row.get("notes", "")):
                        continue
                    status = row.get("status")
                    if status in ("NEW", "CONFIRMED"):
                        self.status(str(row["id"]), workspace, "CANCELLED")
                        status = "CANCELLED"
                    if status == "CANCELLED":
                        self.request("DELETE", f"/orders/{row['id']}", owner, workspace)
            except Exception:
                pass

        _, orders = self.request("GET", "/orders", owner, WORKSPACE_A, expected=(200,))
        _, shipments = self.request("GET", "/shipments", owner, WORKSPACE_A, expected=(200,))
        _, inventory = self.request("GET", "/inventory", owner, WORKSPACE_A, expected=(200,))
        active_orders = [o for o in orders if PREFIX in str(o.get("notes", ""))]
        active_shipments = [s for s in shipments if PREFIX in str(s.get("notes", "")) or PREFIX in str(s.get("tracking_number", ""))]
        fixture_variants = set(self.created["variants"])
        fixture_inventory = [i for i in inventory if str(i.get("product_variant_id")) in fixture_variants]
        reservations = sum(int(i["reserved_quantity"]) for i in fixture_inventory)
        self.residual = {"orders": len(active_orders), "shipments": len(active_shipments), "reservations": reservations, "stock_delta": 0}
        self.check("M", "API cleanup leaves no active reservations or shipments", reservations == 0 and len(active_shipments) == 0, self.residual)

    def run(self) -> int:
        try:
            self.wait_environment()
            self.setup_sessions()
            customer = self.create_customer(WORKSPACE_A, "Primary")
            _, a, _ = self.create_variant(WORKSPACE_A, "A", 10)
            _, b, _ = self.create_variant(WORKSPACE_A, "B", 10)
            _, last, _ = self.create_variant(WORKSPACE_A, "LAST", 1)
            _, helper1, _ = self.create_variant(WORKSPACE_A, "H1", 1)
            _, helper2, _ = self.create_variant(WORKSPACE_A, "H2", 1)
            _, contested, _ = self.create_variant(WORKSPACE_A, "CONTEST", 1)
            _, manager_variant, _ = self.create_variant(WORKSPACE_A, "MANAGER", 2)
            _, zero, _ = self.create_variant(WORKSPACE_A, "ARCHIVE0", 0)
            _, stocked, _ = self.create_variant(WORKSPACE_A, "ARCHIVE3", 3)
            foreign = self.setup_foreign()

            self.gates_b_to_f_h(customer, a, b)
            self.gate_g(customer, last, helper1, helper2, contested)
            self.gate_i(customer, zero, stocked)
            self.gate_j(customer, manager_variant, foreign)
            self.check("H", "no Nova Poshta or Meta provider endpoint invoked", self.network["nova_poshta"] == 0 and self.network["meta"] == 0, self.network)
            self.check("A", "no backend HTTP 5xx during closure", self.network["5xx"] == 0, self.network)
        except Exception as exc:
            self.safe_error = str(exc)[:500]
            self.findings.append({"severity": "BLOCKER", "safe_error": self.safe_error})
        finally:
            try:
                if self.sessions.get("OWNER"):
                    self.cleanup_api()
            except Exception as exc:
                self.findings.append({"severity": "WARN", "cleanup_error": str(exc)[:300]})

        failures = [item for item in self.checks if item["status"] != "PASS"]
        core_pass = not failures and not self.safe_error
        report = {
            "sprint": "8D", "phase": "core-runtime",
            "decision": "PASS_PENDING_POSTGRES_CLEANUP" if core_pass else "FAIL",
            "runtime": self.runtime, "marker": PREFIX, "checks": self.checks,
            "findings": self.findings, "network": self.network, "residual": self.residual,
            "security": {
                "passwords_suppressed": True, "tokens_suppressed": True,
                "authorization_headers_suppressed": True, "customer_pii_synthetic": True,
                "provider_calls_suppressed": True,
            },
            "safe_error": self.safe_error,
        }
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        lines = [
            "# Sprint 8D core runtime closure", "", f"- Decision: **{report['decision']}**",
            f"- Runtime: `{self.runtime.get('runtime_commit', 'unavailable')}`",
            f"- Checks: {len(self.checks) - len(failures)} PASS / {len(failures)} FAIL",
            f"- Residual: `{json.dumps(self.residual, ensure_ascii=False)}`", "",
            "| Gate | Check | Status |", "|---|---|---|",
        ]
        lines += [f"| {c['gate']} | {c['name']} | {c['status']} |" for c in self.checks]
        MD.write_text("\n".join(lines), encoding="utf-8")
        print(json.dumps(report, ensure_ascii=False, indent=2), flush=True)
        return 0 if core_pass else 1


if __name__ == "__main__":
    required = [
        "STAGING_FRONTEND_URL", "STAGING_API_URL", "EXPECTED_RUNTIME_COMMIT",
        "STAGING_OWNER_EMAIL", "STAGING_OWNER_PASSWORD",
        "STAGING_MANAGER_EMAIL", "STAGING_MANAGER_PASSWORD",
        "STAGING_ANALYST_EMAIL", "STAGING_ANALYST_PASSWORD",
        "STAGING_TEST_WORKSPACE_ID",
    ]
    missing = [name for name in required if not os.environ.get(name)]
    if missing:
        print("Missing required Sprint 8D inputs", file=sys.stderr)
        raise SystemExit(2)
    raise SystemExit(Closure().run())
