#!/usr/bin/env python3
"""Cold-start-safe entrypoint for Sprint 8B staging closure."""
from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path

MODULE_PATH = Path(__file__).with_name("staging_sprint_8b_closure.py")
spec = importlib.util.spec_from_file_location("sellora_sprint_8b_closure", MODULE_PATH)
if spec is None or spec.loader is None:
    raise SystemExit("Unable to load Sprint 8B closure module")
base = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = base
spec.loader.exec_module(base)


class Sprint8BClosureV2(base.Sprint8BClosure):
    def create_demo_flow(self, browser) -> None:
        assert self.owner is not None
        context = self.init_context(browser, self.owner, self.empty_workspace_id, "light", 1366, 768)
        context.add_init_script(
            script="""
            (() => {
              const originalFetch = window.fetch.bind(window);
              window.fetch = async (...args) => {
                const request = args[0];
                const url = typeof request === 'string' ? request : request?.url || '';
                const init = args[1] || {};
                const method = String(init.method || request?.method || 'GET').toUpperCase();
                if (method === 'POST' && url.includes('/workspaces/demo')) {
                  await new Promise((resolve) => setTimeout(resolve, 1800));
                }
                return originalFetch(...args);
              };
            })();
            """
        )
        page = context.new_page()
        label = "owner-demo-create/desktop/light"
        self.watch_page(page, label)
        request_counter = {"count": 0}

        def count_demo_request(request) -> None:
            if request.method == "POST" and "/workspaces/demo" in request.url:
                request_counter["count"] += 1

        page.on("request", count_demo_request)
        try:
            page.goto(f"{self.frontend}/dashboard", wait_until="domcontentloaded", timeout=45000)
            self.wait_page(page)
            button = page.get_by_role("button", name=re.compile(r"демо|demo", re.I)).first
            if button.count() == 0:
                raise RuntimeError("OWNER demo CTA not found")
            button.evaluate("element => { element.click(); element.click(); }")
            page.wait_for_timeout(250)
            loading_visible = button.is_disabled()
            page.screenshot(path=str(base.SHOTS / "owner-demo-generation-loading.png"))
            page.locator("[data-demo-workspace-banner]").wait_for(state="visible", timeout=120000)
            self.demo_workspace_id = str(page.evaluate("localStorage.getItem('sellora.current_workspace_id') || ''"))
            self.result("OWNER", "demo generation loading state visible", loading_visible)
            self.result("OWNER", "duplicate-click protection emitted one POST", request_counter["count"] == 1, request_counter["count"])
            self.result("OWNER", "demo workspace has separate ID", bool(self.demo_workspace_id) and self.demo_workspace_id != self.empty_workspace_id, self.demo_workspace_id)
            self.check_page(page, label, "demo banner immediately after creation", "owner-demo-created-banner.png")
        except Exception as exc:
            self.finding("FAIL", label, "runner_exception", repr(exc))
        finally:
            context.close()

        if not self.demo_workspace_id:
            return

        _, first = self.request("POST", "/workspaces/demo", token=self.owner.access_token, payload={"locale": "uk", "currency_code": "UAH"}, expected=(201,))
        _, second = self.request("POST", "/workspaces/demo", token=self.owner.access_token, payload={"locale": "uk", "currency_code": "UAH"}, expected=(201,))
        self.result(
            "Idempotency",
            "repeated runtime POST returns same demo workspace",
            str(first.get("id")) == self.demo_workspace_id == str(second.get("id")),
            {"first": first.get("id"), "second": second.get("id")},
        )

        _, status_data = self.request("GET", "/onboarding/status", token=self.owner.access_token, workspace_id=self.demo_workspace_id, expected=(200,))
        self.result("Dataset", "demo onboarding is provenance-labeled and complete", status_data.get("is_demo_workspace") is True and status_data.get("progress_percent") == 100, status_data)

        counts = {}
        for key, path in {
            "leads": "/leads",
            "customers": "/customers",
            "products": "/products",
            "inventory": "/inventory",
            "inventory_transactions": "/inventory/transactions",
            "orders": "/orders",
            "shipments": "/shipments",
            "campaigns": "/advertising/campaigns",
            "metrics": "/advertising/metrics",
            "finance_adjustments": "/finance/adjustments",
        }.items():
            _, data = self.request("GET", path, token=self.owner.access_token, workspace_id=self.demo_workspace_id, expected=(200,))
            counts[key] = base.item_count(data)
        expected = {
            "leads": 6,
            "customers": 4,
            "products": 6,
            "inventory": 6,
            "inventory_transactions": 6,
            "orders": 5,
            "shipments": 0,
            "campaigns": 0,
            "metrics": 0,
            "finance_adjustments": 0,
        }
        self.result("Dataset", "core demo dataset is coherent and truthful", all(counts.get(key) == value for key, value in expected.items()), {"actual": counts, "expected": expected})

        code, _ = self.request("PATCH", "/workspaces/demo/deactivate", token=self.manager.access_token, workspace_id=self.demo_workspace_id)
        self.result("RBAC", "MANAGER cannot deactivate OWNER demo workspace", code == 403, f"HTTP {code}")
        code, _ = self.request("PATCH", "/workspaces/demo/deactivate", token=self.analyst.access_token, workspace_id=self.demo_workspace_id)
        self.result("RBAC", "ANALYST cannot deactivate OWNER demo workspace", code == 403, f"HTTP {code}")


if __name__ == "__main__":
    required = [
        "STAGING_FRONTEND_URL",
        "STAGING_API_URL",
        "STAGING_OWNER_EMAIL",
        "STAGING_OWNER_PASSWORD",
        "STAGING_MANAGER_EMAIL",
        "STAGING_MANAGER_PASSWORD",
        "STAGING_ANALYST_EMAIL",
        "STAGING_ANALYST_PASSWORD",
        "STAGING_TEST_WORKSPACE_ID",
    ]
    missing = [name for name in required if not base.env(name)]
    if missing:
        print("Missing required Sprint 8B staging inputs", file=sys.stderr)
        raise SystemExit(2)
    decision = Sprint8BClosureV2().run()
    print(f"Sprint 8B staging closure decision: {decision}")
    raise SystemExit(0 if decision == "PASS" else 1)
